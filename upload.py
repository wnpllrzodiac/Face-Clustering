#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import random
import requests
import os
import json
import sys
from requests_toolbelt.multipart.encoder import MultipartEncoder

server_ip='10.102.25.132'
    
def fix_filename(filename):
    return filename.encode('utf-8').decode('ISO-8859-1', 'replace')

def listDir(rootDir):
    for filename in os.listdir(rootDir):
        pathname = os.path.join(rootDir, filename)
        print('pathname: %s' % pathname)
        if os.path.isdir(pathname):
            listDir(pathname)
        else:
            upload_file(pathname)
    
def upload_file(file):
    if not os.path.exists(file):
        print('file %s NOT exists! ' % file)
        return
    
    print('uploading file %s ...' % file)
    
    size = os.path.getsize(file)
    
    url = 'http://{}:9123/upload'.format(server_ip)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:50.0) Gecko/20100101 Firefox/50.0', 
        'Referer': url 
    }
    
    multipart_encoder = MultipartEncoder(
        fields = {
            'myFile': (fix_filename(os.path.basename(file)), open(file, 'rb'), 'application/octet-stream')
        },
        boundary = '-----------------------------' + str(random.randint(1e28, 1e29 - 1))
    )
    headers['Content-Type'] = multipart_encoder.content_type
    #请求头必须包含一个特殊的头信息,类似于Content-Type: multipart/form-data; boundary=${bound}
    #注意：这里请求头也可以自己设置Content-Type信息，用于自定义boundary
    r = requests.post(url, data=multipart_encoder, headers=headers)
    print(r.text)
    
if __name__ == '__main__':
    #file = 'D:\\3g\\peoplePhoto\\【有图】#TYZ# 8P 摄影：JNLeung\\【有图】#TYZ# 8P 摄影：JNLeung_002.jpg'
    #upload_file(file)
   
    folder = '/home/suhui/work/media/peoplePhoto'
    if len(sys.argv) > 1:
        folder = sys.argv[1]
    listDir(folder) 
