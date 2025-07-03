# TAILS Embedded System README

**Firmware Development for Tactical Aerial Insight and Localization Suite (TAILS)**  
By Frederick Andrews, Jad Mghabghab, Josué Dazogbo, Maureen Kouassi, Mouad Ben Lahbib,  Computer Engineering Students at the University of Ottawa  
Date: 3 July 2025

## Overview

This repository contains the embedded software developed for the **TAILS** (Tactical Aerial Insight and Localization Suite) system. The embedded code runs on a [Heltec WiFi LoRa 32 (V3)](https://heltec.org/project/wifi-lora-32-v3/) board and is responsible for communication, telemetry, and interfacing with onboard sensors (e.g. GPS, IMU). The firmware enables reliable transmission of drone location and sensor data via LoRa to a centralized receiver station.

The project is written in C++ and built using the [Arduino framework](https://www.arduino.cc/), targeting a modified ESP32 microcontroller, with additional support for SX1262-based LoRa modules and UBlox GPS receivers.

## Features
- 🧠 **AI Object Detection & POI Recognition**: Point of Interest (POI) object detection enables automated identification of key landmarks or objects; selectable via configuration on mobile app.
- 🛰️ **LoRa Telemetry Transmission**: Real-time transmission of position and altitude data.
- 📍 **GPS Integration**: Reads NMEA sentences and parses location data from UBlox modules.
- 📡 **BLE Peripheral Support**: Allows configuration and basic diagnostics over BLE.

## Repository Structure

```bash
TAILS-Embedded/
├── GroundNode/
│   └── HeltecLoRaApp/      # Firmware for the base station (LoRa to BLE)
├── OnBoardNode/            # Embedded code running on the drone’s board
├── installs-Yolov8.text    # Instructions for installing YOLOv8 dependencies
└── README.md               # This document
```

