import cv2
from networktables import NetworkTables
import numpy as np
import time
import zmq

# Subscribe to the ZMQ server to communicate with Webots.
context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect('tcp://127.0.0.1:10012')
socket.subscribe('image')

# Initialize Network Tables to communicate with the robot code.
NetworkTables.initialize('127.0.0.1')
visionSubsystemTable = NetworkTables.getTable('SmartDashboard/VisionSubsystem')

# Initialize calibration parameters.
camera_matrix = np.matrix([
    [378.19332477,   0.        , 422.8684558 ],
    [  0.        , 378.08020475, 400.09320061],
    [  0.        ,   0.        ,   1.        ]])
camera_distortion = np.matrix([[-1.03790313e-01, -8.14745560e-03, 2.30413847e-05, 4.17593664e-04, 3.82276818e-03]])
camera_new_matrix = np.matrix([
    [263.92288208,   0.        , 424.26958176],
    [  0.        , 263.44046021, 400.17072099],
    [  0.        ,   0.        ,   1.        ]])
camera_roi = (51, 62, 748, 676)

time_prev = time.time()
while True:

    # Receive image data.
    frame = socket.recv_multipart()
    image_height = int.from_bytes(frame[1], byteorder='big')
    image_width = int.from_bytes(frame[2], byteorder='big')
    image_depth = int.from_bytes(frame[3], byteorder='big')
    image_data = frame[4]

    # Construct and display the image.
    image_raw = np.frombuffer(image_data, np.uint8).reshape((image_height, image_width, image_depth))
    cv2.imshow('Raw Video', image_raw)

    # Undistort the image.
    image = cv2.undistort(image_raw, camera_matrix, camera_distortion, None, camera_new_matrix)
    x,y,w,h = camera_roi
    image = image[y:y+h, x:x+w]
    cv2.imshow('Undistorted Video', image)

    # Process the image.
    image_hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    image_mask = cv2.inRange(image_hsv, (40,10,0), (70,255,255))
    contours, _ = cv2.findContours(image_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

    bearing = 0
    if len(contours) != 0:
        # Draw the contours and display the annotated image.
        image_annotated = cv2.drawContours(image, contours, -1, (0,0,255), 2)
        cv2.imshow('Processed Video', image_annotated)

        # Find and draw the largest contour.
        largest_contour = max(contours, key=cv2.contourArea)
        x,y,w,h = cv2.boundingRect(largest_contour)
        cv2.rectangle(output, (x,y), (x+w, y+h), (255,0,0), 2)

        # Get the horizontal bearing to the contour.
        x_center = x + (w / 2)
        bearing = (x_center / (image.shape[1] / 2)) - 1

    # Publish output.
    visionSubsystemTable.putNumber('Marker Bearing', bearing)

    # Quit if Escape is pressed.
    if cv2.waitKey(1) == 27:
        cv2.destroyAllWindows()
        break

    # Display the frames per second.
    time_curr = time.time()
    print(f'FPS: {1 / (time_curr - time_prev)}')
    time_prev = time_curr
