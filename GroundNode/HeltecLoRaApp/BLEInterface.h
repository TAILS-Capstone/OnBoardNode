/* 
 * File:   BLEInterface.h
 * Author: JDazogbo
 *
 * Created on February 10, 2025, 11:15 AM
 */

#ifndef BLEINTERFACE_H
#define	BLEINTERFACE_H


/*---------------- Include Files ------------------*/

// Bluetooth Related Imports for ESP32
#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <BLE2901.h>

// Utility Files
#include <string>

/*---------------- BLE Server Class Declaration ------------------*/

class BLEInterface {

private:

    BLEServer *pServer;
    BLEService *pService;
    BLECharacteristic *pCharacteristic;
    BLEAdvertising *pAdvertising;
    BLE2901 *descriptor_2901;

    bool deviceConnected = false;
    bool oldDeviceConnected = false;
    uint8_t value = 0;
    
public:

    // Constructor
    BLEInterface(String deviceName, String serviceUUID, String characteristicUUID, String description);

    // Getter For the BLEServer
    BLEServer* getBLEServer();
        
    // Start the BLE Server
    void start();

    // Sets the device Connection Status
    void setDeviceConnected(bool connected);
            
    // Check if a device is connected
    bool isConnected();
    
    // Check if device recently disconnected
    bool deviceRecentlyDisconnected();

    // Handles Disconnection of BLE Device
    void handleDisconnection();

    // Check if device recently connected
    bool deviceRecentlyConnected();

    // Handles Reconnection of BLE Device
    void handleReconnection();

    // Set the Characteristic Value (single byte)
    void setValue(uint8_t value);

    // Set the Characteristic Value (array of bytes)
    void setValue(uint8_t* data, size_t length);

    // Get the Characteristic Value
    uint32_t getValue();

    // Notify the device of a new value
    void notify();

};

/*---------------- BLE Connection Callbacks Class Declaration ------------------*/

// BLEConnectionCallbacks class to handle connection events
class BLEConnectionCallbacks : public BLEServerCallbacks {
private:
    BLEInterface *pInterface;  // Pointer to BLEInterface instance

public:
    BLEConnectionCallbacks(BLEInterface *pInterface);  // Constructor
    void onConnect(BLEServer *pServer);  // Handles connection event
    void onDisconnect(BLEServer *pServer);  // Handles disconnection event
};





#endif	/* BLEINTERFACE_H */