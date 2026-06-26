# -*- coding: utf-8 -*-
# @Time    : 2025/6/16
# @Author  : 小宇
# @File    : registration.py

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from code import Code as RegistrationCode  # 复用验证码组件
from page.database import DatabaseManager


class RegisterWidget(QWidget):
    back_to_login_signal = pyqtSignal()  # 返回登录界面的信号

    def __init__(self, db_config, w=800, h=600):
        super().__init__()
        self.w = w
        self.h = h
        self.resize(self.w, self.h)
        self.setWindowTitle('智能座舱 - 注册')
        self.setWindowIcon(QIcon(QPixmap("images/icon.png")))
        self.registration_code = RegistrationCode(self)
        self.registration_code.setFixedSize(120, 40)

        # 初始化数据库管理器
        self.db_config = db_config
        self.db_manager = DatabaseManager(db_config)
        self.init_window_items()

    def init_window_items(self):
        """初始化界面控件"""
        self.total_layout = QVBoxLayout()
        self.total_layout.setAlignment(Qt.AlignCenter)
        self.setLayout(self.total_layout)

        # 标题
        title_label = QLabel("注册新账户")
        title_label.setFont(QFont("微软雅黑", 24, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        self.total_layout.addWidget(title_label)
        self.total_layout.addSpacing(50)

        # 用户名输入
        user_layout = QHBoxLayout()
        user_label = QLabel("用户名:")
        user_label.setFont(QFont("微软雅黑", 12))
        self.user_edit = QLineEdit()
        user_layout.addWidget(user_label)
        user_layout.addWidget(self.user_edit)
        self.total_layout.addLayout(user_layout)
        self.total_layout.addSpacing(20)

        # 密码输入
        pwd_layout = QHBoxLayout()
        pwd_label = QLabel("密码:")
        pwd_label.setFont(QFont("微软雅黑", 12))
        self.pwd_edit = QLineEdit()
        self.pwd_edit.setEchoMode(QLineEdit.Password)

        # 添加密码可见性切换按钮
        self.pwd_eye_btn = QPushButton()
        self.pwd_eye_btn.setIcon(QIcon(QPixmap("images/eye_close.png")))
        self.pwd_eye_btn.setIconSize(QSize(24, 24))
        self.pwd_eye_btn.setCheckable(True)
        self.pwd_eye_btn.setStyleSheet("""
                   QPushButton {
                       background-color: transparent;
                       border: none;
                       padding: 0 5px;
                   }
                   QPushButton:hover {
                       background-color: #f0f0f0;
                       border-radius: 3px;
                   }
               """)
        self.pwd_eye_btn.clicked.connect(self.toggle_password_visibility)

        pwd_layout.addWidget(pwd_label)
        pwd_layout.addWidget(self.pwd_edit)
        pwd_layout.addWidget(self.pwd_eye_btn)
        self.total_layout.addLayout(pwd_layout)
        self.total_layout.addSpacing(20)

        # 确认密码输入
        confirm_pwd_layout = QHBoxLayout()
        confirm_pwd_label = QLabel("确认密码:")
        confirm_pwd_label.setFont(QFont("微软雅黑", 12))
        self.confirm_pwd_edit = QLineEdit()
        self.confirm_pwd_edit.setEchoMode(QLineEdit.Password)

        # 添加确认密码可见性切换按钮
        self.confirm_eye_btn = QPushButton()
        self.confirm_eye_btn.setIcon(QIcon(QPixmap("images/eye_close.png")))
        self.confirm_eye_btn.setIconSize(QSize(24, 24))
        self.confirm_eye_btn.setCheckable(True)
        self.confirm_eye_btn.setStyleSheet("""
                   QPushButton {
                       background-color: transparent;
                       border: none;
                       padding: 0 5px;
                   }
                   QPushButton:hover {
                       background-color: #f0f0f0;
                       border-radius: 3px;
                   }
               """)
        self.confirm_eye_btn.clicked.connect(self.toggle_confirm_password_visibility)

        confirm_pwd_layout.addWidget(confirm_pwd_label)
        confirm_pwd_layout.addWidget(self.confirm_pwd_edit)
        confirm_pwd_layout.addWidget(self.confirm_eye_btn)
        self.total_layout.addLayout(confirm_pwd_layout)
        self.total_layout.addSpacing(20)

        # 验证码输入
        captcha_layout = QHBoxLayout()
        captcha_label = QLabel("验证码:")
        captcha_label.setFont(QFont("微软雅黑", 12))
        self.captcha_edit = QLineEdit()
        captcha_layout.addWidget(captcha_label)
        captcha_layout.addWidget(self.captcha_edit)
        captcha_layout.addWidget(self.registration_code)
        self.total_layout.addLayout(captcha_layout)
        self.total_layout.addSpacing(40)

        # 按钮布局
        btn_layout = QHBoxLayout()
        self.register_btn = QPushButton("注册")
        self.back_btn = QPushButton("返回登录")
        self.quit_btn = QPushButton("退出")
        btn_layout.addWidget(self.register_btn)
        btn_layout.addWidget(self.back_btn)
        btn_layout.addWidget(self.quit_btn)
        self.total_layout.addLayout(btn_layout)

        # 信号连接
        self.register_btn.clicked.connect(self.handle_register)
        self.back_btn.clicked.connect(self.back_to_login)
        self.quit_btn.clicked.connect(self.close)
        self.registration_code.mousePressEvent = self.refresh_captcha

    def refresh_captcha(self, event):
        """刷新验证码"""
        self.registration_code.ui_init()
        event.accept()

    def toggle_password_visibility(self):
        """切换密码可见性"""
        if self.pwd_eye_btn.isChecked():
            self.pwd_edit.setEchoMode(QLineEdit.Normal)
            self.pwd_eye_btn.setIcon(QIcon(QPixmap("images/eye_open.png")))
        else:
            self.pwd_edit.setEchoMode(QLineEdit.Password)
            self.pwd_eye_btn.setIcon(QIcon(QPixmap("images/eye_close.png")))

    def toggle_confirm_password_visibility(self):
        """切换确认密码可见性"""
        if self.confirm_eye_btn.isChecked():
            self.confirm_pwd_edit.setEchoMode(QLineEdit.Normal)
            self.confirm_eye_btn.setIcon(QIcon(QPixmap("images/eye_open.png")))
        else:
            self.confirm_pwd_edit.setEchoMode(QLineEdit.Password)
            self.confirm_eye_btn.setIcon(QIcon(QPixmap("images/eye_close.png")))

    def handle_register(self):
        """处理注册逻辑"""
        username = self.user_edit.text().strip()
        password = self.pwd_edit.text().strip()
        confirm_password = self.confirm_pwd_edit.text().strip()
        captcha = self.captcha_edit.text().strip().lower()
        reg_code = self.registration_code.text.lower()

        # 输入验证
        if not all([username, password, confirm_password, captcha]):
            QMessageBox.warning(self, "注册失败", "所有字段均不能为空")
            return
        if len(username) < 6 or len(username) > 10:
            QMessageBox.warning(self, "注册失败", "用户名需6-10位")
            return
        if len(password) < 6 or len(password) > 10:
            QMessageBox.warning(self, "注册失败", "密码需6-10位")
            return
        if password != confirm_password:
            QMessageBox.warning(self, "注册失败", "密码不一致")
            return
        if captcha != reg_code:
            QMessageBox.warning(self, "注册失败", "验证码错误，请重新输入")
            self.refresh_captcha(None)
            return

        # 检查用户名是否存在
        if self.check_username_availability(username):
            # 用户名可用，继续注册
            if self.db_manager.add_user(username, password):
                QMessageBox.information(self, "注册成功", "注册成功，请登录")
                self.back_to_login()
            else:
                QMessageBox.critical(self, "注册失败", "数据库操作失败，请稍后重试")
        # 否则 check_username_availability 已经显示了错误弹窗

    def check_username_availability(self, username):
        """检查用户名是否可用，并在不可用时显示警告"""
        if self.db_manager.check_username_exists(username):
            QMessageBox.warning(self, "注册失败", "该用户名已存在")
            self.user_edit.setFocus()  # 将焦点放回用户名输入框
            return False
        return True

    def back_to_login(self):
        """返回登录界面"""
        self.back_to_login_signal.emit()
        self.hide()

    def closeEvent(self, event):
        """关闭窗口时清理资源"""
        self.db_manager = None
        super().closeEvent(event)