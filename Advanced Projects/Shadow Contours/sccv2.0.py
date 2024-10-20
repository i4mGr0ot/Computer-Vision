import cv2
import numpy as np
import RPi.GPIO as GPIO
import time
import os

# GPIO Setup
LED_PIN = 18  # GPIO Pin for LED
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT)
pwm = GPIO.PWM(LED_PIN, 100)  # PWM at 100 Hz
pwm.start(0)  # Start with 0% duty cycle

# Configuration
CAMERA_INDEX = 0  # Default camera index for Pi Camera
BED_SIZE_MM = 450  # 1.5 ft in mm
DXF_FILENAME = "contour_output.dxf"
FRAME_COUNT = 5  # Number of frames for noise reduction
THRESH_BLOCK_SIZE = 11  # Block size for adaptive thresholding
THRESH_C = 2  # Constant subtracted from mean in adaptive thresholding

# Load Camera Calibration Matrix
if os.path.exists("camera_matrix.npy") and os.path.exists("dist_coeffs.npy"):
    camera_matrix = np.load("camera_matrix.npy")
    dist_coeffs = np.load("dist_coeffs.npy")
else:
    camera_matrix, dist_coeffs = None, None  # No calibration available

def set_led_brightness(brightness):
    """Set LED brightness via PWM (0-100%)."""
    pwm.ChangeDutyCycle(brightness)

def capture_image():
    """Capture a grayscale image from the camera."""
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("Error: Camera not detected.")
        return None

    time.sleep(2)  # Let camera stabilize
    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("Error: Failed to capture image.")
        return None

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # If calibration data is available, undistort the image
    if camera_matrix is not None and dist_coeffs is not None:
        gray = cv2.undistort(gray, camera_matrix, dist_coeffs)

    return gray

def average_frames():
    """Capture multiple frames and compute their average."""
    frames = [capture_image() for _ in range(FRAME_COUNT)]
    return np.mean(frames, axis=0).astype(np.uint8)

def process_image(image):
    """Apply adaptive thresholding and extract contours."""
    thresholded = cv2.adaptiveThreshold(
        image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, THRESH_BLOCK_SIZE, THRESH_C
    )
    contours, _ = cv2.findContours(thresholded, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    print(f"Detected {len(contours)} contour(s).")
    return contours

def scale_contours(contours, image_shape):
    """Scale contours from pixels to millimeters."""
    height, width = image_shape
    scale_x = BED_SIZE_MM / width
    scale_y = BED_SIZE_MM / height

    scaled_contours = [
        [(int(pt[0][0] * scale_x), int(pt[0][1] * scale_y)) for pt in contour]
        for contour in contours
    ]
    return scaled_contours

def save_dxf(contours, filename):
    """Export contours as a DXF file."""
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
    print(f"DXF saved as: {filename}")

def main():
    try:
        print("Turning on LED...")
        set_led_brightness(100)  # Full brightness

        print("Capturing averaged image...")
        image = average_frames()
        if image is None:
            return

        print("Processing image...")
        contours = process_image(image)

        print("Scaling contours...")
        scaled_contours = scale_contours(contours, image.shape)

        print(f"Saving contours to {DXF_FILENAME}...")
        save_dxf(scaled_contours, DXF_FILENAME)

        print("Process completed successfully.")

    finally:
        print("Turning off LED...")
        set_led_brightness(0)
        pwm.stop()
        GPIO.cleanup()

if __name__ == "__main__":
    main()
