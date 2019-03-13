#!/usr/bin/python3
 
import pymysql
import os
import cv2
import numpy as np
import face_recognition
import matplotlib.pyplot as plt
from imutils import paths
from imutils import build_montages
from sklearn.cluster import DBSCAN

def update_cluster(db, cursor, face_idx, label_id):
      try:
          sql = 'UPDATE clus_face_tb SET cluster_idx = %d WHERE id = %d' % (label_id, face_idx)
          print('sql: ', sql)
          cursor.execute(sql)
          db.commit()
      except Exception as e:
        print('failed to update face data: ', e)
        db.rollback()

def cluster_faces(db, cursor, cat_id):
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

    print("[INFO] total cluster_face_count %d" % cluster_face_count)

if __name__ == '__main__':
    # 打开数据库连接
    db = pymysql.connect("192.168.23.71","root","tysxwg07","test" )
    
    # 使用 cursor() 方法创建一个游标对象 cursor
    cursor = db.cursor()
    
    cluster_faces(db, cursor, 'test')

    # 关闭数据库连接
    db.close()

