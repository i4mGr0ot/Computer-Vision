import RPi.GPIO as GPIO
import time
import cv2
import pytesseract
from PIL import Image, ImageEnhance
from fpdf import FPDF
import os
import boto3
import logging

# AWS S3 setup (replace with your credentials)
s3 = boto3.client('s3')
bucket_name = 'your-s3-bucket-name'

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Raspberry Pi GPIO Pin Configuration
MOTOR_PIN = 18  # Example GPIO pin for the motor control (PWM)
SUCTION_PIN = 23  # Pin to control the suction valve
SENSOR_PIN = 24  # Pin to receive feedback (optional, for suction intensity)
CAMERA_TRIGGER_PIN = 25  # Pin to trigger Arducam capture

# GPIO setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(MOTOR_PIN, GPIO.OUT)
GPIO.setup(SUCTION_PIN, GPIO.OUT)
GPIO.setup(SENSOR_PIN, GPIO.IN)
GPIO.setup(CAMERA_TRIGGER_PIN, GPIO.OUT)

# PWM setup for motor control
motor_pwm = GPIO.PWM(MOTOR_PIN, 100)  # 100 Hz frequency
motor_pwm.start(0)  # Start with 0 duty cycle (off)

# Arducam setup
# Initialize camera (assuming Arducam SDK is installed)
import ArducamSDK as arducam
camera_handle = None  # Camera initialization goes here

# Define image parameters
image_width = 1920
image_height = 1080
capture_mode = 0x02  # Example capture mode for Arducam (adjust as necessary)

# Image validation parameters
MIN_RESOLUTION = (1000, 1000)

class ExamSheetRobot:
    def __init__(self, total_answer_sheets):
        self.total_answer_sheets = total_answer_sheets
        self.processed_answer_sheets = 0
        self.pages = {}
        self.total_pages = 0
        self.first_page_info = None  # To store extracted info from the first page
        self.suction_intensity = None  # Calibrated during first page flip

    def arducam_capture_image(self):
        """
        Capture an image using Arducam controlled via Raspberry Pi GPIO.
        """
        GPIO.output(CAMERA_TRIGGER_PIN, GPIO.HIGH)
        # Capture image logic using Arducam SDK (simplified)
        frame = arducam.capture(camera_handle, capture_mode)
        image = cv2.imdecode(frame, cv2.IMREAD_COLOR)
        GPIO.output(CAMERA_TRIGGER_PIN, GPIO.LOW)
        return image

    def validate_image(self, image):
        """
        Validate the image quality by checking resolution.
        """
        height, width = image.shape[:2]
        if (width, height) < MIN_RESOLUTION:
            logging.error("Image resolution is too low. Retry capturing.")
            return False
        return True

    def process_image(self, image):
        """
        Preprocess the image to enhance quality for OCR.
        """
        pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        enhancer = ImageEnhance.Contrast(pil_image)
        enhanced_image = enhancer.enhance(2.0)
        return cv2.cvtColor(np.array(enhanced_image), cv2.COLOR_RGB2BGR)

    def extract_info_from_first_page(self, image):
        """
        Use OCR to extract student's name, class, and subject from the first page.
        """
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        text = pytesseract.image_to_string(gray_image)

        # Assuming the first three lines are name, class, and subject
        lines = text.split('\n')
        name = lines[0].strip()
        class_section = lines[1].strip()
        subject = lines[2].strip()

        if not name or not class_section or not subject:
            raise Exception("Failed to extract info from the first page.")

        self.first_page_info = {'name': name, 'class_section': class_section, 'subject': subject}
        logging.info(f"Extracted: Name: {name}, Class: {class_section}, Subject: {subject}")

    def calibrate_suction(self):
        """
        Calibrate the suction intensity based on the first page's thickness.
        """
        logging.info("Calibrating suction for the first page...")
        motor_pwm.ChangeDutyCycle(50)  # Example initial suction power

        while GPIO.input(SENSOR_PIN) == 0:  # Wait for page to be grabbed
            time.sleep(0.1)  # Adjust based on suction speed

        # Record suction intensity and apply to future pages
        self.suction_intensity = 50  # Example value (can be adjusted based on feedback)
        motor_pwm.ChangeDutyCycle(0)  # Stop suction after grabbing

    def flip_page(self):
        """
        Flip a page using suction control.
        """
        logging.info("Flipping page using suction mechanism.")
        motor_pwm.ChangeDutyCycle(self.suction_intensity)
        time.sleep(2)  # Adjust time based on actual suction motor speed
        motor_pwm.ChangeDutyCycle(0)

    def capture_all_pages(self):
        """
        Capture all pages of the answer sheet and organize them.
        """
        page_number = 1
        if self.suction_intensity is None:
            self.calibrate_suction()

        while True:
            logging.info(f"Capturing page {page_number}")
            image = self.arducam_capture_image()
            processed_image = self.process_image(image)

            if not self.validate_image(processed_image):
                logging.error("Image failed validation. Retrying capture.")
                continue

            if page_number == 1:
                self.extract_info_from_first_page(processed_image)

            # Store valid page
            self.pages[page_number] = processed_image

            # Flip to next page
            self.flip_page()
            page_number += 1

            more_pages = input("Is there another page? (y/n): ").lower() != 'y'
            if more_pages:
                break

        self.total_pages = page_number - 1
        logging.info(f"Captured {self.total_pages} pages.")

    def organize_pages(self):
        """
        Ensure pages are ordered before saving them as PDF.
        """
        self.pages = {key: self.pages[key] for key in sorted(self.pages)}
        logging.info("Pages organized in correct sequence.")

    def save_as_pdf(self, pdf_filename):
        """
        Convert captured images into a PDF document.
        """
        pdf = FPDF()
        for page_num in sorted(self.pages.keys()):
            temp_filename = f"temp_page_{page_num}.jpg"
            cv2.imwrite(temp_filename, self.pages[page_num])

            pdf.add_page()
            pdf.image(temp_filename, x=10, y=10, w=190)
            os.remove(temp_filename)

        pdf.output(pdf_filename)

    def upload_to_cloud(self, pdf_filename):
        """
        Upload the generated PDF to the cloud (AWS S3).
        """
        student_name = self.first_page_info['name'].replace(' ', '_')
        object_name = f"{student_name}_answersheet.pdf"
        s3.upload_file(pdf_filename, bucket_name, object_name)
        logging.info(f"Uploaded {pdf_filename} to {bucket_name}/{object_name}")

    def start_process(self):
        """
        Initiate the process of capturing and processing the answer sheet.
        """
        self.capture_all_pages()
        self.organize_pages()

        pdf_filename = f"{self.first_page_info['name']}_answersheet.pdf"
        self.save_as_pdf(pdf_filename)
        self.upload_to_cloud(pdf_filename)
        self.processed_answer_sheets += 1
        logging.info(f"Processed {self.processed_answer_sheets} out of {self.total_answer_sheets} answer sheets.")

    def verify_completed_sheets(self):
        """
        Check if the number of processed sheets matches the total expected.
        """
        if self.processed_answer_sheets == self.total_answer_sheets:
            logging.info(f"All {self.total_answer_sheets} answer sheets processed successfully.")
        else:
            logging.error(f"Processed {self.processed_answer_sheets} out of {self.total_answer_sheets}.")


if __name__ == "__main__":
    total_sheets = int(input("Enter total number of answer sheets: "))
    robot = ExamSheetRobot(total_sheets)

    for i in range(total_sheets):
        robot.start_process()

    robot.verify_completed_sheets()

    GPIO.cleanup()  # Clean up GPIO pins
