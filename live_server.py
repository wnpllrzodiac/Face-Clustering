#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import config
import cherrypy
import os
import urllib
import json
import cv2
import face_recognition
import datetime
import pymysql
import uuid
import hashlib
import time
from imutils import build_montages

def repaire_filename(filename):
    return filename.encode('ISO-8859-1').decode('utf-8', 'replace')

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
    def upload_test(self, myFile, cat_id = 'test'):
        out = '''<html>
        <head>
            <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        </head>
        <body>
            myFile length: %s<br />
            myFile filename: %s<br />
            myFile mime-type: %s<br />
            <img src="http://%s:%d/img/%s" with="320" height="240"/>
        </body>
        </html>'''

        # Although this just counts the file length, it demonstrates
        # how to read large files in chunks instead of all at once.
        # CherryPy reads the uploaded file into a temporary file;
        # myFile.file.read reads from that.
        basename = repaire_filename(myFile.filename)
        m = hashlib.md5()
        str_file = '%d_%s' % (int(time.time() * 1000), basename)
        m.update(str_file.encode('utf-8'))
        folder = os.path.join(config.upload_folder, cat_id)
        if not os.path.exists(folder):
            os.mkdir(folder)
        new_basename = m.hexdigest() + '.' + basename.split('.')[-1]
        filepath = os.path.join(folder, new_basename)
        size = 0
        with myFile.file as upload_file, open(filepath, 'wb') as to_save:
            while True:
                data = upload_file.read(8192)
                if not data:
                    break
                to_save.write(data)
                size += len(data)

        return out % (size, basename, myFile.content_type, config.image_server_ip, config.image_server_port, new_basename)
        
    @cherrypy.expose
    @cherrypy.tools.json_out()
    def upload(self, myFile, cat_id = 'test'):
        # Although this just counts the file length, it demonstrates
        # how to read large files in chunks instead of all at once.
        # CherryPy reads the uploaded file into a temporary file;
        # myFile.file.read reads from that.
        basename = repaire_filename(myFile.filename)
        m = hashlib.md5()
        str_file = '%d_%s' % (int(time.time() * 1000), basename)
        m.update(str_file.encode('utf-8'))
        folder = os.path.join(config.upload_folder, cat_id)
        if not os.path.exists(folder):
            os.mkdir(folder)
        filepath = os.path.join(folder, m.hexdigest() + '.' + basename.split('.')[-1])
        size = 0
        with myFile.file as upload_file, open(filepath, 'wb') as to_save:
            while True:
                data = upload_file.read(8192)
                if not data:
                    break
                to_save.write(data)
                size += len(data)

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
        path = os.path.join(config.upload_folder, 'pdf_file.pdf')
        return static.serve_file(path, 'application/x-download',
                                 'attachment', os.path.basename(path))

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_cluster_count(self, cat_id='test'):
        sql = 'SELECT max(cluster_idx) from clus_face_tb where cat_id = "%s"' % (cat_id)
        
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
            count = values[0][0]
        except Exception as e:
            print('failed to get cluster count from db: ', e)
            message['msg'] = e

        db.close()

        if count and count >= 0:
            message['code']         = 0
            message['msg']          = 'ok'
            message['cluster_count']= count + 1
        else:
            message['error']        = 'no cluster face count'

        return message   

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_cluster_faces(self, cat_id='test', cluster_idx=0):
        sql = 'SELECT img_idx,img_path,box_top,box_right,box_bottom,box_left,clus_img_tb.width,clus_img_tb.height from clus_face_tb \
            left join clus_img_tb on clus_img_tb.id = clus_face_tb.img_idx \
            where clus_face_tb.cluster_idx = %d and clus_face_tb.cat_id = "%s"' \
                % (int(cluster_idx), cat_id)
        
        message = {
            'code': -1,
            'msg': 'error',
            'cat_id': cat_id,
            'cluster_idx': int(cluster_idx),
            'sql': sql
        }

        # 打开数据库连接
        db = pymysql.connect("192.168.23.71","root","tysxwg07","test" )
        
        # 使用 cursor() 方法创建一个游标对象 cursor
        cursor = db.cursor()

        faces = []

        try:
            cursor.execute(sql)
            values = cursor.fetchall()

            for v in values:
                idx = v[0]
                path = v[1]
                top, right, bottom, left = v[2:6]
                width, height = v[6:]
                f = path.split('/')[-1]
                download_url = 'http://%s:%d/img/%s/%s' % (config.image_server_ip, config.image_server_port, cat_id, f)
                faces.append({
                    'image': download_url, 
                    'top': top, 
                    'right': right,
                    'bottom': bottom,
                    'left': left,
                    'width': 480,
                    'height': int(480 * height / width)
                })
        except Exception as e:
            print('failed to get cluster faces from db: ', e)
            message['msg'] = e

        db.close()

        if len(faces) > 0:
            message['code']         = 0
            message['msg']          = 'ok'
            message['result']       = faces
        else:
            message['error']        = 'no cluster faces'

        return message

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_pic_faces(self, img_id):
        sql = 'SELECT clus_face_tb.id,img_path,clus_face_tb.box_top,clus_face_tb.box_right,clus_face_tb.box_bottom,clus_face_tb.box_left from clus_face_tb \
            left join clus_img_tb on clus_img_tb.id = clus_face_tb.img_idx WHERE img_idx = %d' % (int(img_id))
        
        message = {
            'code': -1,
            'msg': 'error',
            'img_id': img_id,
            'sql': sql
        }

        # 打开数据库连接
        db = pymysql.connect("192.168.23.71","root","tysxwg07","test" )
        
        # 使用 cursor() 方法创建一个游标对象 cursor
        cursor = db.cursor()

        faces = []

        try:
            cursor.execute(sql)
            values = cursor.fetchall()

            if len(values):
                path = values[0][1]
                f = path.split('/')[-1]
                download_url = 'http://%s:%d/img/%s' % (config.image_server_ip, config.image_server_port, urllib.parse.quote(f))
                message['image'] = download_url
            for v in values:
                idx = v[0]
                top, right, bottom, left = v[2:6]
                faces.append({
                    'top': top, 
                    'right': right,
                    'bottom': bottom,
                    'left': left
                })
        except Exception as e:
            print('failed to get pic faces from db: ', e)
            message['msg'] = e

        db.close()

        if len(faces) > 0:
            message['code']         = 0
            message['msg']          = 'o.k.'
            message['result']       = faces
        else:
            message['error']        = 'no pic faces'

        return message
        
    @cherrypy.expose
    def get_cluster_montage(self, cat_id='test', cluster_idx=0):
        out = '''<html>
        <head>
            <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        </head>
        <body>
            <a id="prev_page" href="%s">上一页</a>
            <a id="next_page" href="%s">下一页</a>
            <a id="all_pics" href="%s">图片</a>
            </p>
            <img src="http://%s:9123/montage/%s" with="640" height="480"/>
        </body>
        </html>'''
        pic_name = '{}_{}_{}.jpg'.format(cat_id, cluster_idx, uuid.uuid1())
        
        sql = 'SELECT img_idx,img_path,box_top,box_right,box_bottom,box_left from clus_face_tb \
            left join clus_img_tb on clus_img_tb.id = clus_face_tb.img_idx \
            where clus_face_tb.cluster_idx = %d and clus_face_tb.cat_id = "%s"' \
                % (int(cluster_idx), cat_id)

        # 打开数据库连接
        db = pymysql.connect("192.168.23.71","root","tysxwg07","test" )
        
        # 使用 cursor() 方法创建一个游标对象 cursor
        cursor = db.cursor()

        faces = []

        try:
            cursor.execute(sql)
            values = cursor.fetchall()

            for v in values:
                idx = v[0]
                path = v[1]
                top, right, bottom, left = v[2:6]
                
                image = cv2.imread(path)
                face = image[top:bottom, left:right]

                # force resize the face ROI to 96x96 and then add it to the
                # faces montage list
                face = cv2.resize(face, (96,96))
                faces.append(face)

            # create a montage using 96x96 "tiles" with 5 rows and 5 columns
            montage = build_montages(faces, (96,96), (5,5))[0]
            cv2.imwrite('/tmp/{}'.format(pic_name), montage)
        except Exception as e:
            print('failed to get cluster faces from db: ', e)

        db.close()

        return out % (\
            'get_cluster_montage?cat_id={}&cluster_idx={}'.format(cat_id, int(cluster_idx) - 1), \
            'get_cluster_montage?cat_id={}&cluster_idx={}'.format(cat_id, int(cluster_idx) + 1), \
            'static/waterfall.html?cat_id={}&cluster_idx={}'.format(cat_id, cluster_idx), \
            config.server_ip, pic_name)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_pic(self, img_id):
        sql = 'SELECT img_path,width,height,cat_id from clus_img_tb WHERE id = %s' % (img_id)
        
        message = {
            'code': -1,
            'msg': 'error',
            'img_id': img_id,
            'sql': sql
        }

        # 打开数据库连接
        db = pymysql.connect("192.168.23.71","root","tysxwg07","test")
        
        # 使用 cursor() 方法创建一个游标对象 cursor
        cursor = db.cursor()

        try:
            cursor.execute(sql)
            values = cursor.fetchall()
            if len(values):
                path = values[0][0]
                w,h = values[0][1:3]
                cat_id = values[0][3]
                f = path.split('/')[-1]
                download_url = 'http://%s:%d/img/%s/%s' % (config.image_server_ip, config.image_server_port, cat_id, f)
                message['code'] = 0
                message['msg']  = 'o.k.'
                message['image']  = download_url
                message['width']  = w
                message['height'] = h
            else:
                message['msg']  = 'no such pic'
        except Exception as e:
            print('failed to query pic from db: ', e)
            message['msg'] = e

        db.close()

        return message
        
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
                width, height = v[1:3] # 192 288
                f = path.split('/')[-1]
                download_url = 'http://%s:%d/img/%s/%s' % (config.image_server_ip, config.image_server_port, cat_id, f)
                files.append({
                    'image': download_url,
                    'width': 480,
                    'height': int(480 * height / width)
                })
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
        
    @cherrypy.expose
    @cherrypy.tools.json_out()
    def clean_db(self):
        message = {
            'code': 0,
            'msg': 'o.k.',
        }
        
        try:
            db = pymysql.connect("192.168.23.71","root","tysxwg07","test" )
            cursor = db.cursor()
            cursor.execute('truncate table clus_img_tb')
            cursor.execute('truncate table clus_face_tb')
            cursor.execute('truncate table clus_cluster_tb')
        except Exception as e:
            print('failed to clean db: ', e)
            message['code'] = -1
            message['msg'] = e
            
        return message

if __name__ == '__main__':
    port = 9123
    
    conf = {
        'global': {
            'server.shutdown_timeout': 1,
            'server.socket_host': '0.0.0.0',
            'server.socket_port': port,
            'tools.encode.on': True,
            'tools.encode.encoding': "utf-8",
            #'server.thread_pool': 2, # single thread server.
        },
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
            'tools.staticdir.dir': config.image_folder
        },
        '/montage': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': '/tmp'
        }
    }
    cherrypy.quickstart(ImgClusterServer(), '/', conf)
