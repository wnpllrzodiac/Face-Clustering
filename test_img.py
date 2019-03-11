from imutils import paths
import face_recognition
import argparse
import pickle
import cv2
import os

imagePath = '/media/zodiac/Prog/3g/peoplePhoto/【有图】《一叶知秋》/【有图】《一叶知秋》_002.jpg' 
image = cv2.imread(imagePath)
try:
    image.shape
except:
    print('failed to read img file: %s' % (imagePath))
    exit(0)

rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

# detect the (x,y) coordinates of the bounding boxes
# corresponding to each face in the input image
boxes = face_recognition.face_locations(rgb, model="HOG")
print(boxes)


# compute the facial embedding for the face
encodings = face_recognition.face_encodings(rgb, boxes)
print(encodings)
