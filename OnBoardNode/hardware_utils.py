#!/usr/bin/env python3
import time
import logging
import os

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    logging.warning("RPi.GPIO library not found. GPIO functionalities will be disabled.")

try:
    from picamera2 import Picamera2, Preview
    CAMERA_AVAILABLE = True
except ImportError:
    CAMERA_AVAILABLE = False
    logging.warning("Picamera2 library not found. Camera functionalities will be disabled.")

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    logging.warning("pySerial library not found. GPS functionalities will be disabled.")

import cv2
import numpy as np

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class CameraController:
    def __init__(self):
        if not CAMERA_AVAILABLE:
            raise ImportError("Picamera2 library is required for CameraController")
        self.picam2 = Picamera2()
        self.config = self.picam2.create_preview_configuration()
        self.picam2.configure(self.config)
        logging.info("Camera configured with preview configuration.")

    def start_preview(self):
        self.picam2.start_preview(Preview.QT)
        logging.info("Camera preview started.")

    def capture_frame(self):
        frame = self.picam2.capture_array()
        logging.debug("Captured frame of shape: %s", frame.shape)
        return frame

    def stop_camera(self):
        self.picam2.stop()
        logging.info("Camera stopped.")

class GPIOController:
    def __init__(self):
        if not GPIO_AVAILABLE:
            raise ImportError("RPi.GPIO library is required for GPIOController")
        GPIO.setmode(GPIO.BCM)
        logging.info("GPIO set to BCM mode.")

    def setup_pin(self, pin, direction=GPIO.OUT, initial=GPIO.LOW):
        GPIO.setup(pin, direction, initial=initial)
        logging.info("Pin %d set up as %s with initial state %s.", pin, "OUTPUT" if direction == GPIO.OUT else "INPUT", initial)

    def write_pin(self, pin, value):
        GPIO.output(pin, value)
        logging.debug("Pin %d set to %s.", pin, "HIGH" if value == GPIO.HIGH else "LOW")

    def read_pin(self, pin):
        value = GPIO.input(pin)
        logging.debug("Pin %d read as %s.", pin, "HIGH" if value == GPIO.HIGH else "LOW")
        return value

    def cleanup(self):
        GPIO.cleanup()
        logging.info("GPIO cleanup performed.")

class GPSController:
    def __init__(self, port='/dev/ttyAMA0', baudrate=9600, timeout=1):
        if not SERIAL_AVAILABLE:
            raise ImportError("pySerial is required for GPSController")
        self.port = port
        self.baudrate = baudrate
        try:
            self.ser = serial.Serial(port, baudrate, timeout=timeout)
            logging.info("Connected to GPS on port %s at %d baud.", port, baudrate)
        except serial.SerialException as e:
            logging.error("Failed to connect to GPS: %s", e)
            self.ser = None

    def read_line(self):
        if self.ser and self.ser.is_open:
            line = self.ser.readline().decode('ascii', errors='replace').strip()
            logging.debug("GPS data: %s", line)
            return line
        else:
            logging.warning("GPS serial port is not open.")
            return None

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            logging.info("GPS serial port closed.")

def process_image(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    processed = cv2.GaussianBlur(gray, (5, 5), 0)
    logging.debug("Processed image with Gaussian blur.")
    return processed

def dummy_inference(frame):
    mean_intensity = np.mean(frame)
    result = {"mean_intensity": mean_intensity, "timestamp": time.time()}
    logging.debug("Dummy inference result: %s", result)
    return result

if __name__ == '__main__':
    logging.info("Starting hardware utilities demo.")

    if CAMERA_AVAILABLE:
        try:
            camera = CameraController()
            time.sleep(1)
            frame = camera.capture_frame()
            processed = process_image(frame)
            inference_result = dummy_inference(processed)
            logging.info("Inference result: %s", inference_result)
            camera.stop_camera()
        except Exception as e:
            logging.error("Camera error: %s", e)
    else:
        logging.info("Camera functionalities not available.")

    if GPIO_AVAILABLE:
        try:
            gpio_ctrl = GPIOController()
            test_pin = 18
            gpio_ctrl.setup_pin(test_pin, GPIO.OUT, initial=GPIO.LOW)
            gpio_ctrl.write_pin(test_pin, GPIO.HIGH)
            time.sleep(1)
            gpio_ctrl.write_pin(test_pin, GPIO.LOW)
            gpio_ctrl.cleanup()
        except Exception as e:
            logging.error("GPIO error: %s", e)
    else:
        logging.info("GPIO functionalities not available.")

    if SERIAL_AVAILABLE:
        try:
            gps_ctrl = GPSController()
            for _ in range(5):
                data = gps_ctrl.read_line()
                if data:
                    logging.info("GPS Data: %s", data)
                time.sleep(1)
            gps_ctrl.close()
        except Exception as e:
            logging.error("GPS error: %s", e)
    else:
        logging.info("GPS functionalities not available.")

    logging.info("Hardware utilities demo finished.")
