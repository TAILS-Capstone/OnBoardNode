/*
 * File:   LoRaInterface.c
 * Author: JDazogbo
 *
 * Created on September 11, 2025, 1:31 PM
 */

/*---------------- Include Files ------------------*/

#include <LoRaInterface.h>

uint8_t LoRaInterface::txpacket[BUFFER_SIZE];
uint8_t LoRaInterface::rxpacket[BUFFER_SIZE];
RadioEvents_t LoRaInterface::RadioEvents;

int16_t LoRaInterface::txNumber;
int16_t LoRaInterface::rssi;
int16_t LoRaInterface::rxSize;
bool LoRaInterface::lora_idle;

// Free function callback for RxDone
void onRxDone(uint8_t *payload, uint16_t size, int16_t rssi, int8_t snr)
{
    memcpy(LoRaInterface::rxpacket, payload, size);
    LoRaInterface::rxpacket[size] = '\0';
    LoRaInterface::rssi = rssi;
    LoRaInterface::rxSize = size;
    Radio.Sleep();
    LoRaInterface::lora_idle = true;
}

/*---------------- LoRa Module Class Declaration ------------------*/

LoRaInterface::LoRaInterface(uint32_t rfFrequency, uint8_t outputPower)
{
    Mcu.begin(HELTEC_BOARD, SLOW_CLK_TPYE);
    txNumber = 0;
    rssi = 0;
    lora_idle = true;
    RadioEvents.RxDone = onRxDone;
    Radio.Init(&RadioEvents);
    Radio.SetChannel(rfFrequency);
    Radio.SetPublicNetwork(true);
    Radio.SetRxConfig(MODEM_LORA, LORA_BANDWIDTH, LORA_SPREADING_FACTOR,
                      LORA_CODINGRATE, 0, LORA_PREAMBLE_LENGTH,
                      LORA_SYMBOL_TIMEOUT, LORA_FIX_LENGTH_PAYLOAD_ON,
                      BUFFER_SIZE, true, 0, 0, LORA_IQ_INVERSION_ON, true);
}

void LoRaInterface::checkMessageQueue()
{
    if (lora_idle)
    {
        lora_idle = false;
        Radio.Rx(0);
    }
    Radio.IrqProcess();
}

void LoRaInterface::getRxPacket(uint8_t *dataLoc)
{
    if (LoRaInterface::rxSize > 0)
    {
        // Print before and after execution
        memcpy(dataLoc, LoRaInterface::rxpacket, LoRaInterface::rxSize);
    }
    else
    {
        dataLoc = nullptr;
    }
}

int16_t LoRaInterface::getRssi()
{
    return LoRaInterface::rssi;
}

int16_t LoRaInterface::getRxSize()
{
    return LoRaInterface::rxSize;
}