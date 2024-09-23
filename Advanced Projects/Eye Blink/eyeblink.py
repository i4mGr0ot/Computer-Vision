import cv2
import dlib
import numpy as np
from scipy.spatial import distance as dist

detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")

def eye_aspect_ratio(eye):
    A = dist.euclidean(eye[1], eye[5])
    B = dist.euclidean(eye[2], eye[4])
    C = dist.euclidean(eye[0], eye[3])

    ear = (A + B) / (2.0 * C)
    
    return ear

(left_eye_start, left_eye_end) = (42, 48) 
(right_eye_start, right_eye_end) = (36, 42) 

EAR_THRESHOLD = 0.2
EAR_CONSEC_FRAMES = 3 

counter = 0
alarm_triggered = False

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = detector(gray)

    for face in faces:
        shape = predictor(gray, face)
        shape = np.array([[p.x, p.y] for p in shape.parts()])

        left_eye = shape[left_eye_start:left_eye_end]
        right_eye = shape[right_eye_start:right_eye_end]

        left_EAR = eye_aspect_ratio(left_eye)
        right_EAR = eye_aspect_ratio(right_eye)

        ear = (left_EAR + right_EAR) / 2.0

        if left_EAR < EAR_THRESHOLD and right_EAR >= EAR_THRESHOLD:
            counter += 1
        elif right_EAR < EAR_THRESHOLD and left_EAR >= EAR_THRESHOLD:
            counter += 1
        else:
            counter = 0
            alarm_triggered = False

        if counter >= EAR_CONSEC_FRAMES and not alarm_triggered:
            print("Shakuni's one-eye-shut gesture detected!")
            cv2.putText(frame, "ALARM: One-eye-shut gesture detected!", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            alarm_triggered = True

        for (x, y) in np.concatenate((left_eye, right_eye)):
            cv2.circle(frame, (x, y), 2, (0, 255, 0), -1)

    cv2.imshow("Shakuni's Wink Detector", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
