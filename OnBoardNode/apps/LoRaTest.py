from LoRaRF import SX126x
import time

def ping_lora_devices():
    print("Checking for SX126x LoRa device...")
    
    try:
        lora = SX126x()
        lora.begin()
        print("SX126x series detected!")
        
        # Configure LoRa parameters
        lora.setFrequency(915000000)  # Set frequency to 915 MHz
        lora.setTxPower(22, lora.TX_POWER_SX1262)  # Set transmit power
        lora.setLoRaModulation(8, 125000, 5, False)  # Modulation settings
        
        # Send a ping message
        message = "Ping"
        message_bytes = [ord(c) for c in message]
        
        print("Sending ping...")
        lora.beginPacket()
        lora.write(message_bytes, len(message_bytes))
        lora.endPacket()
        
        # Wait and check for response
        print("Waiting for response...")
        time.sleep(2)  # Allow time for a response
        
        if lora.request():
            print("Response received!")
            response = ""
            while lora.available() > 0:
                response += chr(lora.read())
            print("Received message:", response)
        else:
            print("No response received.")
        
    except Exception as e:
        print("SX126x series not detected or error occurred:", e)

if __name__ == "__main__":
    ping_lora_devices()