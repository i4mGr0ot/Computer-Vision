import RPi.GPIO as GPIO
import time
import cv2
import pytesseract
from PIL import Image
from fpdf import FPDF
import os
import boto3
from collections import defaultdict
from oled import OLED  # Assumed OLED library for your setup

# AWS Setup
s3 = boto3.client('s3')
bucket_name = 'your-s3-bucket-name'

# GPIO setup
SUCTION_PIN = 18        # PWM pin for controlling suction pump
SERVO_PIN = 17          # Pin for controlling page-flip servo motor
ARM_PIN = 22            # Pin to control robot arm for pressing tablet button
IMAGE_PATH = '/home/pi/images/'  # Folder to save images locally before upload
PDF_PATH = '/home/pi/pdfs/'

# OCR setup
pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'

# Global variables
uploads = defaultdict(list)  # Track uploaded images
total_pages = 0              # Total pages for the current student
uploaded_page_count = 0      # Count of uploaded pages

# OLED setup
oled = OLED()  # Initialize your OLED display here

def suction_control(intensity):
    """Controls the suction pump intensity."""
    GPIO.setup(SUCTION_PIN, GPIO.OUT)
    pwm = GPIO.PWM(SUCTION_PIN, 1000)
    pwm.start(intensity)

def flip_page():
    """Flips the page using the servo motor."""
    GPIO.setup(SERVO_PIN, GPIO.OUT)
    servo = GPIO.PWM(SERVO_PIN, 50)
    servo.start(0)
    
    servo.ChangeDutyCycle(7)  # Lift page
    time.sleep(1)
    servo.ChangeDutyCycle(2)  # Flip page
    time.sleep(1)
    servo.stop()

def press_tablet_button():
    """Simulates robot arm pressing the tablet button."""
    GPIO.setup(ARM_PIN, GPIO.OUT)
    arm = GPIO.PWM(ARM_PIN, 50)
    arm.start(0)
    
    arm.ChangeDutyCycle(7)  # Press button
    time.sleep(0.5)
    arm.ChangeDutyCycle(2)  # Release button
    time.sleep(0.5)
    arm.stop()

def process_image(image_path):
    """Validates and enhances the image."""
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    if cv2.Laplacian(gray, cv2.CV_64F).var() < 100:
        return False  # Image is too blurry
    
    enhanced_img = cv2.convertScaleAbs(img, alpha=1.2, beta=50)
    cv2.imwrite(image_path, enhanced_img)
    return True  # Image processed successfully

def extract_candidate_details(image_path):
    """Extracts candidate details from the image."""
    text = pytesseract.image_to_string(Image.open(image_path))
    details = { "name": "Unknown", "subject": "Unknown", "class": "Unknown" }
    
    for line in text.split('\n'):
        if "Name" in line: details["name"] = line.split(":")[1].strip()
        if "Subject" in line: details["subject"] = line.split(":")[1].strip()
        if "Class" in line: details["class"] = line.split(":")[1].strip()
    
    return details["name"], details["subject"], details["class"]

def create_pdf(images, pdf_path):
    """Creates a PDF from images."""
    pdf = FPDF()
    for image in images:
        pdf.add_page()
        pdf.image(image, x=10, y=10, w=190)
    pdf.output(pdf_path, "F")

def upload_to_aws(file_name, folder):
    """Uploads a file to AWS S3."""
    try:
        s3.upload_file(file_name, bucket_name, f"{folder}/{os.path.basename(file_name)}")
        print(f"{file_name} uploaded successfully.")
    except Exception as e:
        print(f"Upload failed: {e}")

def get_input_from_oled(prompt):
    """Display prompt on OLED and return user input."""
    oled.display_text(prompt)
    user_input = ""
    
    while True:
        oled.display_text(user_input)
        key = input("Type next character (or press Enter to finish): ")  # Placeholder for actual input mechanism
        if key == "":
            break
        elif key == "backspace":
            user_input = user_input[:-1]
        else:
            user_input += key
    
    return user_input

def main():
    global total_pages
    
    # Interactive inputs on OLED screen
    subject_name = get_input_from_oled("Enter Subject Name:")
    total_pages = int(get_input_from_oled("Enter Main Sheet Pages:"))
    supplementary_pages = int(get_input_from_oled("Enter Supplementary Sheet Pages:"))
    class_section = get_input_from_oled("Enter Class and Section:")
    total_students = int(get_input_from_oled("Enter Total Number of Students:"))

    suction_intensity = int(get_input_from_oled("Calibrate Suction Intensity (0-100):"))

    for student in range(total_students):
        print(f"\nProcessing Student {student + 1}...\n")
        candidate_images = []

        suction_control(intensity=suction_intensity)
        for page_number in range(1, total_pages + 1):
            press_tablet_button()
            image_file = f'{IMAGE_PATH}page_{page_number}.jpg'
            
            if process_image(image_file):
                candidate_images.append(image_file)
            else:
                print(f"Failed to capture valid image for page {page_number}. Skipping...")
                continue
            
            flip_page()
        
        candidate_name, subject, class_section = extract_candidate_details(candidate_images[0])
        folder_name = f"{subject_name}/{class_section}"
        os.makedirs(f"{PDF_PATH}{folder_name}", exist_ok=True)
        
        pdf_file = f"{PDF_PATH}{folder_name}/{candidate_name.replace(' ', '_')}.pdf"
        create_pdf(candidate_images, pdf_file)
        upload_to_aws(pdf_file, folder_name)
        
        print(f"Uploaded answer sheet for {candidate_name} in {class_section}.")

    print("All students processed successfully!")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        GPIO.cleanup()
