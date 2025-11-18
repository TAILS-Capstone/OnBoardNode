import gi

from constants import BATCH_INTERVAL_SEC, CONF_THRESHOLD, DATA_MAX_AGE_SEC, DATA_MAX_ROWS, DEDUP_DISTANCE_M, LORA_CFG, RELEVANT_CLASSES
from utils.distance_utils import haversine_m

gi.require_version("Gst", "1.0")
from gi.repository import Gst, GLib
import cv2
import hailo
import sys
import os
import time
import math
import threading
from collections import deque
import pandas as pd

from core.gps.gps_manager import GPSManager

from core.vision.hailo_apps_infra.hailo_rpi_common import (
    get_caps_from_pad,
    get_numpy_from_buffer,
    app_callback_class,
)
from core.vision.hailo_apps_infra.detection_pipeline import GStreamerDetectionApp
from core.transmitter import SX126x

# --- Logging initialization (added) ---
import os
import sys
import logging

def _init_logging():
    if logging.getLogger().handlers:
        return  # Already configured elsewhere
    level = os.getenv("APP_LOG_LEVEL", "INFO").upper()
    try:
        from systemd.journal import JournalHandler  # type: ignore
        handler = JournalHandler()
    except Exception:
        handler = logging.StreamHandler(sys.stdout)
    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    handler.setFormatter(logging.Formatter(fmt))
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(level)

_init_logging()
logger = logging.getLogger(__name__)
# --- End logging initialization ---

def now_ts() -> float:
    return time.time()

