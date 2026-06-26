# -*- coding: utf-8 -*-
# @Time    : 2025/6/16
# @Author  : 小宇
# @File    : code.py

import random
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


class Code(QLabel):
    code_updated = pyqtSignal()  # 定义信号，用于通知登录界面更新验证码

    def __init__(self, parent, w=120, h=40):
        super().__init__(parent)
        self.w = w
        self.h = h
        self.__text = ''
        self.pixmap = None
        self.ui_init()

    def ui_init(self):
        """初始化验证码界面"""
        self.pixmap = QPixmap(self.w, self.h)
        self.painter = QPainter(self.pixmap)
        self.painter.setRenderHint(QPainter.Antialiasing)
        self.painter.fillRect(0, 0, self.w, self.h, QColor(230, 230, 230))
        self.draw_text()
        self.setPixmap(self.pixmap)
        self.setStyleSheet("border: 1px solid #ddd;")
        self.painter.end()
        self.painter = None

    def draw_text(self):
        """绘制验证码文本"""
        chars = 'abcdefghijklmnopqrstuvwxyz1234567890'
        self.__text = ''.join(random.choices(chars, k=4))

        # 绘制字符
        self.painter.setFont(QFont('Arial', 14, QFont.Bold))
        for i, char in enumerate(self.__text):
            color = QColor(random.randint(50, 150), random.randint(50, 150), random.randint(50, 150))
            self.painter.setPen(color)
            self.painter.drawText(25 + 20 * i, 28, char)

        # 绘制干扰线
        for _ in range(2):
            pen = QPen(QColor(random.randint(150, 200), random.randint(150, 200), random.randint(150, 200)), 1)
            self.painter.setPen(pen)
            x1 = random.randint(0, self.w)
            y1 = random.randint(0, self.h)
            x2 = random.randint(0, self.w)
            y2 = random.randint(0, self.h)
            self.painter.drawLine(x1, y1, x2, y2)

    def mousePressEvent(self, event):
        """鼠标点击时刷新验证码并发送更新信号"""
        self.ui_init()
        self.code_updated.emit()
        super().mousePressEvent(event)

    def __del__(self):
        """对象销毁时释放资源"""
        if hasattr(self, 'painter') and self.painter:
            self.painter.end()

    @property
    def text(self):
        """获取验证码文本"""
        return self.__text