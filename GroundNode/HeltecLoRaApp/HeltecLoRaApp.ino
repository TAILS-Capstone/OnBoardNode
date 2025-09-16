/*
 * File:   HeltecLoRaApp.ino
 * Author: JDazogbo
 *
 * Created on February 10, 2025, 10:29 AM
 */

/*---------------- Include Files ------------------*/

// BLE Includes
#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <BLE2901.h>
#include <BLEInterface.h>

// LoRa Includes
#include <LoRaInterface.h>

// Standard Bluetooth SIG Location and Navigation Service UUID
#define LOCATION_SERVICE_UUID "1819"
#define LOCATION_CHARACTERISTIC_UUID "2A67" // Location and Speed Characteristic

// Constants for fixed-point conversion
#define LAT_LON_SCALE 10000000 // 7 decimal places (0.0000001 degrees)
#define SPEED_SCALE 1000       // 3 decimal places (0.001 m/s)
#define HEADING_SCALE 100      // 2 decimal places (0.01 degrees)

BLEInterface *bleServer;

// Fake GPS coordinates for testing (in fixed-point format)
struct GPSLocation
{
    int32_t latitude;  // Scaled by LAT_LON_SCALE
    int32_t longitude; // Scaled by LAT_LON_SCALE
    int32_t speed;     // Scaled by SPEED_SCALE
    int32_t heading;   // Scaled by HEADING_SCALE
};

// Array of fake locations to simulate movement
// Values are pre-scaled to avoid any floating-point operations
GPSLocation locations[] = {
    {377749000, -1224194000, 0, 0},        // San Francisco (37.774900, -122.419400)
    {377833000, -1224167000, 5000, 9000},  // Moving east
    {377917000, -1224140000, 10000, 9000}, // Moving east faster
    {378000000, -1224113000, 5000, 18000}, // Moving south
    {378083000, -1224086000, 0, 27000},    // Moving west
    {378167000, -1224059000, 5000, 0}      // Moving north
};

int currentLocationIndex = 0;
const int NUM_LOCATIONS = sizeof(locations) / sizeof(locations[0]);

void setup()
{
    Serial.begin(115200);

    // Initialize BLE Server with Location and Navigation Service
    bleServer = new BLEInterface("TailsGPS", LOCATION_SERVICE_UUID, LOCATION_CHARACTERISTIC_UUID, "GPS Location Data");
    LoRaInterface loraServer(915000000, 22);
    // Start the BLE service
    bleServer->start();
    Serial.println("Waiting for a client to connect...");
}

void loop()
{
    // If device is connected, send location updates
    if (bleServer->isConnected())
    {
        // Check queue for messages
        LoRaInterface::checkMessageQueue();

        // Pack location data into a byte array
        uint8_t locationData[LoRaInterface::getRxSize()];

        // Store the packet in app memory
        LoRaInterface::getRxPacket(locationData);

        // Send location data
        bleServer->setValue(locationData, LoRaInterface::getRxSize());
        bleServer->notify();
    }

    // Handle device disconnection
    if (bleServer->deviceRecentlyDisconnected())
    {
        Serial.println("Device disconnected!");
        bleServer->handleDisconnection();
        Serial.println("Waiting for a client to connect...");
        
    }

    // Handle device reconnection
    if (bleServer->deviceRecentlyConnected())
    {
        bleServer->handleReconnection();
        Serial.println("Device connected!");
    }
}