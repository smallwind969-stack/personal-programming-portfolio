# -*- coding: utf-8 -*-
# @Time    : 2025/4/12 10:35
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
        self.ui_init()

    def ui_init(self):
        self.pixmap = QPixmap(self.w, self.h)
        self.painter = QPainter(self.pixmap)
        self.painter.setBrush(QBrush(QColor('gray')))
        self.painter.drawRect(0, 0, self.w, self.h)
        self.draw_text()
        self.setPixmap(self.pixmap)

    def draw_text(self):
        temp_text = 'abcdefghijklmnopqrstuvwxyz1234567890'
        self.__text = ''
        for i in range(4):
            num = random.randint(0, 35)
            self.__text += temp_text[num]
        self.painter.setFont(QFont('宋体', 12))
        for i in range(4):
            self.painter.setPen(QColor(random.randint(220, 255), random.randint(200, 255),
                                       random.randint(220, 255), random.randint(200, 255)))
            self.painter.drawText(10 + 22 * i, 30, self.__text[i])

    def mousePressEvent(self, event):
        self.painter.drawRect(0, 0, self.w, self.h)
        self.draw_text()
        self.setPixmap(self.pixmap)
        self.code_updated.emit()  # 发射信号通知登录界面更新验证码

    @property
    def text(self):
        return self.__text