# ======================================================================================
# Detection + GPS + LoRa class
# ======================================================================================
class DetectionWithGPS(app_callback_class):
    def __init__(self, lora):
        super().__init__()
        self.gps_manager = GPSManager()
        self.detection_count = 0

        # LoRa radio handle
        self.lora = lora

        # always grab frames for recording
        self.use_frame = True

        # DataFrame to store detections; columns: ts, label, lat, lon, sent
        self.df = pd.DataFrame(columns=["ts", "label", "id", "lat", "lon", "sent"])
        self.df_lock = threading.Lock()

        # batching
        self.last_tx_time = 0.0

        # remember last location per ID (for person)
        # maps: track_id (int) -> (lat, lon)
        self.last_loc_by_id = {}

        # Video recording / rotation settings
        self.recordings_dir = os.getenv("VIDEO_DIR", os.path.join(os.getcwd(), "recordings"))
        os.makedirs(self.recordings_dir, exist_ok=True)
        self.video_fps = float(os.getenv("VIDEO_FPS", "20.0"))
        self.video_codec = os.getenv("VIDEO_CODEC", "mp4v")
        self.rotate_interval = int(os.getenv("VIDEO_ROTATE_SEC", "30"))  # seconds
        self.out_writer = None
        self._video_lock = threading.Lock()
        self._segment_start_ts = 0.0
        # track per-segment frame count and path for debug
        self._segment_frame_count = 0
        self._current_segment_path = None
        # recordings will be written in segments ~rotate_interval long; writer is created on first frame

    def increment(self):
        self.detection_count += 1

    def get_count(self):
        return self.detection_count

    # ------------- GPS helpers -------------
    def get_location_data(self):
        lat, lon, elevation = self.gps_manager.get_current_location()
        speed, course = self.gps_manager.get_speed_and_course()
        if self.gps_manager.is_positioned:
            return {
                "latitude": lat,
                "longitude": lon,
                "elevation": elevation,
                "speed": speed,
                "course": course
            }
        return None

    def get_gps_string(self):
        location_data = self.get_location_data()
        if location_data:
            return f"[GPS: Lat={location_data['latitude']:.6f}, Lon={location_data['longitude']:.6f}, Elev={location_data['elevation']:.2f}m, Speed={location_data['speed']:.2f}m/s]"
        return "[GPS: No position fix]"

    # ------------- Data handling -------------
    def _should_record(self, label: str, track_id, lat: float, lon: float) -> bool:
        # Only special handling for person
        if label == "person" and track_id is not None:
            prev = self.last_loc_by_id.get(track_id)
            if prev is not None:
                if haversine_m(lat, lon, prev[0], prev[1]) < DEDUP_DISTANCE_M:
                    # same ID essentially in same spot → skip
                    return False
        return True

    def add_detection(self, label: str, track_id, lat: float, lon: float):
        if not self._should_record(label, track_id, lat, lon):
            return

        ts = now_ts()
        with self.df_lock:
            self.df.loc[len(self.df)] = [ts, label, track_id, lat, lon, False]

            # keep memory bounded
            cutoff = ts - DATA_MAX_AGE_SEC
            self.df = self.df[self.df["ts"] >= cutoff]
            if len(self.df) > DATA_MAX_ROWS:
                self.df = self.df.iloc[-DATA_MAX_ROWS:].reset_index(drop=True)

            # update last location for this ID (person)
            if label == "person" and track_id is not None:
                self.last_loc_by_id[track_id] = (lat, lon)


    def dedup_by_distance(self, batch_df: pd.DataFrame) -> pd.DataFrame:
        """
        Deduplicate within this batch by label and 10 m radius.
        For each label, keep first occurrence, drop subsequent points < 10 m from any kept point of same label.
        """
        if batch_df.empty:
            return batch_df

        keep_rows = []
        for label, group in batch_df.groupby("label"):
            selected = []
            for idx, row in group.sort_values("ts").iterrows():
                if not selected:
                    selected.append((idx, row))
                    continue
                too_close = False
                for _, kept in selected:
                    d = haversine_m(row["lat"], row["lon"], kept["lat"], kept["lon"])
                    if d < DEDUP_DISTANCE_M:
                        too_close = True
                        break
                if not too_close:
                    selected.append((idx, row))
            keep_rows.extend([i for i, _ in selected])

        return batch_df.loc[keep_rows].sort_values("ts")
    
    def dedup_by_id_and_distance(self, batch_df: pd.DataFrame) -> pd.DataFrame:
        if batch_df.empty:
            return batch_df

        keep_rows = []
        # group by both label and id; id may be None/NaN for rare cases
        grouped = batch_df.groupby(["label", "id"], dropna=False)
        for (_, _id), group in grouped:
            selected = []
            for idx, row in group.sort_values("ts").iterrows():
                if not selected:
                    selected.append((idx, row))
                    continue
                too_close = any(
                    haversine_m(row["lat"], row["lon"], kept["lat"], kept["lon"]) < DEDUP_DISTANCE_M
                    for _, kept in selected
                )
                if not too_close:
                    selected.append((idx, row))
            keep_rows.extend([i for i, _ in selected])

        return batch_df.loc[keep_rows].sort_values("ts")

    def try_transmit_batch(self):
        t = now_ts()
        if t - self.last_tx_time < BATCH_INTERVAL_SEC:
            return
        self.last_tx_time = t

        with self.df_lock:
            pending = self.df[self.df["sent"] == False].copy()

        if pending.empty:
            return

        deduped = self.dedup_by_id_and_distance(pending)

        for _, row in deduped.iterrows():
            # include track id in payload; fall back to -1 if None/NaN
            track_id = row["id"]
            try:
                track_id_int = int(track_id)
            except Exception:
                track_id_int = -1
            payload = f"{row['label']},{track_id_int},{row['lat']:.6f},{row['lon']:.6f}"
            self.lora_send_string(payload)

        with self.df_lock:
            sent_mask = self.df.index.isin(deduped.index)
            self.df.loc[sent_mask, "sent"] = True


    # ------------- LoRa sending -------------
    def lora_send_string(self, s: str):
        # Encode to bytes; SX126x.write expects list/bytes
        data = s.encode("utf-8")
        # Basic guard on payload size (truncate if needed to fit configured payloadLength)
        max_len = max(1, LORA_CFG["payloadLength"])
        if len(data) > max_len:
            data = data[:max_len]

        self.lora.beginPacket()
        self.lora.write(list(data), len(data))
        self.lora.endPacket()
        self.lora.wait()  # wait for TX done
        # Print radio stats
        logger.info(f"[LoRa TX] {s} | tx_time={self.lora.transmitTime():0.2f} ms | rate={self.lora.dataRate():0.2f} B/s")

    # Called by detection_callback to record the current frame.
    # This rotates files every self.rotate_interval seconds.
    def set_frame(self, frame):
        if frame is None:
            return
        now = time.time()
        with self._video_lock:
            logger.debug(f"Received frame for recording at {now:.3f}, shape={getattr(frame,'shape',None)}")
            need_new = False
            if self.out_writer is None:
                need_new = True
            elif now - self._segment_start_ts >= self.rotate_interval:
                # rotate: close current writer and start a new one
                # log details about the segment being closed
                try:
                    duration = now - self._segment_start_ts
                    logger.info(
                        f"Rotating recording segment. Closing: path={self._current_segment_path} duration={duration:.2f}s frames={self._segment_frame_count}"
                    )
                    self.out_writer.release()
                except Exception:
                    logger.exception("Error releasing VideoWriter during rotation")
                # reset segment metadata
                self.out_writer = None
                self._current_segment_path = None
                self._segment_frame_count = 0
                need_new = True

            if need_new:
                h, w = frame.shape[:2]
                fourcc = cv2.VideoWriter_fourcc(*self.video_codec)
                ts = time.strftime("%Y%m%d_%H%M%S")
                fname = f"recording_{ts}.mp4"
                path = os.path.join(self.recordings_dir, fname)
                try:
                    self.out_writer = cv2.VideoWriter(path, fourcc, self.video_fps, (w, h))
                    self._segment_start_ts = now
                    self._segment_frame_count = 0
                    self._current_segment_path = path
                    logger.info(f"Started new recording segment: {path} fps={self.video_fps} codec={self.video_codec} rotate_sec={self.rotate_interval}")
                except Exception:
                    logger.exception(f"Failed to create VideoWriter for path={path}")
                    self.out_writer = None
                    self._current_segment_path = None

            if self.out_writer is not None:
                try:
                    self.out_writer.write(frame)
                    self._segment_frame_count += 1
                    # periodic debug log every 100 frames to reduce spam
                    if self._segment_frame_count % 100 == 0:
                        logger.debug(f"Wrote frame #{self._segment_frame_count} to {self._current_segment_path}")
                except Exception:
                    logger.exception(f"Failed writing video frame to {self._current_segment_path}")

    def stop_recording(self):
        with self._video_lock:
            if self.out_writer is not None:
                now = time.time()
                try:
                    duration = now - self._segment_start_ts if self._segment_start_ts else 0.0
                    logger.info(
                        f"Stopping video recording. Finalizing segment: path={self._current_segment_path} duration={duration:.2f}s frames={self._segment_frame_count}"
                    )
                    self.out_writer.release()
                except Exception:
                    logger.exception("Error while releasing VideoWriter")
                finally:
                    self.out_writer = None
                    self._current_segment_path = None
                    self._segment_frame_count = 0

