import argparse
import sys
import time
from typing import List

import cv2
import numpy as np

from picamera2 import CompletedRequest, MappedArray, Picamera2
from picamera2.devices import IMX500
from picamera2.devices.imx500 import NetworkIntrinsics
from picamera2.devices.imx500.postprocess import softmax

last_detections = []
LABELS = None
# Global variables for screenshot timing and FPS calculation
last_screenshot_time = 0
frame_counter = 0

class Classification:
    def __init__(self, idx: int, score: float):
        """Create a Classification object, recording the idx and score."""
        self.idx = idx
        self.score = score

def get_label(request: CompletedRequest, idx: int) -> str:
    """Retrieve the label corresponding to the classification index."""
    global LABELS
    if LABELS is None:
        LABELS = intrinsics.labels
        assert len(LABELS) in [1000, 1001], "Labels file should contain 1000 or 1001 labels."
        output_tensor_size = imx500.get_output_shapes(request.get_metadata())[0][0]
        if output_tensor_size == 1000:
            LABELS = LABELS[1:]  # Ignore the background label if present
    return LABELS[idx]

def parse_and_draw_classification_results(request: CompletedRequest):
    """Analyse and draw the classification results in the output tensor."""
    results = parse_classification_results(request)
    draw_classification_results(request, results)

def parse_classification_results(request: CompletedRequest) -> List[Classification]:
    """Parse the output tensor into the classification results above the threshold."""
    global last_detections
    np_outputs = imx500.get_outputs(request.get_metadata())
    if np_outputs is None:
        return last_detections
    np_output = np_outputs[0]
    if intrinsics.softmax:
        np_output = softmax(np_output)
    top_indices = np.argpartition(-np_output, 3)[:3]  # Get top 3 indices with the highest scores
    top_indices = top_indices[np.argsort(-np_output[top_indices])]  # Sort them by score
    last_detections = [Classification(index, np_output[index]) for index in top_indices]
    return last_detections

def draw_classification_results(request: CompletedRequest, results: List[Classification], stream: str = "main"):
    """Draw the classification results for this request onto the ISP output and save PNG every 4 seconds."""
    global last_screenshot_time, frame_counter
    frame_counter += 1  # Increment frame counter for FPS calculation

    with MappedArray(request, stream) as m:
        if intrinsics.preserve_aspect_ratio:
            # Drawing ROI box
            b_x, b_y, b_w, b_h = imx500.get_roi_scaled(request)
            color = (255, 0, 0)  # red
            cv2.putText(m.array, "ROI", (b_x + 5, b_y + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            cv2.rectangle(m.array, (b_x, b_y), (b_x + b_w, b_y + b_h), (255, 0, 0, 0))
            text_left, text_top = b_x, b_y + 20
        else:
            text_left, text_top = 0, 0

        # Draw classification labels on the image
        for index, result in enumerate(results):
            label = get_label(request, idx=result.idx)
            text = f"{label}: {result.score:.3f}"
            (text_width, text_height), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            text_x = text_left + 5
            text_y = text_top + 15 + index * 20

            # Draw a translucent background for text
            overlay = m.array.copy()
            cv2.rectangle(overlay,
                          (text_x, text_y - text_height),
                          (text_x + text_width, text_y + baseline),
                          (255, 255, 255), cv2.FILLED)
            alpha = 0.3
            cv2.addWeighted(overlay, alpha, m.array, 1 - alpha, 0, m.array)
            cv2.putText(m.array, text, (text_x, text_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        # Every 4 seconds, save the drawn image as a PNG and print FPS and resolution.
        current_time = time.time()
        if current_time - last_screenshot_time >= 4:
            elapsed = current_time - last_screenshot_time if last_screenshot_time != 0 else 4
            fps = frame_counter / elapsed
            filename = f"screenshot_{int(current_time)}.png"
            cv2.imwrite(filename, m.array)
            resolution = f"{m.array.shape[1]}x{m.array.shape[0]}"
            print(f"Saved screenshot: {filename} - FPS: {fps:.2f}, Resolution: {resolution}")
            last_screenshot_time = current_time
            frame_counter = 0

def get_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, help="Path of the model",
                        default="/usr/share/imx500-models/imx500_network_mobilenet_v2.rpk")
    parser.add_argument("--fps", type=int, help="Frames per second")
    parser.add_argument("-s", "--softmax", action=argparse.BooleanOptionalAction, help="Apply post-process softmax")
    parser.add_argument("-r", "--preserve-aspect-ratio", action=argparse.BooleanOptionalAction,
                        help="Preprocess the image with aspect ratio preserved")
    parser.add_argument("--labels", type=str, help="Path to the labels file")
    parser.add_argument("--print-intrinsics", action="store_true",
                        help="Print JSON network_intrinsics then exit")
    return parser.parse_args()

if __name__ == "__main__":
    args = get_args()

    # Must be called before creating Picamera2
    imx500 = IMX500(args.model)
    intrinsics = imx500.network_intrinsics
    if not intrinsics:
        intrinsics = NetworkIntrinsics()
        intrinsics.task = "classification"
    elif intrinsics.task != "classification":
        print("Network is not a classification task", file=sys.stderr)
        exit()

    # Override intrinsics settings from command-line arguments
    for key, value in vars(args).items():
        if key == 'labels' and value is not None:
            with open(value, 'r') as f:
                intrinsics.labels = f.read().splitlines()
        elif hasattr(intrinsics, key) and value is not None:
            setattr(intrinsics, key, value)

    # Set default labels if none provided
    if intrinsics.labels is None:
        with open("assets/imagenet_labels.txt", "r") as f:
            intrinsics.labels = f.read().splitlines()
    intrinsics.update_with_defaults()

    if args.print_intrinsics:
        print(intrinsics)
        exit()

    picam2 = Picamera2(imx500.camera_num)
    config = picam2.create_preview_configuration(controls={"FrameRate": intrinsics.inference_rate}, buffer_count=12)

    # Print the configured resolution (if available in the config)
    if 'main' in config and hasattr(config['main'], 'size'):
        print(f"Configured resolution: {config['main'].size}")
    elif 'main' in config and isinstance(config['main'], dict) and 'size' in config['main']:
        print(f"Configured resolution: {config['main']['size']}")
    else:
        print("Configured resolution not available.")

    imx500.show_network_fw_progress_bar()
    # Start headless (no preview window)
    picam2.start(config, show_preview=False)
    if intrinsics.preserve_aspect_ratio:
        imx500.set_auto_aspect_ratio()
    # Register the callback for processing each frame
    picam2.pre_callback = parse_and_draw_classification_results

    while True:
        time.sleep(0.5)
