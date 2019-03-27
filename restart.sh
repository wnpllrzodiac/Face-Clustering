#!/bin/sh

pid=`ps aux|grep clus_face.py|egrep -v grep| awk '{print $2}'`

if [ ! "$pid"x = ""x ]; then
    echo "Stopping clus_face ..."
    kill -9 $pid
    echo "clus_face(pid ${pid}) stoped"
fi

echo "Starting clus_face ..."
nohup python3 -u clus_face.py >clus_face.py.log 2>&1 &
sleep 1
pid=`ps aux|grep clus_face.py|egrep -v grep| awk '{print $2}'`
echo "clus_face(pid ${pid}) started"
