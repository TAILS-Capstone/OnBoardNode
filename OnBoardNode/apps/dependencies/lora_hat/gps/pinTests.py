import os
import lgpio

# GPIO range you want to check (typically 0-27 for Raspberry Pi)
GPIO_PIN_RANGE = range(0, 28)

# Function to check if a GPIO pin is in use
def check_gpio_busy(pin):
    try:
        # Try to open the GPIO pin using lgpio
        handle = lgpio.gpiochip_open(0)  # Open the first GPIO chip
        lgpio.gpio_claim_input(handle, pin)  # Try to claim pin as input
        lgpio.gpiochip_close(handle)  # Release the handle
        return False  # Pin is not in use
    except lgpio.error as e:
        # If we catch an error, it means the pin is in use
        return True

def get_busy_pins():
    busy_pins = []

    # Iterate over GPIO pins to check if they're busy
    for pin in GPIO_PIN_RANGE:
        if check_gpio_busy(pin):
            busy_pins.append(pin)

    return busy_pins

def main():
    print("Checking for busy GPIO pins...")

    busy_pins = get_busy_pins()

    if busy_pins:
        print("The following GPIO pins are currently in use (busy):")
        for pin in busy_pins:
            print(f"GPIO{pin} is busy.")
    else:
        print("No GPIO pins are currently in use.")

if __name__ == "__main__":
    main()
