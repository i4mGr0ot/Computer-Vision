import cv2
import dlib
import numpy as np

# Load the Haar cascade for face detection
face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

# Load the shape predictor for facial landmarks
shape_predictor = dlib.shape_predictor('shape_predictor_68_face_landmarks.dat')

# Define eye aspect ratio (EAR) threshold
EAR_THRESHOLD = 0.2

# Start video capture
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Convert frame to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Detect faces
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    for (x, y, w, h) in faces:
        # Get the region of interest (ROI)
        roi_gray = gray[y:y+h, x:x+w]
        roi_color = frame[y:y+h, x:x+w]

        # Detect facial landmarks
        rect = dlib.rectangle(int(x), int(y), int(x+w), int(y+h))
        landmarks = shape_predictor(roi_gray, rect)

        # Extract eye landmarks
        left_eye = landmarks[42:48]
        right_eye = landmarks[36:42]

        # Calculate EAR for both eyes
        left_EAR = eye_aspect_ratio(left_eye)
        right_EAR = eye_aspect_ratio(right_eye)

        # Determine eye states
        left_eye_closed = left_EAR < EAR_THRESHOLD
        right_eye_closed = right_EAR < EAR_THRESHOLD

        if left_eye_closed != right_eye_closed:
            cv2.putText(frame, "One eye closed", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        else:
            cv2.putText(frame, "Both eyes open or closed", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)

    # Display the frame
    cv2.imshow('Eye Detection', frame)

    # Break the loop on 'q' key press
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release the capture and close windows
cap.release()
cv2.destroyAllWindows()

def eye_aspect_ratio(eye):
    # Compute the distances between the vertical eye landmarks
    A = np.linalg.norm(eye[1] - eye[5])
    B = np.linalg.norm(eye[2] - eye[4])

    # Compute the distance between the horizontal eye landmarks
    C = np.linalg.norm(eye[0] - eye[3])

    # Calculate the Eye Aspect Ratio (EAR)
    EAR = (A + B) / (2.0 * C)
    return EAR
