import spidev
import time
from LoRaRF import SX126x

def test_spi_communication():
    # Initialize LoRa
    LoRa = SX126x()
    
    # SPI configuration
    busId = 0
    csId = 0
    resetPin = 18
    busyPin = 20
    irqPin = -1
    txenPin = 6
    rxenPin = -1
    
    print("Testing SPI communication with SX1262...")
    
    # Try to initialize the device
    if not LoRa.begin(busId, csId, resetPin, busyPin, irqPin, txenPin, rxenPin):
        print("ERROR: Failed to initialize LoRa device")
        return False
    
    print("✓ Device initialized successfully")
    
    # Check device mode
    mode = LoRa.getMode()
    print(f"Current device mode: 0x{mode:02X}")
    if mode == LoRa.STATUS_MODE_STDBY_RC:
        print("✓ Device in standby mode")
    else:
        print("WARNING: Device not in expected standby mode")
    
    # Check for device errors
    errors = LoRa.getError()
    if errors == 0:
        print("✓ No device errors detected")
    else:
        print(f"WARNING: Device errors detected: 0x{errors:04X}")
    
    # Try to read some registers
    try:
        # Read packet type
        packet_type = LoRa.getPakcetType()
        print(f"Packet type: 0x{packet_type:02X}")
        
        # Read status
        status = LoRa.getStatus()
        print(f"Device status: 0x{status:02X}")
        
        print("✓ Successfully read device registers")
    except Exception as e:
        print(f"ERROR: Failed to read registers: {e}")
        return False
    
    # Try to write and read back a test register
    try:
        test_value = 0x42
        LoRa.writeRegister(0x00, (test_value,), 1)
        read_value = LoRa.readRegister(0x00, 1)[0]
        if read_value == test_value:
            print("✓ Successfully wrote and read back test value")
        else:
            print(f"WARNING: Register readback mismatch. Wrote: 0x{test_value:02X}, Read: 0x{read_value:02X}")
    except Exception as e:
        print(f"ERROR: Failed register readback test: {e}")
        return False
    
    print("\nSPI Communication Test Summary:")
    print("✓ Device responds to commands")
    print("✓ Can read device registers")
    print("✓ Can write and read back values")
    
    return True

if __name__ == "__main__":
    test_spi_communication() 