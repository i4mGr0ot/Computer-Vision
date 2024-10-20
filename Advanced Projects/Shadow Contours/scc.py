import cv2
import numpy as np
import RPi.GPIO as GPIO 
import time 

LED_PIN = 18
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT)
CAMERA_INDEX = 0  
THRESHOLD = 100   
BED_SIZE_MM = 450  
DXF_FILENAME = "contour_output.dxf"

def control_led(state):
    GPIO.output(LED_PIN, GPIO.HIGH if state else GPIO.LOW)

def capture_image():
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("Error: Could not open the camera.")
        return None

    time.sleep(2)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("Error: Failed to capture image.")
        return None

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return gray

def process_image(image):
    _, thresholded = cv2.threshold(image, THRESHOLD, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresholded, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    print(f"Detected {len(contours)} contour(s).")
    return contours

def scale_contours(contours, image_shape):
    height, width = image_shape[:2]
    scale_x = BED_SIZE_MM / width
    scale_y = BED_SIZE_MM / height

    scaled_contours = [
        [(int(pt[0][0] * scale_x), int(pt[0][1] * scale_y)) for pt in contour]
        for contour in contours
    ]
    return scaled_contours

def save_dxf(contours, filename):
    """Write contours to a DXF file."""
    with open(filename, 'w') as f:
        f.write("0\nSECTION\n2\nHEADER\n0\nENDSEC\n")
        f.write("0\nSECTION\n2\nTABLES\n0\nENDSEC\n")
        f.write("0\nSECTION\n2\nBLOCKS\n0\nENDSEC\n")
        f.write("0\nSECTION\n2\nENTITIES\n")

        for contour in contours:
            f.write("0\nPOLYLINE\n8\n0\n66\n1\n70\n1\n")
            for point in contour:
                f.write(f"0\nVERTEX\n8\n0\n10\n{point[0]}\n20\n{point[1]}\n30\n0.0\n")
            f.write("0\nSEQEND\n")

        f.write("0\nENDSEC\n0\nEOF\n")
    print(f"Saved DXF file: {filename}")

def main():
    try:
        print("Turning on the LED...")
        control_led(True)  # Turn on the LED

        print("Capturing image...")
        image = capture_image()
        if image is None:
            return

        print("Processing image...")
        contours = process_image(image)

        print("Scaling contours...")
        scaled_contours = scale_contours(contours, image.shape)

        print(f"Saving DXF to {DXF_FILENAME}...")
        save_dxf(scaled_contours, DXF_FILENAME)

        print("Process completed successfully.")

    finally:
        print("Turning off the LED...")
        control_led(False)  # Ensure the LED is turned off
        GPIO.cleanup()  # Clean up GPIO states

if __name__ == "__main__":
    main()
