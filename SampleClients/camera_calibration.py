import cv2
import numpy as np
import os
import zmq

# Define the dimensions of checkerboard.
CHECKERBOARD = (7, 6)

# Subscribe to the ZMQ server to communicate with Webots.
context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect('tcp://127.0.0.1:10012')
socket.subscribe('image')

# Termination criteria.
criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

# Prepare object points, like (0,0,0), (1,0,0), (2,0,0) ....,(6,5,0).
obj_corners = np.zeros((CHECKERBOARD[0] * CHECKERBOARD[1], 3), np.float32)
obj_corners[:,:2] = np.mgrid[0:CHECKERBOARD[0], 0:CHECKERBOARD[1]].T.reshape(-1,2)

# Arrays to store object points and image points from all the images.
obj_points = [] # 3d point in real world space.
img_points = [] # 2d points in image plane.

# Store undistortion results.
camera_matrix = None
distortion_coefficients = None
rotation_vectors = None
translation_vectors = None
new_camera_matrix = None
roi = None

# Loop until Escape is pressed.
is_capturing = False
while True:
    
    # Receive the frame.
    frame = socket.recv_multipart()

    # Process the image data.
    image_height = int.from_bytes(frame[1], byteorder='big')
    image_width = int.from_bytes(frame[2], byteorder='big')
    image_depth = int.from_bytes(frame[3], byteorder='big')
    image_data = frame[4]
    image = np.frombuffer(image_data, np.uint8).reshape((image_height, image_width, image_depth))

    # Convert to grayscale.
    image_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Check if we want to capture the image.
    if is_capturing:
        is_capturing = False

        # Find and draw the checkboard corners.
        is_pattern_found, img_corners = cv2.findChessboardCorners(image_gray, CHECKERBOARD, None)
        image = cv2.drawChessboardCorners(image, CHECKERBOARD, img_corners, is_pattern_found)
        cv2.imshow('Captured Image', image)

        # If found, add object points and image points.
        if is_pattern_found:
            obj_points.append(obj_corners)
            img_points.append(img_corners)

            # Check if we now have enough points to undistort.
            if len(img_points) >= 3:
                _, camera_matrix, distortion_coefficients, rotation_vectors, translation_vectors = cv2.calibrateCamera(obj_points, img_points, image_gray.shape[::-1], None, None)
                new_camera_matrix, roi = cv2.getOptimalNewCameraMatrix(camera_matrix, distortion_coefficients, image_gray.shape[::-1], 1, image_gray.shape[::-1])


    # Check if we can undistort this frame.
    if camera_matrix is not None:
        image = cv2.undistort(image, camera_matrix, distortion_coefficients, None, new_camera_matrix)
        x, y, w, h = roi
        image = image[y:y+h, x:x+w]

    # Display the video feed.
    cv2.imshow('Video', image)

    # Check if a key was pressed.
    key = cv2.waitKey(1)
    if key == 32:
        # If spacebar was pressed, capture the next image.
        is_capturing = True
    elif key == 8:
        # If Backspace was pressed, delete the last image.
        del obj_points[-1]
        del img_points[-1]
        cv2.destroyWindow('Captured Image')
    elif key == 27:
        # If Escape was pressed, stop capturing images.
        cv2.destroyAllWindows()
        break

# Print the output of the camera calibration.
print(" Camera matrix:")
print(camera_matrix)
  
print("\n Distortion coefficients:")
print(distortion_coefficients)
  
print("\n Rotation Vectors:")
print(rotation_vectors)
  
print("\n Translation Vectors:")
print(translation_vectors)

print("\n Optimal new camera matrix:")
print(new_camera_matrix)

print("\n Region of interest:")
print(roi)