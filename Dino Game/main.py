import cv2
import cvzone
import numpy as np
import pyautogui
from cvzone.FPS import FPS
from mss import mss
 
fpsReader = FPS()
 
 
def capture_screen_region_opencv(x, y, desired_width, desired_height):
    screenshot = pyautogui.screenshot(region=(x, y, desired_width, desired_height))
    screenshot = np.array(screenshot)
    screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)
    return screenshot
 
 
def capture_screen_region_opencv_mss(x, y, width, height):
    with mss() as sct:
        monitor = {"top": y, "left": x, "width": width, "height": height}
        screenshot = sct.grab(monitor)
        # Convert to an OpenCV image
        img = np.array(screenshot)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)  # Convert from BGRA to BGR
 
        return img
 
 
def pre_process(_imgCrop):
    # Convert to grayscale for thresholding
    gray_frame = cv2.cvtColor(_imgCrop, cv2.COLOR_BGR2GRAY)
    # Apply thresholding to the grayscale image
    _, binary_frame = cv2.threshold(gray_frame, 127, 255, cv2.THRESH_BINARY_INV)
    # canny image
    canny_frame = cv2.Canny(binary_frame, 50, 50)
    # dilate image
    kernel = np.ones((5, 5))
    dilated_frame = cv2.dilate(canny_frame, kernel, iterations=2)
 
    return dilated_frame
 
 
def find_obstacles(_imgCrop, _imgPre):
    imgContours, conFound = cvzone.findContours(_imgCrop, _imgPre, minArea=100, filter=None)
    return imgContours, conFound
 
 
def game_logic(conFound, _imgContours, jump_distance=65):
    if conFound:
        # left most contour
        left_most_contour = sorted(conFound, key=lambda x: x["bbox"][0])
 
        cv2.line(_imgContours, (0, left_most_contour[0]["bbox"][1] + 10),
                 (left_most_contour[0]["bbox"][0], left_most_contour[0]["bbox"][1] + 10), (0, 200, 0), 10)
 
        # draw line on screenShotGame from left most contour
        if left_most_contour[0]["bbox"][0] < jump_distance:
            pyautogui.press("space")
            print("jump")
    return _imgContours
 
 
while True:
    # Step 1 - Capture the screen region of game
    imgGame = capture_screen_region_opencv_mss(450, 300, 650, 200)
 
    # Step 2 - Crop the image to the desired region
    cp = 100, 140, 110
    imgCrop = imgGame[cp[0]:cp[1], cp[2]:]
 
    # Step 3 - Pre Process Image
    imgPre = pre_process(imgCrop)
 
    # Step 4 - Find Obstacles
    imgContours, conFound = find_obstacles(imgCrop, imgPre)
 
    # Step 5 - Apply Game Logic
    imgContours = game_logic(conFound, imgContours)
 
    # # Step 6 - Display the Result
    imgGame[cp[0]:cp[1], cp[2]:] = imgContours
 
    fps, imgGame = fpsReader.update(imgGame)
 
    cv2.imshow("Game", imgGame)
    # cv2.imshow("imgCrop", imgContours)
    # cv2.imshow("imgPre", imgPre)
    cv2.waitKey(1)
