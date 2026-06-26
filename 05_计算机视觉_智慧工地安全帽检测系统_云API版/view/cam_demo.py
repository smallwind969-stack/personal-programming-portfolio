# -*- coding: utf-8 -*-
# @Time    : 2025/4/26 14:53
# @Author  : 小宇
# @File    : cam_demo.py
import cv2


def videocapture():
    # 获取摄像头的对象
    cap = cv2.VideoCapture(0)  # 本机的摄像头
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))  # 获取摄像头的图像的宽度
    height = int(cap.get(4))  # 高度
    fps = int(cap.get(cv2.CAP_PROP_FPS))  # 帧率
    fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))  # 视频编码

    # 定义视频输出的对象
    writer = cv2.VideoWriter('../videos/video_out.mp4', fourcc, fps, (width, height))
    # 开启摄像头
    while cap.isOpened():
        ret, frame = cap.read()  # 读取摄像头画面
        print(frame)
        cv2.imshow('video', frame)  # 显示画面
        key = cv2.waitKey(24)
        writer.write(frame)
        if key == ord('q'):  # 按q退出
            break

    cap.release()  # 释放摄像头
    writer.release()
    cv2.destroyAllWindows()

videocapture()
