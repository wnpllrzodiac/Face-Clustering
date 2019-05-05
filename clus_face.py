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
import multiprocessing
import itertools
import matplotlib.pyplot as plt
from imutils import paths
from imutils import build_montages
from sklearn.cluster import DBSCAN

total_detect_msec = 0

# simple log functions.
def trace(msg):
    date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("[%s][trace] %s"%(date, msg))

def process_images_in_process_pool(pool, cat_id, images):
    function_parameters = zip(
        itertools.repeat(cat_id),
        images
    )

    pool.starmap(add_image, function_parameters)

def add_image(cat_id, imagePath):
    global total_detect_msec

    trace('add_image: cat_id {}, path {}'.format(cat_id, imagePath))
    filesize = os.path.getsize(imagePath)
    dt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    image = cv2.imread(imagePath)
    try:
        image.shape
    except:
        trace('failed to read img file: %s' % (imagePath))
        os.unlink(imagePath)
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
        trace('pic %s(res %d x %d) added to db.' % (imagePath, image.shape[1], image.shape[0]))

        cursor.execute('SELECT id from clus_img_tb WHERE img_path = %s', imagePath)
        values = cursor.fetchall()
        img_idx = values[0][0]

        start_time = get_msec()
        detect_face(db, cursor, imagePath, cat_id, img_idx)
        detect_msec = get_msec() - start_time
        trace('detect_msec: %d (avg %d)' % (detect_msec, total_detect_msec))
        total_detect_msec = (total_detect_msec * 4 + detect_msec) // 5
        return True
    except Exception as e:
		    # 发生错误时回滚
        db.rollback()
        trace('failed to add img record: {}'.format(e))
    finally:
        db.close()

    os.unlink(imagePath)
    return False

def save_face(db, cursor, imagePath, cat_id, img_idx, box, feature):
    bytes_feature = feature.tostring()

    try:
      top, right, bottom, left = box
      cursor.execute('insert into clus_face_tb (cat_id, img_idx, box_left, box_top, box_right, box_bottom, feature) \
          values (%s, %s, %s, %s, %s, %s, %s)', (cat_id, img_idx, left, top, right, bottom, bytes_feature))

      db.commit()

      trace('img(id #%d): face (ltrb: %d, %d, %d, %d) added to db' % (img_idx, left, top, right, bottom))
    except Exception as e:
        db.rollback()
        trace('failed to add face record: {}'.format(e))

def detect_face(db, cursor, imagePath, cat_id, img_idx):
    image = cv2.imread(imagePath)
    try:
        image.shape
    except:
        trace('failed to read img file: %s' % (imagePath))
        return False

    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # detect the (x,y) coordinates of the bounding boxes
    # corresponding to each face in the input image
    boxes = face_recognition.face_locations(rgb, model="HOG")
    #print(boxes)

    if len(boxes) == 0:
        trace('NO face detected, try equalizeHist')
        
        (b, g, r) = cv2.split(image)
        bH = cv2.equalizeHist(b)
        gH = cv2.equalizeHist(g)
        rH = cv2.equalizeHist(r)
        # 合并每一个通道
        rgb = cv2.merge((bH, gH, rH))
        start_time = get_msec() 
        boxes = face_recognition.face_locations(rgb, model="CNN")
        recognition_msec = get_msec() - start_time

        if len(boxes) == 0:
            trace('NO face detected')
            return False

    # compute the facial embedding for the face
    encodings = face_recognition.face_encodings(rgb, boxes)
    #print(encodings)

    for box,enc in zip(boxes, encodings):
        save_face(db, cursor, imagePath, cat_id, img_idx, box, enc)
        
def update_cluster(db, cursor, faceid_list, label_id):
        try:
            items = ','.join(faceid_list)
            sql = 'UPDATE clus_face_tb SET cluster_idx = %d WHERE id in (%s)' % (label_id, items)
            cursor.execute(sql)
            db.commit()
        except Exception as e:
            trace('failed to update face data: {}'.format(e))
            db.rollback()

