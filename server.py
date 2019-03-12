#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import cherrypy
import os
import urllib
import json
import cv2
import face_recognition
import datetime
import pymysql

upload_folder = '/home/suhui/work/media/upload_pic'

def repaire_filename(filename):
    return filename.encode('ISO-8859-1').decode('utf-8', 'replace')

def add_pic(imagePath):
    filesize = os.path.getsize(imagePath)
    dt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    image = cv2.imread(imagePath)
    try:
        image.shape
    except:
        print('failed to read img file: %s' % (imagePath))
        return

    # 打开数据库连接
    db = pymysql.connect("192.168.23.71","root","tysxwg07","test" )
    
    # 使用 cursor() 方法创建一个游标对象 cursor
    cursor = db.cursor()

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

    db.close()

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

class ImgClusterServer:
    @cherrypy.expose
    def index(self):
        return """<html>
            <head>
                <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
            </head>
            <body>
                 <form action="upload_test" enctype="multipart/form-data" method="post">
                     filename:<input name="myFile" type="file" />
                     <input type="submit" />
                 </form>
            </body>
        </html>"""

    @cherrypy.expose
    def upload_test(self, myFile):
        out = '''<html>
        <head>
            <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        </head>
        <body>
            myFile length: %s<br />
            myFile filename: %s<br />
            myFile mime-type: %s<br />
            <img src="http://10.102.25.138:9123/img/%s" with="320" height="240"/>
        </body>
        </html>'''

        # Although this just counts the file length, it demonstrates
        # how to read large files in chunks instead of all at once.
        # CherryPy reads the uploaded file into a temporary file;
        # myFile.file.read reads from that.
        basename = repaire_filename(myFile.filename)
        filepath = os.path.join(upload_folder, basename)
        size = 0
        with myFile.file as upload_file, open(filepath, 'wb') as to_save:
            while True:
                data = upload_file.read(8192)
                if not data:
                    break
                to_save.write(data)
                size += len(data)

        return out % (size, basename, myFile.content_type, urllib.parse.quote(basename))
        
    @cherrypy.expose
    @cherrypy.tools.json_out()
    def upload(self, myFile):
        # Although this just counts the file length, it demonstrates
        # how to read large files in chunks instead of all at once.
        # CherryPy reads the uploaded file into a temporary file;
        # myFile.file.read reads from that.
        basename = repaire_filename(myFile.filename)
        filepath = os.path.join(upload_folder, basename)
        size = 0
        with myFile.file as upload_file, open(filepath, 'wb') as to_save:
            while True:
                data = upload_file.read(8192)
                if not data:
                    break
                to_save.write(data)
                size += len(data)

        add_pic(filepath)

        message = {
            'code': 0,
            'msg': 'success',
            'filename': urllib.parse.quote(basename),
            'size': size,
            'mime-type': str(myFile.content_type)
        }
        return message
        
    @cherrypy.expose
    def download(self):
        path = os.path.join(upload_folder, 'pdf_file.pdf')
        return static.serve_file(path, 'application/x-download',
                                 'attachment', os.path.basename(path))

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_pics(self, cat_id='test', page_index = 0, page_size = 10):
        files = []
        i = 0
        start_index = int(page_index) * int(page_size)

        sql = 'SELECT img_path, width, height from clus_img_tb LIMIT %d, %d' % (start_index, int(page_size))
        
        message = {
            'code': -1,
            'msg': 'error',
            'cat_id': cat_id,
            'sql': sql
        }

        # 打开数据库连接
        db = pymysql.connect("192.168.23.71","root","tysxwg07","test" )
        
        # 使用 cursor() 方法创建一个游标对象 cursor
        cursor = db.cursor()

        try:
            cursor.execute(sql)
            values = cursor.fetchall()
            for v in values:
                path = v[0]
                width, height = v[1:] # 192 288
                f = path.split('/')[-1]
                download_url = 'http://10.102.25.138:9123/img/%s' % urllib.parse.quote(f)
                files.append({'image': download_url, 'width': 192, 'height': 192 * height / width})
        except Exception as e:
            print('failed to query pic from db: ', e)
            message['msg'] = e

        db.close()

        if len(files):
            message['code']         = 0
            message['msg']          = 'ok'
            message['page_index']   = int(page_index)
            message['count']        = min(int(page_size), len(files))
            message['more']         = (len(files) == int(page_size))
            message['result']         = files
        else:
            message['error']        = 'no more pic'

        return message                            

if __name__ == '__main__':
    cherrypy.config.update({
            'server.socket_host': '0.0.0.0', #
            'server.socket_port': 9123, #监听端口，默认8080
            'server.log_file': True, #记录日志，默认关闭
            'server.log_access_file': '/tmp/sample.log', #存储访问日志，默认是显示到屏幕上
            'server.log_to_screen': True, #将日志显示到屏幕，默认为True
            'server.log_tracebacks': True, #将跟踪信息写入日志，默认为True。False时只写入500错误
        })
    conf = {
        '/': {
            'tools.sessions.on': True,
            'tools.staticdir.root': os.path.abspath(os.getcwd())
        },
        '/static': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': os.path.abspath(os.getcwd()) + '/html'
        },
        '/img': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': '/home/suhui/work/media/upload_pic'
        }
    }
    cherrypy.quickstart(ImgClusterServer(), '/', conf)