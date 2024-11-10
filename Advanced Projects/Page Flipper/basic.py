import RPi.GPIO as GPIO
import time
from gpiozero import PWMOutputDevice, Servo

# Setup for GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# GPIO Pins
SUCTION_PUMP_PIN = 18         # PWM pin for controlling suction pump intensity
PAGE_TURN_SERVO_PIN = 17      # Pin for page turn servo
CAMERA_CLICK_SERVO_PIN = 27   # Pin for camera click servo
CAMERA_TRIGGER_ANGLE = -0.5   # Angle for servo pressing the capture button
PAGE_FLIP_ANGLE = 0.5         # Angle for flipping pages

# Initialize Suction Pump (PWM for variable suction)
suction_pump = PWMOutputDevice(SUCTION_PUMP_PIN)

# Initialize Servos
page_turn_servo = Servo(PAGE_TURN_SERVO_PIN)
camera_click_servo = Servo(CAMERA_CLICK_SERVO_PIN)

# Function to control suction pump intensity
def control_suction_pump(intensity):
    """
    Controls the suction pump intensity to pick one page.
    Intensity should be a float between 0 (off) and 1 (maximum).
    """
    suction_pump.value = intensity

# Function to lift and flip page
def flip_page():
    """
    Controls the suction pump and servo to flip a page.
    Adjusts suction intensity dynamically to pick only one page.
    """
    # Start with low suction and gradually increase until page is lifted
    for intensity in [i / 10 for i in range(1, 11)]:  # Gradually increase from 0.1 to 1.0
        control_suction_pump(intensity)
        time.sleep(0.1)
        # Check if single page is picked (based on testing, adjust intensity)
        # Here, we're assuming a delay and observing through testing; no sensor used.

    # Once page is lifted, move servo to flip the page
    page_turn_servo.value = PAGE_FLIP_ANGLE  # Move servo to flip the page
    time.sleep(1)  # Wait for the page to fully flip
    
    # Turn off suction pump and reset servo
    control_suction_pump(0)  # Turn off suction
    page_turn_servo.value = -PAGE_FLIP_ANGLE  # Reset servo position
    time.sleep(1)  # Allow time for the page to settle

# Function to capture image after page flip
def capture_image():
    """
    Activates the servo attached to a stylus to press the capture button on the phone screen.
    """
    camera_click_servo.value = CAMERA_TRIGGER_ANGLE  # Move servo to press capture button
    time.sleep(0.5)  # Hold for a short moment to register the press
    camera_click_servo.value = 0  # Reset servo to original position
    time.sleep(1)

# Main sequence to flip page and capture image
def page_flip_sequence():
    """
    Sequence to flip page and capture an image.
    This process repeats based on the required number of pages.
    """
    try:
        total_pages = int(input("Enter the total number of pages to flip: "))
        for page in range(total_pages):
            print(f"Flipping page {page + 1}")
            flip_page()  # Flip page
            capture_image()  # Capture image with phone camera

    except KeyboardInterrupt:
        print("Operation interrupted by user.")

    finally:
        # Cleanup GPIO
        suction_pump.value = 0  # Ensure suction pump is off
        page_turn_servo.value = 0  # Reset servo
        camera_click_servo.value = 0  # Reset camera click servo
        GPIO.cleanup()

if __name__ == "__main__":
    # Run the page flip and capture sequence
    page_flip_sequence()
