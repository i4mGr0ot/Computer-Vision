import RPi.GPIO as GPIO
import time
import cv2
import pytesseract
import boto3
from fpdf import FPDF
from threading import Thread
import os
from io import BytesIO
from PIL import Image

# Setup GPIO for motors and suction pump
GPIO.setmode(GPIO.BCM)

# Pins configuration
SUCTION_PUMP_PIN = 18        # Suction pump motor
PAGE_FLIP_MOTOR_PIN = 23     # Page flipping motor
LOAD_SENSOR_PIN = 24         # To detect multiple pages picked

# Initialize GPIO
GPIO.setup(SUCTION_PUMP_PIN, GPIO.OUT)
GPIO.setup(PAGE_FLIP_MOTOR_PIN, GPIO.OUT)
GPIO.setup(LOAD_SENSOR_PIN, GPIO.IN)

# Suction Pump PWM setup
suction_pwm = GPIO.PWM(SUCTION_PUMP_PIN, 100)  # 100 Hz frequency
suction_pwm.start(0)  # Start with 0% duty cycle

# Initialize AWS S3 client
s3 = boto3.client('s3')
BUCKET_NAME = 'your-aws-s3-bucket-name'

def calibrate_suction():
    """Calibrate suction to ensure one page is picked up."""
    max_retries = 3
    retries = 0

    while retries < max_retries:
        for intensity in range(10, 101, 10):  # Gradually increase suction intensity
            suction_pwm.ChangeDutyCycle(intensity)
            time.sleep(0.5)  # Allow suction to stabilize
            
            # Check if only one page is picked using a load sensor or page thickness detector
            if GPIO.input(LOAD_SENSOR_PIN) == 0:  # Page is successfully picked
                print(f"Suction calibrated at {intensity}% duty cycle.")
                return intensity  # Return the working suction intensity

        retries += 1
        print(f"Retrying suction calibration ({retries}/{max_retries})")

    raise Exception("Failed to calibrate suction - Multiple pages detected.")

def extract_metadata(image):
    """Extract name, class, section, and page count using OCR."""
    max_retries = 2
    retries = 0
    while retries < max_retries:
        try:
            text = pytesseract.image_to_string(image)
            # Parse extracted text for student name, class, section, and page count
            name = parse_name(text)
            class_section = parse_class_section(text)
            page_count = parse_page_count(text)
            return name, class_section, page_count
        except Exception as e:
            print(f"Error extracting metadata: {e}")
            retries += 1
            if retries == max_retries:
                raise Exception("Failed to extract metadata after multiple attempts.")

def parse_name(text):
    """Parse OCR text for student name."""
    # Implement the parsing logic based on the answer sheet format
    return "John Doe"

def parse_class_section(text):
    """Parse OCR text for class and section."""
    # Implement parsing logic
    return "Class 7 - A"

def parse_page_count(text):
    """Parse OCR text for total page count."""
    return int(text.split("Total Pages:")[1].strip())

def capture_and_validate_page(page_number):
    """Capture and validate the current page's image."""
    image_buffer = BytesIO()
    camera = cv2.VideoCapture(0)  # Initialize camera
    
    ret, frame = camera.read()
    if ret:
        # Convert captured frame to PIL image and save it in-memory (to reduce disk I/O)
        image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        image.save(image_buffer, format='JPEG')
        image_buffer.seek(0)

        if validate_image(image_buffer):
            print(f"Page {page_number} captured successfully.")
            return image_buffer
    else:
        raise Exception("Failed to capture image.")

def validate_image(image_buffer):
    """Validate the quality of the captured image."""
    image = Image.open(image_buffer).convert('L')  # Convert to grayscale
    focus_measure = cv2.Laplacian(cv2.cvtColor(np.array(image), cv2.COLOR_GRAY2BGR), cv2.CV_64F).var()
    return focus_measure > 100  # Threshold for image clarity

def create_and_upload_pdf(image_buffers, student_name, class_section):
    """Create PDF from images and upload it to AWS S3."""
    pdf = FPDF()
    for image_buffer in image_buffers:
        # Add each page as an image in the PDF
        pdf.add_page()
        image = Image.open(image_buffer)
        image.save("/tmp/temp_image.jpg")  # Temporarily save the image to disk (FPDF doesn't support in-memory)
        pdf.image("/tmp/temp_image.jpg", 0, 0, 210, 297)  # A4 size

    # Create the PDF in memory (instead of saving to disk)
    pdf_output = BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)

    # Upload the PDF to AWS S3
    s3_key = f"{class_section}/{student_name}.pdf"
    try:
        s3.upload_fileobj(pdf_output, BUCKET_NAME, s3_key)
        print(f"PDF uploaded successfully to S3: {s3_key}")
    except Exception as e:
        raise Exception(f"Failed to upload PDF to S3: {e}")

def scan_answer_sheets(total_sheets):
    """Main loop to scan multiple answer sheets."""
    for i in range(total_sheets):
        try:
            print(f"Scanning Answer Sheet {i + 1}")

            # Lift and calibrate the suction pump for the top answer sheet
            calibrate_suction()

            # Extract metadata from the first page (name, class, etc.)
            first_page = capture_and_validate_page(1)
            name, class_section, page_count = extract_metadata(first_page)

            # Capture and validate remaining pages
            image_buffers = [first_page]
            threads = []
            for page in range(2, page_count + 1):
                t = Thread(target=lambda p: image_buffers.append(capture_and_validate_page(p)), args=(page,))
                t.start()
                threads.append(t)

            # Wait for all threads to complete
            for t in threads:
                t.join()

            # Create PDF and upload to AWS S3
            create_and_upload_pdf(image_buffers, name, class_section)

            # Move the completed sheet to the right pile
            move_to_right_pile()

        except Exception as e:
            print(f"Error scanning sheet {i + 1}: {e}")
            retry_scan(i + 1)  # Retry the current sheet

def move_to_right_pile():
    """Move the scanned answer sheet to the right side."""
    GPIO.output(PAGE_FLIP_MOTOR_PIN, 1)
    time.sleep(1)
    GPIO.output(PAGE_FLIP_MOTOR_PIN, 0)
    print("Moved answer sheet to the right.")

def retry_scan(sheet_number):
    """Retry scanning the current answer sheet."""
    print(f"Retrying scan for Answer Sheet {sheet_number}")
    try:
        scan_answer_sheets(sheet_number)
    except Exception as e:
        print(f"Retry failed: {e}")

if __name__ == "__main__":
    try:
        total_sheets = int(input("Enter total number of answer sheets: "))
        scan_answer_sheets(total_sheets)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Cleanup GPIO to release resources properly
        suction_pwm.stop()
        GPIO.cleanup()
        print("System shutdown. GPIO resources released.")
