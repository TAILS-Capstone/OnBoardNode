import spidev
import time

# SPI configuration
SPI_BUS = 0
SPI_DEVICE = 0  # Ensure this matches your wiring
SPI_SPEED = 1000000  # 1MHz
SPI_MODE = 0        # Mode 0

def main():
    spi = spidev.SpiDev()
    spi.open(SPI_BUS, SPI_DEVICE)
    spi.max_speed_hz = SPI_SPEED
    spi.mode = SPI_MODE

    # Test data pattern
    test_data = bytearray([0x55, 0xAA, 0xFF, 0x00])

    print("Starting SPI loopback test transmission...")
    while True:
        # Send test data and read back the response
        response = spi.xfer(test_data)
        print("Sent:", list(test_data), "Received:", list(response))
        time.sleep(1)

if __name__ == "__main__":
    main()
