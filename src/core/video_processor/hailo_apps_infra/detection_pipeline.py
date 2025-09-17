import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst, GLib
import os
import argparse
import multiprocessing
import numpy as np
import setproctitle
import cv2
import time
import hailo
from core.video_processor.hailo_apps_infra.hailo_rpi_common import (
    get_default_parser,
    detect_hailo_arch,
)
from core.video_processor.hailo_apps_infra.gstreamer_helper_pipelines import (
    QUEUE,
    SOURCE_PIPELINE,
    INFERENCE_PIPELINE,
    INFERENCE_PIPELINE_WRAPPER,
    TILE_CROPPER_PIPELINE,
    TRACKER_PIPELINE,
    USER_CALLBACK_PIPELINE,
    DISPLAY_PIPELINE,
)
from core.video_processor.hailo_apps_infra.gstreamer_app import (
    GStreamerApp,
    app_callback_class,
    dummy_callback,
)


# -----------------------------------------------------------------------------------------------
# User Gstreamer Application
# -----------------------------------------------------------------------------------------------


# This class inherits from the hailo_rpi_common.GStreamerApp class
class GStreamerDetectionApp(GStreamerApp):
    def __init__(self, app_callback, user_data):
        parser = get_default_parser()
        parser.add_argument(
            "--labels-json",
            default=None,
            help="Path to costume labels JSON file",
        )
        args = parser.parse_args()
        # Call the parent class constructor
        super().__init__(args, user_data)
        # Additional initialization code can be added here
        # Set Hailo parameters these parameters should be set based on the model used
        self.batch_size = 8
        nms_score_threshold = 0.3
        nms_iou_threshold = 0.45

        # Determine the architecture if not specified
        if args.arch is None:
            detected_arch = detect_hailo_arch()
            if detected_arch is None:
                raise ValueError(
                    "Could not auto-detect Hailo architecture. Please specify --arch manually."
                )
            self.arch = detected_arch
            print(f"Auto-detected Hailo architecture: {self.arch}")
        else:
            self.arch = args.arch

        if args.hef_path is not None:
            self.hef_path = args.hef_path
        # Set the HEF file path based on the arch
        elif self.arch == "hailo8":
            self.hef_path = os.path.join(self.current_path, "../resources/yolov8m.hef")
        else:  # hailo8l
            self.hef_path = os.path.join(
                self.current_path, "../resources/yolov8s_h8l.hef"
            )

        # Set the post-processing shared object file
        self.post_process_so = os.path.join(
            self.current_path, "../resources/libyolo_hailortpp_postprocess.so"
        )
        self.post_function_name = "filter_letterbox"
        # User-defined label JSON file
        self.labels_json = args.labels_json

        self.app_callback = app_callback

        self.thresholds_str = (
            f"nms-score-threshold={nms_score_threshold} "
            f"nms-iou-threshold={nms_iou_threshold} "
            f"output-format-type=HAILO_FORMAT_TYPE_FLOAT32"
        )

        # Set the process title
        setproctitle.setproctitle("Hailo Detection App")

        self.create_pipeline()

    def get_pipeline_string(self):

        source_pipeline = SOURCE_PIPELINE(
            self.video_source, self.video_width, self.video_height
        )
        detection_pipeline = INFERENCE_PIPELINE(
            hef_path=self.hef_path,
            post_process_so=self.post_process_so,
            post_function_name=self.post_function_name,
            batch_size=self.batch_size,
            config_json=self.labels_json,
            additional_params=self.thresholds_str,
        )
        detection_pipeline_wrapper = INFERENCE_PIPELINE_WRAPPER(detection_pipeline)
        tracker_pipeline = TRACKER_PIPELINE(class_id=1)
        user_callback_pipeline = USER_CALLBACK_PIPELINE()
        display_pipeline = DISPLAY_PIPELINE(
            video_sink=self.video_sink, sync=self.sync, show_fps=self.show_fps
        )

        pipeline_string = (
            f"{source_pipeline} ! "
            f"{detection_pipeline_wrapper} ! "
            f"{tracker_pipeline} ! "
            f"{user_callback_pipeline} ! "
            f"{display_pipeline}"
        )

        print(pipeline_string)
        return pipeline_string

    def get_tiled_pipeline_string(self):
        """Get the tiled pipeline string using RPI camera source.

        Returns:
            str: The complete GStreamer pipeline string for tiled inference with RPI camera.
        """
        return """filesrc location=/home/tails/TAILS-Embedded/OnBoardNode/resources/DJI_0501_10fps.MP4 name=src_0 !
decodebin ! 
videoconvert qos=false ! 
video/x-raw,pixel-aspect-ratio=1/1,format=RGB ! 
queue leaky=no max-size-buffers=3 max-size-bytes=0 max-size-time=0 ! 
hailotilecropper internal-offset=true name=cropper tiles-along-x-axis=4 tiles-along-y-axis=3 overlap-x-axis=0.08 overlap-y-axis=0.08 hailotileaggregator flatten-detections=true iou-threshold=0.3 name=agg cropper. ! 
queue leaky=no max-size-buffers=3 max-size-bytes=0 max-size-time=0 ! agg. cropper. ! 
queue leaky=no max-size-buffers=3 max-size-bytes=0 max-size-time=0 ! 
hailonet hef-path=/home/tails/TAILS-Embedded/OnBoardNode/resources/yolov8s_h8l.hef batch-size=16 output-format-type=HAILO_FORMAT_TYPE_FLOAT32 ! 
queue leaky=no max-size-buffers=3 max-size-bytes=0 max-size-time=0 ! 
hailofilter name=inference_hailofilter so-path=/home/tails/TAILS-Embedded/OnBoardNode/pipelines/resources/libyolo_hailortpp_postprocess.so qos=false !
queue leaky=no max-size-buffers=3 max-size-bytes=0 max-size-time=0 ! agg. agg. !
queue leaky=no max-size-buffers=3 max-size-bytes=0 max-size-time=0 !
hailooverlay qos=false !
queue leaky=no max-size-buffers=3 max-size-bytes=0 max-size-time=0 ! 
videoconvert qos=false !
fpsdisplaysink video-sink=xvimagesink name=hailo_display sync=false text-overlay=true"""


if __name__ == "__main__":
    # Create an instance of the user app callback class
    user_data = app_callback_class()
    app_callback = dummy_callback
    app = GStreamerDetectionApp(app_callback, user_data)
    app.run()
