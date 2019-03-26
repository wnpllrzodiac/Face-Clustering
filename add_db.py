#!/usr/bin/python3
 
import pymysql
import datetime
import time
import os
import cv2
import sys
from imutils import paths
import face_recognition

def add_pic(db, cursor, imagePath):
    filesize = os.path.getsize(imagePath)
    dt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    image = cv2.imread(imagePath)
    try:
        image.shape
    except:
        print('failed to read img file: %s' % (imagePath))
        return

    #INSERT INTO students (class_id, name, gender, score) VALUES (2, '大牛', 'M', 80)
    cat_id = 'test'
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
    except Exception as e:
		    # 发生错误时回滚
        db.rollback()
        print('failed to add img record: ', e)

def save_face(db, cursor, imagePath, cat_id, img_idx, box, feature):
    bytes_feature = feature.tostring()
    #print(bytes_feature)

    try:
      top, right, bottom, left = box
      cursor.execute('insert into clus_face_tb (cat_id, img_idx, box_left, box_top, box_right, box_bottom, feature) \
          values (%s, %s, %s, %s, %s, %s, %s)', (cat_id, img_idx, left, top, right, bottom, bytes_feature))

      db.commit()

      #cursor.execute('select feature from clus_face_tb where img_idx = %s' % (123))
      #values = cursor.fetchall()

      print('face added to db')

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

'''
CREATE TABLE `clus_img_tb` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `cat_id` varchar(64) DEFAULT NULL COMMENT '图像分类目录',
  `img_desc` varchar(256) DEFAULT NULL COMMENT '图像描述',
  `img_path` varchar(512) NOT NULL COMMENT '图像路径',
  `width` int(11) DEFAULT NULL COMMENT '图像宽',
  `height` int(11) DEFAULT NULL COMMENT '图像高',
  `add_time` datetime DEFAULT NULL COMMENT '添加时间',
  `filesize` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
''' 

'''
CREATE TABLE `test`.`clus_face_tb` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `cat_id` varchar(64) DEFAULT NULL
  `img_idx` INT NOT NULL,
  `left` INT NOT NULL,
  `top` INT NOT NULL,
  `right` INT NOT NULL,
  `bottom` INT NOT NULL,
  `feature` BLOB NULL,
  `cluster_idx` INT,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
'''

'''
CREATE TABLE `test`.`clus_cluster_tb` (
  `id` INT NULL AUTO_INCREMENT,
  `cluster_idx` INT NOT NULL,
  `name` VARCHAR(64) NULL,
  `extrainfo` VARCHAR(256) NULL,
  PRIMARY KEY (`id`));
'''

def test1():
    # 打开数据库连接
    db = pymysql.connect("192.168.23.71","root","tysxwg07","test" )
     
    # 使用 cursor() 方法创建一个游标对象 cursor
    cursor = db.cursor()
     
    # 使用 execute()  方法执行 SQL 查询 
    cursor.execute("SELECT VERSION()")
     
    # 使用 fetchone() 方法获取单条数据.
    data = cursor.fetchone()
     
    print ("Database version : %s " % data)

    # add pic

    imagePaths = list(paths.list_images('/media/zodiac/Prog/3g/peoplePhoto'))
    data = []

    for (i, imagePath) in enumerate(imagePaths):
        add_pic(db, cursor, imagePath)

    # 关闭数据库连接
    db.close()

def get_msec():
    msec = int(time.time() * 1000)
    return msec

def test_detec_face(imagePath):
    start_time = get_msec()
    if imagePath[0:4] == 'http':
        cap = cv2.VideoCapture(imagePath)
        ret=cap.isOpened()
        if not ret:
            print('failed to open img file: %s' % (imagePath))
            return      
        ret,image = cap.read()
        #image = image[:,:,::-1]
    else:
        image = cv2.imread(imagePath)
    try:
        image.shape
    except:
        print('failed to read img file: %s' % (imagePath))
        return
    load_msec = get_msec() - start_time

    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    start_time = get_msec()    
    # detect the (x,y) coordinates of the bounding boxes
    # corresponding to each face in the input image
    boxes = face_recognition.face_locations(rgb, model="HOG")
    recognition_msec = get_msec() - start_time
    #print(boxes)

    if len(boxes) == 0:
        print('NO face detected, try equalizeHist')
        
        (b, g, r) = cv2.split(image)
        bH = cv2.equalizeHist(b)
        gH = cv2.equalizeHist(g)
        rH = cv2.equalizeHist(r)
        # 合并每一个通道
        rgb = cv2.merge((bH, gH, rH))
        start_time = get_msec() 
        boxes = face_recognition.face_locations(rgb, model="HOG")
        recognition_msec = get_msec() - start_time

        if len(boxes) == 0:
            print('NO face detected')
            return

    # compute the facial embedding for the face
    start_time = get_msec()
    encodings = face_recognition.face_encodings(rgb, boxes)
    encode_msec = get_msec() - start_time
    #print(encodings)

    print('load %d, recognize %d, encode %d msec' % (load_msec, recognition_msec, encode_msec))

    for box,enc in zip(boxes, encodings):
        print('face ', box)

if __name__ == '__main__':
    img_path = '/data/dllive/piclive/uplaod/1.jpg'
    if len(sys.argv) > 1:
        img_path = sys.argv[1]

    test_detec_face(img_path)
    
