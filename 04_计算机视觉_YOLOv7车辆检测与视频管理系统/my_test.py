# -*- coding: utf-8 -*-
# @Time    : 2025/6/16
# @Author  : 小宇
# @File    : my_test.py

import cv2
from driving_detect import driving_detect

my_detect = driving_detect()

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if ret:
        labels, boxs = my_detect.detect(frame)
        print(labels)
        i = 0
        c = (0,255,0)
        if labels is not None:
            for box in boxs:
                cv2.rectangle(frame, (box[0],box[1]), (box[2], box[3]), (0,255,0),2)
                cv2.putText(frame, labels[i],(box[0],box[1]), cv2.FONT_HERSHEY_SIMPLEX,1,c,3)
                i+=1
        cv2.imshow('image', frame)
        cv2.waitKey(3)

cv2.waitKey()
cv2.destroyAllWindows()