# ======================================================================================
# GStreamer detection callback
# ======================================================================================
def detection_callback(pad, info, user_data: DetectionWithGPS):
    buffer = info.get_buffer()
    if buffer is None:
        return Gst.PadProbeReturn.OK

    user_data.increment()
    gps_info = user_data.get_gps_string()  # (still prints if you need it)

    location_data = user_data.get_location_data()
    if not location_data:
        location_data = {"latitude": 0.0, "longitude": 0.0, "elevation": 0.0, "speed": 0.0, "course": 0.0}

    # caps → optional frame
    format, width, height = get_caps_from_pad(pad)
    frame = None
    if format and width and height:
        frame = get_numpy_from_buffer(buffer, format, width, height)

    roi = hailo.get_roi_from_buffer(buffer)
    detections = roi.get_objects_typed(hailo.HAILO_DETECTION)

    for detection in detections:
        label = detection.get_label()
        if label not in RELEVANT_CLASSES:
            continue  # ignore non-relevant classes

        confidence = detection.get_confidence()
        bbox = detection.get_bbox()

        # Hailo track ID (from tracker)
        track = detection.get_objects_typed(hailo.HAILO_UNIQUE_ID)
        track_id = track[0].get_id() if len(track) == 1 else None

        if confidence >= CONF_THRESHOLD:
            user_data.add_detection(
                label=label,
                track_id=track_id,
                lat=location_data["latitude"],
                lon=location_data["longitude"],
            )

    if frame is not None:
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        user_data.set_frame(frame)

    user_data.try_transmit_batch()
    return Gst.PadProbeReturn.OK


