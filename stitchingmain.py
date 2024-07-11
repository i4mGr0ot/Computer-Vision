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
