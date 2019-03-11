#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import numpy as np
import MySQLdb
import base64
import sys
    
if __name__ == '__main__':
    feature = np.array([1.0, 2.0, 3.0])
    print(feature)
    print(feature.dtype)
    
    try:
        db = MySQLdb.connect("192.168.23.71", "root", "tysxwg07", "test", charset='utf8' )

        # 使用cursor()方法获取操作游标 
        cursor = db.cursor()

        # 使用execute方法执行SQL语句
        cursor.execute("SELECT VERSION()")

        # 使用 fetchone() 方法获取一条数据
        data = cursor.fetchone()

        print("Database version : %s " % data)

        bytes_feature = feature.tostring()
        print(bytes_feature)
        #cursor.execute('insert into testblob values (%s, "%s")' % (2, bytes.decode(data)))
        cursor.execute('insert into testblob values (%s, %s)', (2, bytes_feature))
        
        db.commit()
        
        cursor.execute('select feature from testblob where framenum = %s' % (2))
        values = cursor.fetchall()
        
        print(values)
        feature = np.frombuffer(values[0][0], dtype=np.float64) #np.float32
        print(feature)

        # 关闭数据库连接
        db.close()
    except Exception as e:
        print("Exception: ", e);
        sys.exit(1)