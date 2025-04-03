import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst, GLib
import cv2
import hailo
import sys
import os

# Add the GPS module path to system path
sys.path.append(os.path.join(os.path.dirname(__file__), '../lora_hat/gps'))
from gps_manager import GPSManager

from hailo_apps_infra.hailo_rpi_common import (
    get_caps_from_pad,
    get_numpy_from_buffer,
    app_callback_class,
)
from hailo_apps_infra.detection_pipeline import GStreamerDetectionApp

class DetectionWithGPS(app_callback_class):
    def __init__(self):
        super().__init__()
        self.gps_manager = GPSManager()
        self.detection_count = 0
        
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

def detection_callback(pad, info, user_data):
    buffer = info.get_buffer()
    if buffer is None:
        return Gst.PadProbeReturn.OK

    user_data.increment()
    gps_info = user_data.get_gps_string()
    
    # Get GPS data
    location_data = user_data.get_location_data()
    if location_data:
        print(f"Frame {user_data.get_count()} {gps_info}")
        print(f"GPS Location: Lat={location_data['latitude']:.6f}, Lon={location_data['longitude']:.6f} {gps_info}")
        print(f"Elevation: {location_data['elevation']:.2f}m, Speed: {location_data['speed']:.2f}m/s {gps_info}")

    # Get the caps from the pad
    format, width, height = get_caps_from_pad(pad)

    # Process video frame if enabled
    frame = None
    if user_data.use_frame and format and width and height:
        frame = get_numpy_from_buffer(buffer, format, width, height)

    # Get detections
    roi = hailo.get_roi_from_buffer(buffer)
    detections = roi.get_objects_typed(hailo.HAILO_DETECTION)

    # Process detections
    detection_count = 0
    for detection in detections:
        label = detection.get_label()
        confidence = detection.get_confidence()
        bbox = detection.get_bbox()
        
        # Get track ID if available
        track_id = 0
        track = detection.get_objects_typed(hailo.HAILO_UNIQUE_ID)
        if len(track) == 1:
            track_id = track[0].get_id()
            
        print(f"Detection: ID: {track_id} Label: {label} Confidence: {confidence:.2f} {gps_info}")
        
        if frame is not None:
            # Draw bounding box and label on frame
            x1, y1, x2, y2 = bbox.left, bbox.top, bbox.right, bbox.bottom
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
            cv2.putText(frame, f"{label} {confidence:.2f}", 
                       (int(x1), int(y1)-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    if frame is not None:
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        user_data.set_frame(frame)

    return Gst.PadProbeReturn.OK

if __name__ == "__main__":
    user_data = DetectionWithGPS()
    app = GStreamerDetectionApp(detection_callback, user_data, tiling=False)
    app.run() 