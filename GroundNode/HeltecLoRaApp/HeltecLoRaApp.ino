#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

BLEServer *pServer = nullptr;
BLECharacteristic *pTxCharacteristic = nullptr;
bool deviceConnected = false;
bool oldDeviceConnected = false;

// UUIDs for BLE UART Service (Nordic UART)
#define SERVICE_UUID           "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
#define CHARACTERISTIC_UUID_RX "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"  // Receiving data
#define CHARACTERISTIC_UUID_TX "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"  // Sending data

// BLE Connection Callbacks
class MyServerCallbacks : public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) {
        deviceConnected = true;
    }

    void onDisconnect(BLEServer* pServer) {
        deviceConnected = false;
    }
};

// BLE Receive Data Callback
class MyCallbacks : public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic *pCharacteristic) {
        String rxValue = pCharacteristic->getValue().c_str(); // Use Arduino String

        if (rxValue.length() > 0) {
            Serial.print("Received: ");
            Serial.println(rxValue);  // Print to Serial Monitor
        }

    }
};

void setup() {
    Serial.begin(115200);
    Serial.println("Starting Secure Bluetooth...");

    // Initialize BLE Device
    BLEDevice::init("Heltec_LoRa_V3");

    // Set security parameters
    BLESecurity *pSecurity = new BLESecurity();
    pSecurity->setAuthenticationMode(ESP_LE_AUTH_REQ_SC_BOND); // Secure bonding
    pSecurity->setCapability(ESP_IO_CAP_NONE); // No input/output (Just works pairing)
    pSecurity->setInitEncryptionKey(ESP_BLE_ENC_KEY_MASK | ESP_BLE_ID_KEY_MASK); // Encryption keys

    // Create BLE Server
    pServer = BLEDevice::createServer();
    pServer->setCallbacks(new MyServerCallbacks());

    // Create BLE Service
    BLEService *pService = pServer->createService(SERVICE_UUID);

    // Create BLE TX Characteristic (For sending data)
    pTxCharacteristic = pService->createCharacteristic(
                            CHARACTERISTIC_UUID_TX,
                            BLECharacteristic::PROPERTY_NOTIFY
                        );
    pTxCharacteristic->addDescriptor(new BLE2902());

    // Create BLE RX Characteristic (For receiving data)
    BLECharacteristic *pRxCharacteristic = pService->createCharacteristic(
                            CHARACTERISTIC_UUID_RX,
                            BLECharacteristic::PROPERTY_WRITE
                        );
    pRxCharacteristic->setCallbacks(new MyCallbacks());

    // Start the service
    pService->start();

    // Start advertising Bluetooth
    pServer->getAdvertising()->start();
    Serial.println("Secure Bluetooth Ready! Waiting for connections...");
}

void loop() {
    // Send data if device is connected
    if (deviceConnected) {
        String message = "Hello from ESP32!";
        pTxCharacteristic->setValue(message.c_str()); // Send string as char array
        pTxCharacteristic->notify(); // Notify connected device
        Serial.println("Sent: " + message);
        delay(1000); // Send every second
    }

    // Reconnect if disconnected
    if (!deviceConnected && oldDeviceConnected) {
        delay(500);
        pServer->startAdvertising();
        Serial.println("Restarting advertising...");
        oldDeviceConnected = deviceConnected;
    }

    // Handle new connection
    if (deviceConnected && !oldDeviceConnected) {
        oldDeviceConnected = deviceConnected;
        Serial.println("Attempting to Connect to old device...");
    }
}
