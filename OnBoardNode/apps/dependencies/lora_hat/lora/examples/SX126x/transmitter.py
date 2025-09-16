import os, sys
currentdir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.dirname(os.path.dirname(currentdir)))
from LoRaRF import SX126x
import time

# Define all parameters upfront
busId = 0
csId = 0
resetPin = 18
busyPin = 20
irqPin = -1
txenPin = 6
rxenPin = -1

# RF parameters
frequency = 915000000  # 915 MHz
txPower = 22          # +22 dBm
txPowerVersion = SX126x.TX_POWER_SX1262

# Modulation parameters
sf = 7                # Spreading factor
bw = 125000          # Bandwidth 125 kHz
cr = 5               # Coding rate 4/5

# Packet parameters
headerType = SX126x.HEADER_EXPLICIT
preambleLength = 12
payloadLength = 15    # "HeLoRa World!\0" + counter byte
crcType = True
syncWord = 0x34

# Initialize LoRa
LoRa = SX126x()
print(f"Begin LoRa radio with:")
print(f"\tReset pin: {resetPin}")
print(f"\tBusy pin: {busyPin}")
print(f"\tIRQ pin: {irqPin}")
print(f"\tTXEN pin: {txenPin}")
print(f"\tRXEN pin: {rxenPin}")

# cold start
# LoRa.setSleep(SX126x.SLEEP_COLD_START)

if not LoRa.begin(busId, csId, resetPin, busyPin, irqPin, txenPin, rxenPin):
    raise Exception("Something wrong, can't begin LoRa radio")

LoRa.setDio2RfSwitch()

# Set frequency
print(f"Set frequency to {frequency/1000000} MHz")
LoRa.setFrequency(frequency)

# Set TX power
print(f"Set TX power to +{txPower} dBm")
LoRa.setTxPower(txPower, txPowerVersion)

# Configure modulation parameters
print("Set modulation parameters:")
print(f"\tSpreading factor = {sf}")
print(f"\tBandwidth = {bw/1000} kHz")
print(f"\tCoding rate = 4/{cr}")
LoRa.setLoRaModulation(sf, bw, cr)

# Configure packet parameters
print("Set packet parameters:")
print(f"\t{'Implicit' if headerType == SX126x.HEADER_IMPLICIT else 'Explicit'} header type")
print(f"\tPreamble length = {preambleLength}")
print(f"\tPayload Length = {payloadLength}")
print(f"\tCRC {'on' if crcType else 'off'}")
LoRa.setLoRaPacket(headerType, preambleLength, payloadLength, crcType)

# Set synchronize word
print(f"Set syncronize word to 0x{syncWord:02X}")
LoRa.setSyncWord(syncWord)

print("\n-- LoRa Transmitter --\n")

# Message to transmit
message = "HeLoRa World!\0"
messageList = list(message)
for i in range(len(messageList)):
    messageList[i] = ord(messageList[i])
counter = 0

# Transmit message continuously
while True:
    # Transmit message and counter
    LoRa.beginPacket()
    LoRa.write(messageList, len(messageList))
    LoRa.write([counter], 1)
    LoRa.endPacket()

    # Print message and counter
    print(f"{message}  {counter}")

    # Wait until modulation process for transmitting packet finish
    LoRa.wait()

    # Print transmit time and data rate
    print("Transmit time: {0:0.2f} ms | Data rate: {1:0.2f} byte/s".format(
        LoRa.transmitTime(), LoRa.dataRate()))

    # Don't load RF module with continuous transmit
    time.sleep(5)
    counter = (counter + 1) % 256

try:
    pass
except:
    LoRa.end()