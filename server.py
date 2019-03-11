#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import cherrypy
import os
import urllib
import json

upload_folder = '/home/suhui/work/media/upload_pic'

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

        message = {
            'code': 0,
            'msg': 'success',
            'filename': 'lll', #urllib.parse.quote(basename),
            'size': size,
            'mime-type': str(myFile.content_type)
        }
        return message
        
    @cherrypy.expose
    def download(self):
        path = os.path.join(upload_folder, 'pdf_file.pdf')
        return static.serve_file(path, 'application/x-download',
                                 'attachment', os.path.basename(path))

if __name__ == '__main__':
    cherrypy.config.update({
            'server.socket_host': '10.102.25.138', #
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
        '/img': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': '/home/suhui/work/media/upload_pic'
        }
    }
    cherrypy.quickstart(ImgClusterServer(), '/', conf)