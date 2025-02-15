/* 
 * File:   HeltecLoRaApp.ino
 * Author: JDazogbo
 *
 * Created on February 10, 2025, 10:29 AM
 */

/*---------------- Include Files ------------------*/

#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <BLE2901.h>
#include <BLEInterface.h>

// See the following for generating UUIDs:
// https://www.uuidgenerator.net/

#define SERVICE_UUID        "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHARACTERISTIC_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"

BLEInterface* bleServer;

void setup() {
  Serial.begin(115200);
    
  // Initialize BLE Server
  bleServer = new BLEInterface("TailsStation", SERVICE_UUID, CHARACTERISTIC_UUID, "My characteristic description");
  
  // Start the BLE service
  bleServer->start();
  bleServer->setValue(0);
  Serial.println("Waiting for a client to connect...");

}

void loop() {
    // If device is connected, send notifications
    if (bleServer->isConnected()) {
        bleServer->setValue(bleServer->getValue() + 1);
        bleServer->notify();
        delay(1000);
    }

    // Handle device disconnection
    if (bleServer->deviceRecentlyDisconnected()) {
        Serial.println("Device disconnected!");
        bleServer->handleDisconnection();
        Serial.println("Waiting for a client to connect...");
    }

    // Handle device reconnection
    if (bleServer->deviceRecentlyConnected()) {
        bleServer->handleReconnection();
        Serial.println("Device connected!");
    }
}