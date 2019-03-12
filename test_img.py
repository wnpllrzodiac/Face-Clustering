#!/usr/bin/python3
# -*- coding: UTF-8 -*-

from imutils import paths
import face_recognition
import argparse
import pickle
import cv2
import os
import pymysql
import numpy as np

def add_face(db, cursor, imagePath, box, feature):
    bytes_feature = feature.tostring()
    #print(bytes_feature)
    
    cursor.execute('insert into clus_face_tb (cat_id, img_idx, box_left, box_top, box_right, box_bottom, feature) \
        values (%s, %s, %s, %s, %s, %s, %s)', (2, 124, box[0], box[1], box[2], box[3], bytes_feature))

    db.commit()

    cursor.execute('select feature from clus_face_tb where img_idx = %s' % (123))
    values = cursor.fetchall()

    print('face added to db')

    #print(values)
    feature = np.frombuffer(values[0][0], dtype=np.float64) #np.float32
    print(feature)

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

# 打开数据库连接
db = pymysql.connect("192.168.23.71","root","tysxwg07","test" )

# 使用 cursor() 方法创建一个游标对象 cursor
cursor = db.cursor()

add_face(db, cursor, imagePath, boxes[0], encodings[0])

# 关闭数据库连接
db.close()
