import cv2
import numpy as np
import time
import zmq

# Subscribe to the ZMQ server.
context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect('tcp://127.0.0.1:10012')
socket.subscribe('image')

time_prev = time.time()
while True:

    # Receive image data.
    frame = socket.recv_multipart()
    image_height = int.from_bytes(frame[1], byteorder='big')
    image_width = int.from_bytes(frame[2], byteorder='big')
    image_depth = int.from_bytes(frame[3], byteorder='big')
    image_data = frame[4]

    # Construct the image.
    image = np.frombuffer(image_data, np.uint8).reshape((image_height, image_width, image_depth))

    # Process the image.
    image_hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    image_mask = cv2.inRange(image_hsv, (40,10,0), (70,255,255))
    contours, _ = cv2.findContours(image_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    image_annotated = cv2.drawContours(image, contours, -1, (0,0,255), 2)

    # Display the image.
    cv2.imshow('image', image_annotated)

    # Quit if Escape is pressed.
    if cv2.waitKey(1) == 27:
        cv2.destroyAllWindows()
        break

    # Display the frames per second.
    time_curr = time.time()
    print(f'FPS: {1 / (time_curr - time_prev)}')
    time_prev = time_curr
