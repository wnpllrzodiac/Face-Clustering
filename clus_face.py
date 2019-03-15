#!/usr/bin/python3

import config
import pymysql
import os
import cv2
import sys
import shutil
import time
import datetime
import numpy as np
import face_recognition
import matplotlib.pyplot as plt
from imutils import paths
from imutils import build_montages
from sklearn.cluster import DBSCAN

def add_pic(cat_id, imagePath):
    filesize = os.path.getsize(imagePath)
    dt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    image = cv2.imread(imagePath)
    try:
        image.shape
    except:
        print('failed to read img file: %s' % (imagePath))
        return False

    # 打开数据库连接
    db = pymysql.connect("192.168.23.71","root","tysxwg07","test" )
    
    # 使用 cursor() 方法创建一个游标对象 cursor
    cursor = db.cursor()

    #INSERT INTO students (class_id, name, gender, score) VALUES (2, '大牛', 'M', 80)
    sql = "INSERT INTO clus_img_tb( \
        cat_id, img_desc, img_path, width, height, add_time, filesize) \
        VALUES ('%s', '%s',  '%s',  %d,  %d, '%s', %d)" % \
        (cat_id, 'nothing', imagePath, image.shape[1], image.shape[0], dt, filesize)

    try:
        # 执行sql语句
        cursor.execute(sql)
        # 执行sql语句
        db.commit()
        print('pic %s added to db.' % imagePath)

        cursor.execute('SELECT id from clus_img_tb WHERE img_path = %s', imagePath)
        values = cursor.fetchall()
        img_idx = values[0][0]
        #print('img_idx: ', img_idx)

        detect_face(db, cursor, imagePath, cat_id, img_idx)
        return True
    except Exception as e:
		    # 发生错误时回滚
        db.rollback()
        print('failed to add img record: ', e)
    finally:
        db.close()
        
    return False

def save_face(db, cursor, imagePath, cat_id, img_idx, box, feature):
    bytes_feature = feature.tostring()
    #print(bytes_feature)

    try:
      top, right, bottom, left = box
      cursor.execute('insert into clus_face_tb (cat_id, img_idx, box_left, box_top, box_right, box_bottom, feature) \
          values (%s, %s, %s, %s, %s, %s, %s)', (cat_id, img_idx, left, top, right, bottom, bytes_feature))

      db.commit()

      print('img %d, face (%d, %d, %d, %d) added to db' % (img_idx, left, top, right, bottom))
      
      #cursor.execute('select feature from clus_face_tb where img_idx = %s' % (123))
      #values = cursor.fetchall()

      #print(values)
      #feature = np.frombuffer(values[0][0], dtype=np.float64) #np.float32
      #print(feature)
    except Exception as e:
        # 发生错误时回滚
        db.rollback()
        print('failed to add face record: ', e)

def detect_face(db, cursor, imagePath, cat_id, img_idx):
    image = cv2.imread(imagePath)
    try:
        image.shape
    except:
        print('failed to read img file: %s' % (imagePath))
        return False

    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # detect the (x,y) coordinates of the bounding boxes
    # corresponding to each face in the input image
    boxes = face_recognition.face_locations(rgb, model="HOG")
    #print(boxes)

    # compute the facial embedding for the face
    encodings = face_recognition.face_encodings(rgb, boxes)
    #print(encodings)

    for box,enc in zip(boxes, encodings):
        save_face(db, cursor, imagePath, cat_id, img_idx, box, enc)

def update_cluster(db, cursor, face_idx, label_id):
      try:
          sql = 'UPDATE clus_face_tb SET cluster_idx = %d WHERE id = %d' % (label_id, face_idx)
          cursor.execute(sql)
          db.commit()
      except Exception as e:
        print('failed to update face data: ', e)
        db.rollback()

