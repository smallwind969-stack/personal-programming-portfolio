# -*- coding: utf-8 -*-
# @Time    : 2025/4/6 21:49
# @Author  : 小宇
# @File    : registration.py
import sys
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from tools import get_input_validator


class RegisterWidget(QWidget):
    # 定义返回登录页面的信号
    back_to_login_signal = pyqtSignal()

    def __init__(self, w=1000, h=800):
        super().__init__()
        self.w = w
        self.h = h
        self.resize(self.w, self.h)
        self.setWindowTitle('注册界面')
        try:
            self.setWindowIcon(QIcon(QPixmap('./images/icon.png')))
        except Exception:
            print("图标文件未找到，请检查路径。")
        palette = QPalette()
        try:
            palette.setBrush(self.backgroundRole(),
                             QBrush(
                                 QPixmap('./images/bg.jpg').scaled(self.w, self.h)))
            self.setPalette(palette)
        except Exception:
            print("背景图片文件未找到，请检查路径。")
        self.init_window_item()

    def init_window_item(self):
        self.totalLayout = QVBoxLayout()
        self.setLayout(self.totalLayout)

        self.line1 = QHBoxLayout()
        self.totalLayout.addLayout(self.line1)
        self.accLabel = QLabel(' 用户名:', self)
        self.accLabel.setStyleSheet('color:purple')
        self.accEdit = QLineEdit(self)
        self.accEdit.setPlaceholderText(' 请输入账号 ')
        self.accEdit.setStyleSheet('color:red')
        self.validator = get_input_validator()
        self.accEdit.setValidator(self.validator)
        self.line1.addWidget(self.accLabel)
        self.line1.addWidget(self.accEdit)
        self.line1.setContentsMargins(10, 0, 100, 0)

        self.line2 = QHBoxLayout()
        self.totalLayout.addLayout(self.line2)
        self.pwdLabel = QLabel('   密码:', self)
        self.pwdLabel.setStyleSheet('color:purple')
        self.pwdEdit = QLineEdit(self)
        self.pwdEdit.setPlaceholderText(' 请输入密码 ')
        self.pwdEdit.setStyleSheet('color:red')
        self.pwdEdit.setEchoMode(QLineEdit.Password)
        self.pwdEdit.setValidator(self.validator)
        self.line2.addWidget(self.pwdLabel)
        self.line2.addWidget(self.pwdEdit)
        self.line2.setContentsMargins(10, 0, 100, 0)

        self.line3 = QHBoxLayout()
        self.totalLayout.addLayout(self.line3)
        self.pwdConfirmLabel = QLabel('确认密码:', self)
        self.pwdConfirmLabel.setStyleSheet('color:purple')
        self.pwdConfirmEdit = QLineEdit(self)
        self.pwdConfirmEdit.setPlaceholderText(' 请再次输入密码 ')
        self.pwdConfirmEdit.setStyleSheet('color:red')
        self.pwdConfirmEdit.setEchoMode(QLineEdit.Password)
        self.pwdConfirmEdit.setValidator(self.validator)
        self.line3.addWidget(self.pwdConfirmLabel)
        self.line3.addWidget(self.pwdConfirmEdit)
        self.line3.setContentsMargins(0, 0, 100, 0)

        self.buttonLayout = QHBoxLayout()
        self.totalLayout.addLayout(self.buttonLayout)
        self.regBtn = QPushButton('注册', self)
        self.regBtn.setFixedWidth(100)
        self.backBtn = QPushButton('返回登录', self)
        self.backBtn.setFixedWidth(100)
        self.quiBtn = QPushButton('退出', self)
        self.quiBtn.setFixedWidth(100)
        self.buttonLayout.addWidget(self.regBtn)
        self.buttonLayout.addWidget(self.backBtn)
        self.buttonLayout.addWidget(self.quiBtn)

        self.regBtn.clicked.connect(self.register)
        self.backBtn.clicked.connect(self.back_to_login)
        self.quiBtn.clicked.connect(self.quit)

        self.totalLayout.setSpacing(50)

    def register(self):
        username = self.accEdit.text()
        password = self.pwdEdit.text()
        confirm_password = self.pwdConfirmEdit.text()
        if not username or not password or not confirm_password:
            QMessageBox.warning(self, "注册失败", "用户名和密码不能为空，请重新输入。")
            return
        if password != confirm_password:
            QMessageBox.warning(self, "注册失败", "两次输入的密码不一致，请重新输入。")
            self.pwdEdit.clear()
            self.pwdConfirmEdit.clear()
            return
        try:
            with open('users.txt', 'a') as f:
                f.write(f"{username}:{password}\n")
            QMessageBox.information(self, "注册成功", "注册成功，请登录。")
            self.back_to_login()
        except Exception as e:
            QMessageBox.warning(self, "注册失败", f"注册过程中出现错误: {str(e)}")

    def back_to_login(self):
        self.back_to_login_signal.emit()
        self.hide()

    def quit(self):
        self.close()
