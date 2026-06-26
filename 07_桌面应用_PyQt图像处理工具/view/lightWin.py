# -*- coding: utf-8 -*-
# @Time    : 2025/5/17 14:07
# @Author  : 小宇
# @File    : lightWin.py
import os
import cv2
import numpy as np
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *


class lightWin(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(900, 700)
        self.setWindowTitle('亮度调整')
        self.setStyleSheet('background-color:rgba(20,100,140,25%);font:24px;color:white')
        self.pathLight = None  # 当前操作的图片路径
        self.temp = './temp_image/light.jpg'  # 临时文件路径
        self.main_window = None  # 主窗口引用
        self.init_control()

    def init_control(self):
        # 主窗口组件
        center_widget = QWidget()
        self.setCentralWidget(center_widget)

        # 创建主布局
        self.totalLaout = QVBoxLayout()
        center_widget.setLayout(self.totalLaout)

        # 第一行：标题和确认按钮
        self.line1 = QHBoxLayout()
        self.totalLaout.addLayout(self.line1)
        self.label = QLabel("设置亮度: 9", self)
        self.label.setStyleSheet('color:white;font:24px')
        self.B1 = QPushButton('确认', self)
        self.line1.addWidget(self.label)
        self.line1.addWidget(self.B1)

        # 第二行：亮度滑块
        self.line2 = QHBoxLayout()
        self.totalLaout.addLayout(self.line2)
        self.start = QSlider(Qt.Orientation.Horizontal)
        self.start.setMinimum(1)  # 最小值设为1，避免亮度为0
        self.start.setMaximum(50)  # 调整范围为1-50
        self.start.setTickInterval(1)
        self.start.setSingleStep(1)
        self.start.setValue(9)  # 默认值为9
        self.start.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.line2.addWidget(self.start)

        # 第三行：原图和预览图
        self.line3 = QHBoxLayout()
        self.totalLaout.addLayout(self.line3)
        self.L1 = QLabel()  # 原图
        self.L2 = QLabel()  # 预览图
        self.L1.setAlignment(Qt.AlignCenter)
        self.L2.setAlignment(Qt.AlignCenter)
        self.line3.addWidget(self.L1)
        self.line3.addWidget(self.L2)

        # 设置布局比例
        self.line1.setContentsMargins(10, 10, 600, 10)
        self.line2.setContentsMargins(10, 10, 600, 10)

        # 连接信号和槽
        self.start.valueChanged.connect(self.on_value_changed)
        self.B1.clicked.connect(self.save_result)

    def showEvent(self, event):
        """窗口显示时加载图片"""
        print('亮度窗口显示')
        if self.pathLight and os.path.exists(self.pathLight):
            self.L1.setPixmap(QPixmap(self.pathLight).scaledToWidth(400))
            self.L2.setPixmap(QPixmap(self.pathLight).scaledToWidth(400))
        else:
            print("错误：未设置图片路径或路径不存在")

    def on_value_changed(self, value):
        """
        亮度滑块值变化时更新预览图
        :param value: 滑块当前值
        """
        try:
            if not self.pathLight or not os.path.exists(self.pathLight):
                print("错误：未设置图片路径或路径不存在")
                return

            # 更新标签显示
            self.label.setText(f'设置亮度: {value}')

            # 计算亮度因子（0.1-2.0）
            brightness_factor = value / 10.0

            # 读取图片并转换到HSV色彩空间
            img = cv2.imread(self.pathLight)
            hsv_img = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

            # 分离通道并调整亮度
            H, S, V = cv2.split(hsv_img)
            adjusted_V = np.clip(V * brightness_factor, 0, 255).astype(hsv_img.dtype)

            # 合并通道并转回BGR
            adjusted_hsv = cv2.merge([H, S, adjusted_V])
            adjusted_img = cv2.cvtColor(adjusted_hsv, cv2.COLOR_HSV2BGR)

            # 保存调整后的图片
            os.makedirs(os.path.dirname(self.temp), exist_ok=True)
            cv2.imwrite(self.temp, adjusted_img)

            # 更新预览
            self.L2.setPixmap(QPixmap(self.temp).scaledToWidth(400))

        except Exception as e:
            print(f"亮度调整出错: {e}")

    def save_result(self):
        """保存调整结果并返回主窗口"""
        if not hasattr(self, 'main_window') or self.main_window is None:
            print("错误：未设置主窗口引用")
            return

        if self.temp and os.path.exists(self.temp):
            # 传递结果给主窗口
            self.main_window.tempFile = self.temp
            self.main_window.back_from_light()  # 调用主窗口的回调函数
            self.close()  # 关闭亮度调整窗口
        else:
            print("无法保存结果：临时文件不存在")