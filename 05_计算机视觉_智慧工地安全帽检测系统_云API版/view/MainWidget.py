# -*- coding: utf-8 -*-
# @Time    : 2025/4/25 10:51
# @Author  : 小宇
# @File    : MainWidget.py
import os
import time
import cv2
import tempfile
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import matplotlib.image as mping
import matplotlib.pyplot as plt
from apig_sdk import signer
import requests
import json

from view import hat
from view.VideoWidget import VideoWidget  # 绝对导入


class MainWidget(QWidget):
    # 定义一个信号，用于在帧计数达到200时触发保存操作
    save_video_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.frameCount = 0
        self.video_path = "./videos/"  # 初始化视频路径
        self.video_check_path = "./check_videos/"
        self.init_win()
        self.init_control()  # 调用初始化UI控件的方法
        self.init_connections()  # 初始化信号连接

    def init_win(self):
        self.setFixedSize(1300, 720)
        self.setWindowTitle('智慧工地 - AI检测系统')
        self.setWindowIcon(QIcon('./images/icon.png'))

        pale = QPalette()
        pale.setBrush(self.backgroundRole(), QBrush(QPixmap('./images/bg.jpg').scaled(self.size())))
        self.setPalette(pale)

    def init_control(self):
        self.L1 = QLabel('智慧工地 - AI检测系统', self)
        self.L1.setStyleSheet('color:white;font:20px')
        self.L1.setGeometry(560, 12, 300, 30)

        self.totalLayout = QHBoxLayout()
        self.setLayout(self.totalLayout)

        self.left = QVBoxLayout()
        self.right = QVBoxLayout()
        self.mid = QVBoxLayout()

        self.totalLayout.addLayout(self.left)
        self.totalLayout.addLayout(self.mid)
        self.totalLayout.addLayout(self.right)

        self.left_line1 = QLabel("监控视频数：6个\n已检测视频数：6个\n未检测视频数：0个")
        self.left_line1.setStyleSheet('color:white;font:20px')
        self.left_line2 = QLabel('安全帽检测数：0个\n反光衣检测数：0个')
        self.left_line2.setStyleSheet('color:white;font:20px')
        self.left_line1.setContentsMargins(40, 10, 0, 0)
        self.left_line2.setContentsMargins(40, 10, 0, 0)
        self.left.addWidget(self.left_line1)
        self.left.addWidget(self.left_line2)

        # 中间
        self.video_widget = VideoWidget()
        self.mid.addWidget(self.video_widget)
        self.imgLab = QLabel('请选择视频', self)
        self.imgLab.setStyleSheet('color:white; font:20px')
        self.imgLab.setAlignment(Qt.AlignCenter)
        self.mid.addWidget(self.imgLab)

        self.right_line1 = QLabel('工地监控视频列表', self)
        self.right_line1.setStyleSheet('color:white;font:20px')
        self.view1 = QListView(self)
        self.view1.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.view1.setSelectionMode(QAbstractItemView.SingleSelection)

        self.right_line2 = QLabel('检测后视频列表', self)
        self.right_line2.setStyleSheet('color:white;font:20px')
        self.view2 = QListView(self)
        self.view2.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.view2.setSelectionMode(QAbstractItemView.SingleSelection)

        self.right.addWidget(self.right_line1)
        self.right.addWidget(self.view1)
        self.right.addWidget(self.right_line2)
        self.right.addWidget(self.view2)

        self.totalLayout.setStretchFactor(self.left, 2)
        self.totalLayout.setStretchFactor(self.mid, 6)
        self.totalLayout.setStretchFactor(self.right, 2)

        self.mid.setContentsMargins(100, 20, 20, 20)
        self.right.setContentsMargins(0, 90, 10, 10)

        # 初始化视频列表
        self.updata_filelist()
        self.updata_chack_video()

    def init_connections(self):
        # 连接保存视频信号到保存和更新方法
        self.save_video_signal.connect(self.save_and_update)
        # 连接视频列表点击事件
        self.view1.clicked.connect(self.list_view_click)

    def save_and_update(self):
        if hasattr(self.video_widget, 'out') and self.video_widget.out:
            self.video_widget.out.release()

        if hasattr(self.video_widget, 'cap') and self.video_widget.cap and self.video_widget.cap.isOpened():
            self.cap_width = int(self.video_widget.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.cap_height = int(self.video_widget.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.timeStr = time.strftime('%Y%m%d%H%M%S', time.localtime())

            # 创建新的视频写入器
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.video_widget.out = cv2.VideoWriter(
                f'{self.video_path}{self.timeStr}.mp4',
                fourcc,
                10,
                (self.cap_width, self.cap_height)
            )

            # 更新视频列表
            self.updata_filelist()

    def updata_filelist(self):
        self.list1 = self.get_video_name(self.video_path)
        self.slm1 = QStringListModel()
        self.slm1.setStringList(self.list1)
        self.view1.setModel(self.slm1)

    def list_view_click(self, item):
        i = item.row()
        # 从list中获取路径
        path = os.path.join(self.video_path, self.list1[i])
        # 初始化视频但不自动播放
        self.video_widget.video_init_control(path)
        self.video_widget.get_fist_frame()
        # 停止任何可能正在运行的定时器
        self.video_widget.time1.stop()

    def updata_chack_video(self):
        video_files = self.get_video_name(self.video_check_path)
        slm2 = QStringListModel()
        slm2.setStringList(video_files)
        self.view2.setModel(slm2)

    def get_video_name(self, path):
        try:
            files = os.listdir(path)
            # 过滤出视频文件
            video_extensions = ['.mp4', '.avi', '.mov', '.mkv']
            return [f for f in files if os.path.splitext(f)[1].lower() in video_extensions]
        except FileNotFoundError:
            print(f"路径 {path} 不存在")
            return []