# ======================================================================================
# LoRa initialization
# ======================================================================================
def init_lora():
    LoRa = SX126x()
    logger.info("Begin LoRa radio with:")
    logger.info(f"\tReset pin: {LORA_CFG['resetPin']}")
    logger.info(f"\tBusy pin: {LORA_CFG['busyPin']}")
    logger.info(f"\tIRQ pin:  {LORA_CFG['irqPin']}")
    logger.info(f"\tTXEN pin: {LORA_CFG['txenPin']}")
    logger.info(f"\tRXEN pin: {LORA_CFG['rxenPin']}")

    if not LoRa.begin(
        LORA_CFG["busId"], LORA_CFG["csId"],
        LORA_CFG["resetPin"], LORA_CFG["busyPin"],
        LORA_CFG["irqPin"], LORA_CFG["txenPin"], LORA_CFG["rxenPin"]
    ):
        raise RuntimeError("Unable to initialize LoRa radio")

    LoRa.setDio2RfSwitch()

    logger.info(f"Set frequency to {LORA_CFG['frequency']/1e6:.3f} MHz")
    LoRa.setFrequency(LORA_CFG["frequency"])

    logger.info(f"Set TX power to +{LORA_CFG['txPower']} dBm")
    LoRa.setTxPower(LORA_CFG["txPower"], LORA_CFG["txPowerVersion"])

    logger.info("Set modulation parameters:")
    logger.info(f"\tSpreading factor = {LORA_CFG['sf']}")
    logger.info(f"\tBandwidth = {LORA_CFG['bw']/1000:.0f} kHz")
    logger.info(f"\tCoding rate = 4/{LORA_CFG['cr']}")
    LoRa.setLoRaModulation(LORA_CFG["sf"], LORA_CFG["bw"], LORA_CFG["cr"])

    logger.info("Set packet parameters:")
    logger.info(f"\t{'Implicit' if LORA_CFG['headerType'] == SX126x.HEADER_IMPLICIT else 'Explicit'} header type")
    logger.info(f"\tPreamble length = {LORA_CFG['preambleLength']}")
    logger.info(f"\tPayload Length  = {LORA_CFG['payloadLength']}")
    logger.info(f"\tCRC {'on' if LORA_CFG['crcType'] else 'off'}")
    LoRa.setLoRaPacket(
        LORA_CFG["headerType"],
        LORA_CFG["preambleLength"],
        LORA_CFG["payloadLength"],
        LORA_CFG["crcType"]
    )

    logger.info(f"Set synchronize word to 0x{LORA_CFG['syncWord']:02X}")
    LoRa.setSyncWord(LORA_CFG["syncWord"])

    logger.info("\n-- LoRa Ready --\n")
    return LoRa

# ======================================================================================
# Main
# ======================================================================================
if __name__ == "__main__":
    # Initialize LoRa radio
    lora = init_lora()

    # Wire up app
    user_data = DetectionWithGPS(lora)
    app = GStreamerDetectionApp(detection_callback, user_data)

    try:
        app.run()
    except KeyboardInterrupt:
        logger.info("Program is terminating...")
    finally:
        try:
            user_data.stop_recording()
        except Exception:
            pass
        try:
            lora.end()
        except Exception:
            pass
        sys.exit(0)
