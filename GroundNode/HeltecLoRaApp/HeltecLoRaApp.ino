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

// Standard Bluetooth SIG Location and Navigation Service UUID
#define LOCATION_SERVICE_UUID        "1819"
#define LOCATION_CHARACTERISTIC_UUID "2A67"  // Location and Speed Characteristic

// Constants for fixed-point conversion
#define LAT_LON_SCALE 10000000  // 7 decimal places (0.0000001 degrees)
#define SPEED_SCALE 1000        // 3 decimal places (0.001 m/s)
#define HEADING_SCALE 100       // 2 decimal places (0.01 degrees)

BLEInterface* bleServer;

// Fake GPS coordinates for testing (in fixed-point format)
struct GPSLocation {
    int32_t latitude;    // Scaled by LAT_LON_SCALE
    int32_t longitude;   // Scaled by LAT_LON_SCALE
    int32_t speed;      // Scaled by SPEED_SCALE
    int32_t heading;    // Scaled by HEADING_SCALE
};

// Array of fake locations to simulate movement
// Values are pre-scaled to avoid any floating-point operations
GPSLocation locations[] = {
    {377749000, -1224194000, 0, 0},      // San Francisco (37.774900, -122.419400)
    {377833000, -1224167000, 5000, 9000}, // Moving east
    {377917000, -1224140000, 10000, 9000}, // Moving east faster
    {378000000, -1224113000, 5000, 18000}, // Moving south
    {378083000, -1224086000, 0, 27000},    // Moving west
    {378167000, -1224059000, 5000, 0}      // Moving north
};

int currentLocationIndex = 0;
const int NUM_LOCATIONS = sizeof(locations) / sizeof(locations[0]);

void setup() {
    Serial.begin(115200);
    
    // Initialize BLE Server with Location and Navigation Service
    bleServer = new BLEInterface("TailsGPS", LOCATION_SERVICE_UUID, LOCATION_CHARACTERISTIC_UUID, "GPS Location Data");
    
    // Start the BLE service
    bleServer->start();
    Serial.println("Waiting for a client to connect...");
}

void loop() {
    // If device is connected, send location updates
    if (bleServer->isConnected()) {
        // Get current location
        GPSLocation& loc = locations[currentLocationIndex];
        
        // Pack location data into a byte array
        uint8_t locationData[16];
        
        // Latitude (4 bytes)
        locationData[0] = loc.latitude & 0xFF;
        locationData[1] = (loc.latitude >> 8) & 0xFF;
        locationData[2] = (loc.latitude >> 16) & 0xFF;
        locationData[3] = (loc.latitude >> 24) & 0xFF;
        
        // Longitude (4 bytes)
        locationData[4] = loc.longitude & 0xFF;
        locationData[5] = (loc.longitude >> 8) & 0xFF;
        locationData[6] = (loc.longitude >> 16) & 0xFF;
        locationData[7] = (loc.longitude >> 24) & 0xFF;
        
        // Speed (4 bytes) - in mm/s (0.001 m/s resolution)
        locationData[8] = loc.speed & 0xFF;
        locationData[9] = (loc.speed >> 8) & 0xFF;
        locationData[10] = (loc.speed >> 16) & 0xFF;
        locationData[11] = (loc.speed >> 24) & 0xFF;
        
        // Heading (4 bytes) - in 0.01 degrees
        locationData[12] = loc.heading & 0xFF;
        locationData[13] = (loc.heading >> 8) & 0xFF;
        locationData[14] = (loc.heading >> 16) & 0xFF;
        locationData[15] = (loc.heading >> 24) & 0xFF;
        
        // Send location data
        bleServer->setValue(locationData, 16);
        bleServer->notify();
        
        // Print location for debugging (convert back to human-readable format)
        Serial.print("Location: ");
        Serial.print((float)loc.latitude / LAT_LON_SCALE, 7);
        Serial.print(", ");
        Serial.print((float)loc.longitude / LAT_LON_SCALE, 7);
        Serial.print(" Speed: ");
        Serial.print((float)loc.speed / SPEED_SCALE, 3);
        Serial.print(" m/s Heading: ");
        Serial.print((float)loc.heading / HEADING_SCALE, 2);
        Serial.println("°");
        
        // Move to next location
        currentLocationIndex = (currentLocationIndex + 1) % NUM_LOCATIONS;
        
        delay(2000);  // Update every 2 seconds
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