def cluster_faces(cat_id):
    save_montage = False
    
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
    encodings = np.array([d["encoding"] for d in data])
    #np.random.shuffle(encodings)

    trace(encodings.shape)

    # cluster the embeddings
    trace("[INFO] clustering...")
    clt = DBSCAN(metric="euclidean", n_jobs=-1, eps=0.35, min_samples=3)
    clt.fit(encodings)

    #plt.scatter(encodings[:, 4], encodings[:, 9], marker='o', c=clt.labels_)
    #plt.show()

    # determine the total number of unique faces found in the dataset
    labelIDs = np.unique(clt.labels_)
    numUniqueFaces = len(np.where(labelIDs > -1)[0])
    trace("[INFO] # unique faces : {}".format(numUniqueFaces))

    if save_montage:
        # remove old pic
        for num in range(0, 20):
            filename = 'out_%d.jpg' % num
            if os.path.exists(filename):
              os.unlink(filename)
              trace('file %s deleted' % filename)
      
    # loop over the unique face integers
    face_id = 0
    cluster_face_count = 0
    for labelID in labelIDs:
        # find all the indexes into the 'data' array that belong to the
        # current label ID, then randomly sample a maximum of 25 index from the set
        trace("[INFO] faces for face ID: {}".format(labelID))
        idxs = np.where(clt.labels_ == labelID)[0]
        trace("[INFO] face count: %d, cluster count %d" % (len(idxs), cluster_face_count))
        cluster_face_count = cluster_face_count + len(idxs)
        
        if labelID != -1:
            faceIdList = []
            for i in idxs:
                faceIdList.append(str(data[i]["faceIndex"]))
            update_cluster(db, cursor, faceIdList, labelID)

        if save_montage:
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
    trace("[INFO] total cluster_face_count %d" % cluster_face_count)

def test():
    cat_id = 'test'
        
    cluster_faces(cat_id)

    # 关闭数据库连接
    db.close()
    
def get_msec():
    msec = int(time.time() * 1000)
    return msec
    
if __name__ == '__main__':
    trace('clus face work started...')
    
    # macOS will crash due to a bug in libdispatch if you don't use 'forkserver'
    processes = 8
    context = multiprocessing
    if "forkserver" in multiprocessing.get_all_start_methods():
        context = multiprocessing.get_context("forkserver")

    pool = context.Pool(processes=processes)
    
    total_cluster_msec = 0
    while True:
        trace('ready to scan pic')
        t = int(time.time())
        for folder in os.listdir(config.upload_folder):
            if os.path.isdir(os.path.join(config.upload_folder, folder)):
                cat_id = folder
                trace('list pics in cat_id: %s' % cat_id)
                
                new_folder = os.path.join(config.image_folder, folder)
                if not os.path.exists(new_folder):
                    os.mkdir(new_folder)

                multi_process = True
                cluster_face = False
                if multi_process:
                    images = []
                    for file in os.listdir(os.path.join(config.upload_folder, folder)):
                        filepath = '%s/%s/%s' % (config.upload_folder, folder, file)
                        try:
                            new_filepath = os.path.join(new_folder, file)
                            shutil.move(filepath, new_filepath)
                            images.append(new_filepath)
                        except Exception as e:
                            trace('failed to move file: {}'.format(e))

                    if len(images) > 0:
                        process_images_in_process_pool(pool, cat_id, images)
                        cluster_face = True
                else:
                    for file in os.listdir(os.path.join(config.upload_folder, folder)):
                        filepath = '%s/%s/%s' % (config.upload_folder, folder, file)
                        try:
                            new_filepath = os.path.join(new_folder, file)
                            shutil.move(filepath, new_filepath)
                            
                            if add_image(cat_id, new_filepath):
                                cluster_face = True
                            else:
                                trace('failed to read pic')
                        except Exception as e:
                            trace('failed to move file: {}'.format(e))
                
                if cluster_face:
                    trace('cluster face: %s' % cat_id)
                    start_time = get_msec()
                    try:
                        cluster_faces(cat_id)
                        
                        cluster_msec = get_msec() - start_time
                        trace('cluster_msec: %d (avg %d)' % (cluster_msec, total_cluster_msec))
                        total_cluster_msec = (total_cluster_msec * 4 + cluster_msec) // 5
                    except Exception as e:
                        trace('failed to cluster_faces: {}'.format(e))
                    
        used_time = int(time.time()) - t
        sleep_sec = 30 - used_time
        if sleep_sec > 3:
            time.sleep(sleep_sec)
    
    p.close()
    p.join()
    print('All processes done!')
    
    trace('clus face work exited')

