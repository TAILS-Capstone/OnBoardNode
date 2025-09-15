/*
 * File:   LoRaInterface.h
 * Author: JDazogbo
 *
 * Created on September 11, 2025, 12:50 PM
 */

#ifndef LORAINTERFACE_H
#define LORAINTERFACE_H

/*---------------- Include Files ------------------*/

// LoRa imports
#include "LoRaWan_APP.h"
#include "Arduino.h"

// Utility Files
#include <string>

/*---------------- LoRa Parameters ------------------*/

#define RF_FREQUENCY 915000000 // Hz

#define TX_OUTPUT_POWER 22 // dBm

#define LORA_BANDWIDTH 0                 // [0: 125 kHz,
                                         //  1: 250 kHz,
                                         //  2: 500 kHz,
                                         //  3: Reserved]
#define LORA_SPREADING_FACTOR 7          // [SF7..SF12]
#define LORA_CODINGRATE 1                // [1: 4/5,
                                         //  2: 4/6,
                                         //  3: 4/7,
                                         //  4: 4/8]
#define LORA_PREAMBLE_LENGTH 12          // Same for Tx and Rx
#define LORA_SYMBOL_TIMEOUT 0            // Symbols
#define LORA_FIX_LENGTH_PAYLOAD_ON false // Needs to be false
#define LORA_IQ_INVERSION_ON false

#define RX_TIMEOUT_VALUE 1000
#define BUFFER_SIZE 15 // Define the payload size here

class LoRaInterface
{
public:
    static uint8_t txpacket[BUFFER_SIZE];
    static uint8_t rxpacket[BUFFER_SIZE];
    static RadioEvents_t RadioEvents;
    static int16_t txNumber;
    static int16_t rssi, rxSize;
    static bool lora_idle;

    LoRaInterface(uint32_t rfFrequency, uint8_t outputPower);

    static void checkMessageQueue();

    static uint8_t *getRxPacket();
    static int16_t getRssi();
    static int16_t getRxSize();
};

void onRxDone(uint8_t *payload, uint16_t size, int16_t rssi, int8_t snr);

#endif // LORAINTERFACE_H