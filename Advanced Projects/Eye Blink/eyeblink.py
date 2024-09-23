import cv2
import dlib
import numpy as np
from scipy.spatial import distance as dist

# Load the face detector and facial landmarks predictor
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")

# EAR calculation function
def eye_aspect_ratio(eye):
    # compute the euclidean distances between the two sets of vertical eye landmarks (x, y)-coordinates
    A = dist.euclidean(eye[1], eye[5])
    B = dist.euclidean(eye[2], eye[4])

    # compute the euclidean distance between the horizontal eye landmark (x, y)-coordinates
    C = dist.euclidean(eye[0], eye[3])

    # compute the eye aspect ratio
    ear = (A + B) / (2.0 * C)
    
    return ear

# Eye landmarks from the facial landmark predictor
(left_eye_start, left_eye_end) = (42, 48) # Left eye landmarks
(right_eye_start, right_eye_end) = (36, 42) # Right eye landmarks

# EAR threshold to detect closed eyes
EAR_THRESHOLD = 0.2
EAR_CONSEC_FRAMES = 3  # Number of frames to confirm a gesture

# To track the number of consecutive frames with closed eyes
counter = 0
alarm_triggered = False

# Start video capture
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

        # Get the eye landmarks
        left_eye = shape[left_eye_start:left_eye_end]
        right_eye = shape[right_eye_start:right_eye_end]

        # Calculate EAR for both eyes
        left_EAR = eye_aspect_ratio(left_eye)
        right_EAR = eye_aspect_ratio(right_eye)

        # Average EAR for both eyes
        ear = (left_EAR + right_EAR) / 2.0

        # Check if one eye is closed (left or right) and the other is open
        if left_EAR < EAR_THRESHOLD and right_EAR >= EAR_THRESHOLD:
            counter += 1
        elif right_EAR < EAR_THRESHOLD and left_EAR >= EAR_THRESHOLD:
            counter += 1
        else:
            counter = 0
            alarm_triggered = False

        # If the gesture is sustained for a number of frames, trigger the alarm
        if counter >= EAR_CONSEC_FRAMES and not alarm_triggered:
            print("Shakuni's one-eye-shut gesture detected!")
            cv2.putText(frame, "ALARM: One-eye-shut gesture detected!", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            alarm_triggered = True

        # Visualize the landmarks for debugging
        for (x, y) in np.concatenate((left_eye, right_eye)):
            cv2.circle(frame, (x, y), 2, (0, 255, 0), -1)

    # Show the video feed with detected landmarks and alarm message
    cv2.imshow("Shakuni Gesture Detector", frame)

    # Break loop on 'q' key press
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