def cluster_faces(cat_id):
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
          #print(values)
          face_idx  = v[0]
          img_idx   = v[1]
          top, right, bottom, left = v[2:6]
          feature   = np.frombuffer(v[6], dtype=np.float64)
          img_path  = v[7]

          #print(feature)
          box = (top, right, bottom, left)
          d = [{"faceIndex": face_idx, "imageIndex": img_idx, "imagePath": img_path, "loc": box, "encoding": feature}]
          data.extend(d)
    except Exception as e:
        print('failed to read face data: ', e)
        db.close()
        return

    data = np.array(data)
    encodings = np.array([d["encoding"] for d in data])
    #np.random.shuffle(encodings)

    print(encodings.shape)
    #print(encodings[0])
    #print(type(encodings))

    # cluster the embeddings
    print("[INFO] clustering...")
    clt = DBSCAN(metric="euclidean", n_jobs=-1, eps=0.35, min_samples=3)
    clt.fit(encodings)

    plt.scatter(encodings[:, 4], encodings[:, 9], marker='o', c=clt.labels_)
    plt.show()

    # determine the total number of unique faces found in the dataset
    labelIDs = np.unique(clt.labels_)
    numUniqueFaces = len(np.where(labelIDs > -1)[0])
    print("[INFO] # unique faces : {}".format(numUniqueFaces))

    # remove old pic
    for num in range(0, 20):
        filename = 'out_%d.jpg' % num
        if os.path.exists(filename):
          os.remove(filename)
          print('file %s deleted' % filename)
      
    # loop over the unique face integers
    face_id = 0
    cluster_face_count = 0
    for labelID in labelIDs:
        # find all the indexes into the 'data' array that belong to the
        # current label ID, then randomly sample a maximum of 25 index from the set
        print("[INFO] faces for face ID: {}".format(labelID))
        idxs = np.where(clt.labels_ == labelID)[0]
        print("[INFO] face count: %d, cluster count %d" % (len(idxs), cluster_face_count))
        cluster_face_count = cluster_face_count + len(idxs)
        
        if labelID != -1:
            [update_cluster(db, cursor, data[i]["faceIndex"], labelID) for i in idxs]

        idxs = np.random.choice(idxs, size=min(25, len(idxs)),
          replace=False)

        # initialize the list of faces to include in the montage
        faces = []
        # loop over the sampled indexes
        for i in idxs:
            # load the input image and extract the face ROI
            image = cv2.imread(data[i]["imagePath"])
            (top, right, bottom, left) = data[i]["loc"]
            face = image[top:bottom, left:right]

            # force resize the face ROI to 96x96 and then add it to the
            # faces montage list
            face = cv2.resize(face, (96,96))
            faces.append(face)

        # create a montage using 96x96 "tiles" with 5 rows and 5 columns
        montage = build_montages(faces, (96,96), (5,5))[0]

        # show the output montage
        title = "Face ID #{}".format(labelID)
        title = "Unknown Faces" if labelID == -1 else title
        #cv2.imshow(title, montage)
        #cv2.waitKey(0)
        cv2.imwrite('out_{}.jpg'.format(face_id), montage)
        face_id += 1

    db.close()
    print("[INFO] total cluster_face_count %d" % cluster_face_count)

def test():
    cat_id = 'test'
        
    cluster_faces(cat_id)

    # 关闭数据库连接
    db.close()
    
if __name__ == '__main__':
    while True:
        for folder in os.listdir(config.upload_folder):
            if os.path.isdir(os.path.join(config.upload_folder, folder)):
                cat_id = folder
                print('list pics in cat_id: %s' % cat_id)
                
                cluster_face = False
                for file in os.listdir(os.path.join(config.upload_folder, folder)):
                    filepath = '%s/%s/%s' % (config.upload_folder, folder, file)
                    try:
                        new_folder = os.path.join(config.image_folder, folder)
                        if not os.path.exists(new_folder):
                            os.mkdir(new_folder)
                        new_filepath = os.path.join(new_folder, file)
                        
                        shutil.move(filepath, new_filepath)
                        
                        if add_pic(cat_id, new_filepath):
                            cluster_face = True
                        else:
                            print('failed to read pic')
                            shutil.remove(new_filepath)
                    except Exception as e:
                        print('failed to move file: ', e)
                
                if cluster_face:
                    print('cluster face: %s' % cat_id)
                    cluster_faces(cat_id)
        time.sleep(30)

