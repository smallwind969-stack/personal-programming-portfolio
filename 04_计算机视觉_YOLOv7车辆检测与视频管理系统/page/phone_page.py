# -*- coding: utf-8 -*-
# @Time    : 2025/6/16
# @Author  : 小宇
# @File    : phone_page.py

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton


class PhonePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        title = QLabel("电话页面")
        title.setStyleSheet("font-size: 24px; color: white;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # 返回按钮
        back_btn = QPushButton("返回首页")
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: #444;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                margin-top: 20px;
            }
            QPushButton:hover {
                background-color: #555;
            }
        """)
        back_btn.clicked.connect(lambda: self.parentWidget().setCurrentIndex(0))  # 切回首页
        layout.addWidget(back_btn, alignment=Qt.AlignCenter)

        self.setStyleSheet("background-color: #2b2b2b;")