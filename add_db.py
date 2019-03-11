#!/usr/bin/python3
 
import pymysql
import datetime
import os
import cv2
from imutils import paths

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
    sql = "INSERT INTO clus_img_tb( \
        cat, img_desc, img_path, width, height, add_time, filesize) \
        VALUES ('%s', '%s',  '%s',  %d,  %d, '%s', %d)" % \
        ('test', 'nothing', imagePath, image.shape[1], image.shape[0], dt, filesize)

    try:
   		# 执行sql语句
        cursor.execute(sql)
  		# 执行sql语句
        db.commit()
        print('pic %s added to db.' % imagePath)
    except Exception as e:
		# 发生错误时回滚
        db.rollback()
        print(e)

'''
CREATE TABLE `clus_img_tb` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `cat` varchar(16) DEFAULT NULL COMMENT '图像分类目录',
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
  `img_idx` INT NOT NULL,
  `left` INT NOT NULL,
  `top` INT NOT NULL,
  `right` INT NOT NULL,
  `bottom` INT NOT NULL,
  `feature` BLOB NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

'''

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

