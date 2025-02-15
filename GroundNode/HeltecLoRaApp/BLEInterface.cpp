/* 
 * File:   BLEInterface.cpp
 * Author: JDazogbo
 *
 * Created on February 10, 2025, 11:31 AM
 */

 /*---------------- Include Files ------------------*/

#include <BLEInterface.h>

/*---------------- BLE Connection Callbacks Class Definition ------------------*/

// Constructor: Assigns the BLEInterface instance
BLEConnectionCallbacks::BLEConnectionCallbacks(BLEInterface *pInterface) {
    this->pInterface = pInterface;
}

// Called when a device connects
void BLEConnectionCallbacks::onConnect(BLEServer *pServer) {
    if (this->pInterface) {
        this->pInterface->setDeviceConnected(true);  
    }
}

// Called when a device disconnects
void BLEConnectionCallbacks::onDisconnect(BLEServer *pServer) {
    if (this->pInterface) {
        this->pInterface->setDeviceConnected(false);
    }
}


/*---------------- BLEInterface Class Definition ------------------*/

BLEInterface::BLEInterface(String deviceName, String serviceUUID, String characteristicUUID, String description) {
  
    // Create the BLE Device
    BLEDevice::init(deviceName);

    // Create the BLE Server
    this->pServer = BLEDevice::createServer();
    this->pServer->setCallbacks(new BLEConnectionCallbacks(this));

    // Create the BLE Service
    this->pService = this->pServer->createService(serviceUUID);

    // Create a BLE Characteristic
    this->pCharacteristic = this->pService->createCharacteristic(
    characteristicUUID,
    BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_NOTIFY | BLECharacteristic::PROPERTY_INDICATE
    );

    // Creates BLE Descriptor 0x2902: Client Characteristic Configuration Descriptor (CCCD)
    this->pCharacteristic->addDescriptor(new BLE2902());
    // Adds also the Characteristic User Description - 0x2901 descriptor
    descriptor_2901 = new BLE2901();
    descriptor_2901->setDescription(description);
    descriptor_2901->setAccessPermissions(ESP_GATT_PERM_READ);  // enforce read only - default is Read|Write
    this->pCharacteristic->addDescriptor(descriptor_2901);
}

BLEServer* BLEInterface::getBLEServer() {
    return this->pServer;
}

void BLEInterface::start() {

    // Start the service
    this->pService->start();

    // Start advertising
    this->pAdvertising = BLEDevice::getAdvertising();
    this->pAdvertising->addServiceUUID(this->pService->getUUID());
    this->pAdvertising->setScanResponse(false);
    this->pAdvertising->setMinPreferred(0x0);  // set value to 0x00 to not advertise this parameter
    BLEDevice::startAdvertising();
}

void BLEInterface::setDeviceConnected(bool connected) {
    this->deviceConnected = connected;
}

bool BLEInterface::isConnected() {
    return this->deviceConnected;
}

bool BLEInterface::deviceRecentlyDisconnected() {
    return !this->deviceConnected && this->oldDeviceConnected;
}

void BLEInterface::handleDisconnection() {
    if (this->deviceRecentlyDisconnected()) {
        this->oldDeviceConnected = this->deviceConnected;
        delay(500);                   // give the bluetooth stack the chance to get things ready
        BLEDevice::startAdvertising();
    }
}

bool BLEInterface::deviceRecentlyConnected() {
    return this->deviceConnected && !this->oldDeviceConnected;
}

void BLEInterface::handleReconnection() {
    if (this->deviceRecentlyConnected()) {
        this->oldDeviceConnected = this->deviceConnected;
    }
}

void BLEInterface::setValue(uint8_t value) {
    if (this->deviceConnected) {
        this->value = value;
        this->pCharacteristic->setValue((uint8_t *)&value, 4);
    }
}

uint32_t BLEInterface::getValue() {
    return this->value;
}

void BLEInterface::notify() {
    if (this->deviceConnected) {
        this->pCharacteristic->notify();
    }
}

