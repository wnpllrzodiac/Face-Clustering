#!/usr/bin/python3
 
import pymysql
import datetime
import time
import os
import cv2
import sys
import numpy as np
import face_recognition
from matplotlib import pyplot as plt
from imutils import build_montages

# simple log functions.
def trace(msg):
    date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("[%s][trace] %s"%(date, msg))

def get_msec():
    msec = int(time.time() * 1000)
    return msec

def get_face_info(face_id):
    # 打开数据库连接
    db = pymysql.connect("192.168.23.71","root","tysxwg07","test" )
    
    # 使用 cursor() 方法创建一个游标对象 cursor
    cursor = db.cursor()
    
    try:
        # SELECT * from clus_face_tb left join clus_img_tb on clus_img_tb.id = clus_face_tb.img_idx where clus_face_tb.cat_id = 'test';
        cursor.execute('SELECT clus_face_tb.id, img_idx, box_top, box_right, box_bottom, box_left, feature, img_path \
            from clus_face_tb \
            left join clus_img_tb on clus_img_tb.id = clus_face_tb.img_idx \
            WHERE clus_face_tb.id = %s', face_id)
        values = cursor.fetchall()

        if len(values) > 0:
            v = values[0]
            #trace(values)
            face_idx  = v[0]
            img_idx   = v[1]
            top, right, bottom, left = v[2:6]
            feature   = np.frombuffer(v[6], dtype=np.float64)
            img_path  = v[7]

            #trace(feature)
            box = (top, right, bottom, left)
            return (img_path, box, feature)
    except Exception as e:
        trace('failed to read face data: {}'.format(e))
        db.close()
    
    return None

def test_compare_face(cat_id, unknown_face_encoding):
    # 打开数据库连接
    db = pymysql.connect("192.168.23.71","root","tysxwg07","test" )
    
    # 使用 cursor() 方法创建一个游标对象 cursor
    cursor = db.cursor()
    
    try:
        # SELECT * from clus_face_tb left join clus_img_tb on clus_img_tb.id = clus_face_tb.img_idx where clus_face_tb.cat_id = 'test';
        cursor.execute('SELECT clus_face_tb.id, img_idx, box_top, box_right, box_bottom, box_left, feature, img_path from clus_face_tb \
            left join clus_img_tb on clus_img_tb.id = clus_face_tb.img_idx \
            WHERE clus_face_tb.cat_id = %s', cat_id)
        values = cursor.fetchall()

        data = []
        for v in values:
            #trace(values)
            face_idx  = v[0]
            img_idx   = v[1]
            top, right, bottom, left = v[2:6]
            feature   = np.frombuffer(v[6], dtype=np.float64)
            img_path  = v[7]

            #trace(feature)
            box = (top, right, bottom, left)
            d = [{"faceIndex": face_idx, "imageIndex": img_idx, "imagePath": img_path, "loc": box, "encoding": feature}]
            data.extend(d)
    except Exception as e:
        trace('failed to read face data: {}'.format(e))
        db.close()
        return

    data = np.array(data)
    known_faces = np.array([d["encoding"] for d in data])
    trace('known_faces count: {}'.format(len(known_faces)))

    #结果是True/false的数组，未知面孔known_faces阵列中的任何人相匹配的结果
    start_time = get_msec()
    results = face_recognition.compare_faces(known_faces, unknown_face_encoding, tolerance=0.5)
    compare_msec = get_msec() - start_time
    trace('compare time: {} msec'.format(compare_msec))
    results = np.array(results)
    found = np.where(results==True)[0]
    faces = []
    for i in found:
        imagepath = data[i]["imagePath"]
        (top, right, bottom, left) = data[i]["loc"]
        trace('#{}: {}'.format(i, imagepath))

        image = cv2.imread(imagepath)
        face = image[top:bottom, left:right]
        face = cv2.resize(face, (96,96))
        faces.append(face)

    # create a montage using 96x96 "tiles" with 5 rows and 5 columns
    montage = build_montages(faces, (96,96), (8,8))[0]

    # show the output montage
    title = "match face"
    #cv2.imshow('match face', montage)
    #plt.subplot(122)

    (r, g, b) = cv2.split(montage)
    img = cv2.merge([b,g,r])
    plt.imshow(img)
    
    trace("result :{}".format(results))

if __name__ == '__main__':
    cat_id = 'mwyy'
    face_id = 3802
    if len(sys.argv) > 1:
        face_id = sys.argv[1]
    (path, box, unknown_face_encoding) = get_face_info(face_id)

    (top, right, bottom, left) = box[0:4]
    face_img = cv2.imread(path)
    face = face_img[top:bottom, left:right]
    #cv2.imshow('unknown face', face)
    plt.figure(figsize=(10, 10))
    #plt.subplot(121)
    #plt.imshow(face)

    test_compare_face(cat_id, unknown_face_encoding)

    plt.show()

    #while True:
    #    if cv2.waitKey(20) & 0xFF == ord('q'):
    #        break
