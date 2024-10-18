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

# Global variables for tracking upload state
uploads = defaultdict(list)  # To track uploaded images
total_pages = 0              # Total pages for the current student
uploaded_page_count = 0      # Count of uploaded pages

# OLED setup
oled = OLED()  # Initialize your OLED display here

def suction_control(intensity):
    """Controls the suction pump intensity based on calibration."""
    GPIO.setup(SUCTION_PIN, GPIO.OUT)
    pwm = GPIO.PWM(SUCTION_PIN, 1000)
    pwm.start(0)
    pwm.ChangeDutyCycle(intensity)

def flip_page():
    """Flips the page using the servo motor and resets the suction pump."""
    GPIO.setup(SERVO_PIN, GPIO.OUT)
    servo = GPIO.PWM(SERVO_PIN, 50)
    servo.start(0)
    
    # Move servo to flip page
    servo.ChangeDutyCycle(7)  # Adjust angle to lift page
    time.sleep(1)
    servo.ChangeDutyCycle(2)  # Flip page to right side
    time.sleep(1)
    servo.stop()

def press_tablet_button():
    """Simulates robot arm pressing the capture button on the tablet."""
    GPIO.setup(ARM_PIN, GPIO.OUT)
    arm = GPIO.PWM(ARM_PIN, 50)
    arm.start(0)
    
    # Simulate button press on tablet camera
    arm.ChangeDutyCycle(7)  # Move to press button
    time.sleep(0.5)
    arm.ChangeDutyCycle(2)  # Release button
    time.sleep(0.5)
    arm.stop()

def process_image(image_path):
    """Performs basic image validation and enhancement."""
    img = cv2.imread(image_path)
    
    # Check for image clarity (blurriness)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    if laplacian_var < 100:
        print("Image is too blurry, skipping upload.")
        return False  # Indicate failure
    
    # Apply basic enhancements
    enhanced_img = cv2.convertScaleAbs(img, alpha=1.2, beta=50)
    
    # Save enhanced image
    cv2.imwrite(image_path, enhanced_img)
    
    return True  # Indicate success

def extract_candidate_details(image_path):
    """Extracts candidate details (name, subject, class, section) from the first image using OCR."""
    img = Image.open(image_path)
    text = pytesseract.image_to_string(img)
    
    name = "Unknown"
    subject = "Unknown"
    class_section = "Unknown"
    
    # Extracting data from OCR output
    for line in text.split('\n'):
        if "Name" in line:
            name = line.split(":")[1].strip()
        if "Subject" in line:
            subject = line.split(":")[1].strip()
        if "Class" in line:
            class_section = line.split(":")[1].strip()
    
    return name, subject, class_section

def create_pdf(images, pdf_path):
    """Creates a PDF from captured images."""
    pdf = FPDF()
    
    for image in images:
        pdf.add_page()
        pdf.image(image, x=10, y=10, w=190)
    
    pdf.output(pdf_path, "F")

def upload_to_aws(file_name, folder):
    """Uploads file to AWS S3."""
    try:
        s3.upload_file(file_name, bucket_name, folder + "/" + os.path.basename(file_name))
        print(f"{file_name} uploaded successfully.")
    except Exception as e:
        print(f"Upload failed: {e}")

def check_page_sequence(images):
    """Check if pages are in correct sequence."""
    if len(images) != total_pages:
        print("Missing pages detected. Expected pages:", total_pages, "Uploaded pages:", len(images))
        return False
    return True

def calibrate_suction_pump():
    """Calibration of the suction pump intensity for flipping one page."""
    intensity = 0
    while intensity < 100:
        oled.display_text(f"Calibrate Suction Intensity: {intensity}%")
        # Assuming a method to read user input (like a button press to confirm)
        input("Press Enter to confirm intensity...")  # Placeholder for actual button input
        suction_control(intensity)
        
        # Test if only one page flips
        press_tablet_button()  # Simulate image capture
        time.sleep(2)  # Wait for image to be taken
        
        # Logic to check if one page flipped successfully
        if input("Did only one page flip? (y/n): ").strip().lower() == 'y':
            break
        intensity += 10  # Increase intensity in increments
    
    return intensity

def get_input_from_oled(prompt):
    """Display prompt on OLED and return user input as a string."""
    oled.display_text(prompt)
    user_input = ""
    
    while True:
        oled.display_text(user_input)
        key = input("Type next character (or press Enter to finish): ")  # Replace with actual keyboard input mechanism
        
        if key == "":
            break
        elif key == "backspace":
            user_input = user_input[:-1]
        else:
            user_input += key
    
    return user_input

def main():
    global total_pages, uploaded_page_count
    
    # Interactive inputs on OLED screen
    subject_name = get_input_from_oled("Enter Subject Name:")
    total_pages = int(get_input_from_oled("Enter Main Sheet Pages:"))
    supplementary_pages = int(get_input_from_oled("Enter Supplementary Sheet Pages:"))

    class_section = get_input_from_oled("Enter Class and Section:")
    total_students = int(get_input_from_oled("Enter Total Number of Students:"))

    # Adjust for flexibility
    while True:
        adjust_pages = input(f"Current total pages is {total_pages}. Do you want to adjust? (y/n): ")
        if adjust_pages.lower() == 'y':
            total_pages = int(get_input_from_oled("Enter New Total Pages:"))
        else:
            break

    # Calibrate suction pump intensity
    suction_intensity = calibrate_suction_pump()

    for student in range(total_students):
        print(f"\nProcessing Student {student + 1}...\n")
        
        page_number = 1
        candidate_images = []
        
        # Suction control for the first page
        suction_control(intensity=suction_intensity)
        
        for _ in range(total_pages // 2):
            # Simulate capturing image from tablet
            press_tablet_button()
            image_file = f'{IMAGE_PATH}page_{page_number}.jpg'
            
            if process_image(image_file):
                candidate_images.append(image_file)
                uploaded_page_count += 1
            else:
                print(f"Failed to capture valid image for page {page_number}. Retrying...")
                continue
            
            page_number += 1
            
            # Flip page
            flip_page()
        
        # Extract details from the first image
        candidate_name, subject, class_section = extract_candidate_details(candidate_images[0])
        
        # Create folder structure in the cloud
        folder_name = f"{subject_name}/{class_section}"
        os.makedirs(f"{PDF_PATH}{folder_name}", exist_ok=True)
        
        # Create PDF for the candidate's answer sheet
        pdf_file = f"{PDF_PATH}{folder_name}/{candidate_name.replace(' ', '_')}.pdf"
        create_pdf(candidate_images, pdf_file)
        
        # Validate the sequence and upload PDF to AWS
        if check_page_sequence(candidate_images):
            upload_to_aws(pdf_file, folder_name)
        else:
            print("Please ensure all pages are captured before uploading.")
        
        print(f"Uploaded answer sheet for {candidate_name} in {class_section}. Total uploaded pages: {uploaded_page_count}")

    print("All students processed successfully!")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        GPIO.cleanup()
