# -*- coding: utf-8 -*-
# @Time    : 2025/4/23 17:46
# @Author  : 小宇
# @File    : test.py
import sys
from PyQt5.QtCore import Qt, QStringListModel
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *


class MainWidget(QWidget):
    def __init__(self, width=1000, height=600):
        super().__init__()
        self.w = width
        self.h = height
        self.initUI()
        self.init_window_item()

    def initUI(self):
        self.setWindowIcon(QIcon('./images/icon.png'))
        self.setWindowTitle('智慧工地 - AI检测系统')
        self.resize(self.w, self.h)
        # 设置背景图片
        pixmap = QPixmap('./images/bg.jpg')
        if pixmap.isNull():
            print("图片加载失败，请检查图片路径和文件是否损坏。")
        else:
            palette = QPalette()
            palette.setBrush(self.backgroundRole(), QBrush(pixmap.scaled(self.w, self.h)))
            self.setPalette(palette)
            self.setAutoFillBackground(True)  # 确保背景自动填充
    def init_window_item(self):
        # 整体布局
        self.main_layout = QVBoxLayout()

        # 顶部布局
        self.top_layout = QVBoxLayout()

        # 顶部标题布局
        self.title_layout = QHBoxLayout()
        self.title_label = QLabel('智慧工地 - AI检测系统')
        self.title_label.setStyleSheet('color:white')
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_layout.addWidget(self.title_label)
        self.top_layout.addLayout(self.title_layout)

        # 顶部按钮布局
        self.button_layout = QHBoxLayout()

        # 添加左侧间隔项，减小宽度
        left_spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.button_layout.addItem(left_spacer)

        self.play_button = QPushButton('播放')
        self.stop_button = QPushButton('停止')
        self.camera_button = QPushButton('打开摄像头')
        self.cloud_detection_button = QPushButton('云检测')
        self.button_layout.addWidget(self.play_button)
        self.button_layout.addWidget(self.stop_button)
        self.button_layout.addWidget(self.camera_button)
        self.button_layout.addWidget(self.cloud_detection_button)

        # 添加右侧间隔项
        right_spacer = QSpacerItem(300, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.button_layout.addItem(right_spacer)

        # 设置按钮之间的间距
        self.button_layout.setSpacing(30)

        self.top_layout.addLayout(self.button_layout)
        self.main_layout.addLayout(self.top_layout)

        # 中间整体布局（左右分栏及摄像头显示区域）
        self.middle_layout = QHBoxLayout()

        # 左侧信息布局
        self.left_info_layout = QVBoxLayout()
        self.video_stats_label = QLabel("监控视频数：4个\n已检测视频数：10个\n未检测视频数：13个")
        self.video_stats_label.setStyleSheet('color:white')
        self.abnormal_stats_label = QLabel("当前监控工地异常情况：\n无安全帽数：5个\n无穿反光衣数：8个")
        self.abnormal_stats_label.setStyleSheet('color:white')
        self.left_info_layout.addWidget(self.video_stats_label)
        self.left_info_layout.addWidget(self.abnormal_stats_label)
        self.middle_layout.addLayout(self.left_info_layout)

        # 摄像头显示区域
        self.camera_widget = QWidget()
        # self.camera_widget.setStyleSheet("background-color: blank;")  # 设置背景颜色，方便查看区域位置
        self.middle_layout.addWidget(self.camera_widget, stretch=3)  # stretch参数可调整各部分的宽度比例

        # 右侧视频列表布局
        self.right_list_layout = QVBoxLayout()
        self.construction_video_label = QLabel("工地监控视频列表->>")
        self.construction_video_label.setStyleSheet('color:white')
        self.detected_video_label = QLabel("检测后视频列表->>")
        self.detected_video_label.setStyleSheet('color:white')
        self.construction_video_list_view = QListView()
        self.detected_video_list_view = QListView()
        self.construction_video_list_view.setSelectionMode(QListView.ExtendedSelection)
        self.detected_video_list_view.setSelectionMode(QListView.ExtendedSelection)
        # 模拟添加视频文件名到工地监控视频列表
        video_files = ["20250218202407.mp4", "20250218202435.mp4", "20250222110735.mp4",
                       "20250222110802.mp4", "20250222114558.mp4", "工地.mp4"]
        self.model = QStringListModel()
        self.model.setStringList(video_files)
        self.construction_video_list_view.setModel(self.model)
        # 模拟添加检测后视频文件名到检测后视频列表
        detected_video_files = ["20250218202407_check.mp4", "工地_check.mp4"]
        self.detected_model = QStringListModel()
        self.detected_model.setStringList(detected_video_files)
        self.detected_video_list_view.setModel(self.detected_model)
        self.right_list_layout.addWidget(self.construction_video_label)
        self.right_list_layout.addWidget(self.construction_video_list_view)
        self.right_list_layout.addWidget(self.detected_video_label)
        self.right_list_layout.addWidget(self.detected_video_list_view)
        self.middle_layout.addLayout(self.right_list_layout)

        self.main_layout.addLayout(self.middle_layout)

        self.setLayout(self.main_layout)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_widget = MainWidget()
    main_widget.show()
    sys.exit(app.exec_())
