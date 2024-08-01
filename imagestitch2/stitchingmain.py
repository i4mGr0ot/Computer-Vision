import numpy as np
import cv2
import glob
import imutils 

img_path = glob.glob("") #insert file path 
img = [] 

for i in img_path:
  j = cv2.imread(i)
  img.append(j)
  cv2.imshow("Image",j)
  cv2.waitKey(0)

sticher = cv2.Sticher_create()
error, stcImg = Sticher.stich(img)

if not error:
  cv2.imwrite("stcOutput.png", stcImg)
  cv2.imshow("Stiched Image", stcImg)
  cv2.waitKey(0)
  
  stcImg = cv2.copyMakeBorder(stcImg, 10, 10, 10, 10, cv2.BORDER_CONSTANT, (0,0,0))
  gray = cv2.cvtColor(stcImg, cv2.COLOR_BGR2GRAY)
  thresh_img = cv2.threshold(gray, 0, 255 , cv2.THRESH_BINARY)[1]
  cv2.imshow("Threshold Image", thresh_img)
  cv2.waitKey(0)

  contours = cv2.findContours(thresh_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
  contours = imutils.grab_contours(contours)
  areaOI = max(contours, key=cv2.contourArea)

  mask = np.zeros(thresh_img.shape, dtype="uint8")
  x, y, w, h = cv2.boundingRect(areaOI)
  cv2.rectangle(mask, (x,y), (x + w, y + h), 255, -1)

  minRectangle = mask.copy()
  sub = mask.copy()

  while cv2.countNonZero(sub) > 0:
        minRectangle = cv2.erode(minRectangle, None)
        sub = cv2.subtract(minRectangle, thresh_img)

  contours = cv2.findContours(minRectangle.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
  contours = imutils.grab_contours(contours)
  areaOI = max(contours, key=cv2.contourArea)

  cv2.imshow("minRectangle Image", minRectangle)
  cv2.waitKey(0)

  x, y, w, h = cv2.boundingRect(areaOI)

  stcImg = stcImg[y:y + h, x:x + w]
  cv2.imwrite("stitchedOutputProcessed.png", stcImg)
  cv2.imshow("Stitched Image Processed", stcImg)
  cv2.waitKey(0)

else:
    print("Images could not be stitched!")
    print("Likely not enough keypoints being detected!")


