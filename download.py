#!/usr/bin/python3
# -*- coding: UTF-8 -*-
from google_images_download import google_images_download

if __name__ == '__main__':
    with open('stars.txt', 'r', encoding='utf-8') as f:
        while True:
            line = f.readline()
            if not line:
                break
            
            name = line.strip('\r\n')
            print(name)
            
            response = google_images_download.googleimagesdownload()
            absolute_image_paths = response.download({
                "proxy": "127.0.0.1:5566",
                "keywords": name,
                "limit": 10
            })
