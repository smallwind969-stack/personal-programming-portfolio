# -*- coding: utf-8 -*-
# @Time    : 2025/9/18 23:53
# @Author  : 小宇
# @File    : profileWidget.py
# -*- coding: utf-8 -*-
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from tools import get_input_validator


class ProfileWidget(QWidget):
    back_signal = pyqtSignal()  # 返回游戏信号

    def __init__(self, width=600, height=500):
        super().__init__()
        self.username = ""
        self.w = width
        self.h = height
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("个人中心")
        self.resize(self.w, self.h)
        self.setWindowIcon(QIcon("images/icon.png"))

        # 主布局
        main_layout = QVBoxLayout(self)

        # 标题
        title_label = QLabel("个人信息")
        title_font = QFont("微软雅黑", 18, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        main_layout.addSpacing(20)

        # 用户名显示
        self.user_label = QLabel()
        self.user_label.setAlignment(Qt.AlignCenter)
        self.user_label.setFont(QFont("微软雅黑", 14))
        main_layout.addWidget(self.user_label)
        main_layout.addSpacing(20)

        # 密码修改区域
        pwd_group = QGroupBox("修改密码")
        pwd_layout = QFormLayout()

        self.old_pwd_edit = QLineEdit()
        self.old_pwd_edit.setEchoMode(QLineEdit.Password)
        self.old_pwd_edit.setValidator(get_input_validator())

        self.new_pwd_edit = QLineEdit()
        self.new_pwd_edit.setEchoMode(QLineEdit.Password)
        self.new_pwd_edit.setValidator(get_input_validator())

        self.confirm_pwd_edit = QLineEdit()
        self.confirm_pwd_edit.setEchoMode(QLineEdit.Password)
        self.confirm_pwd_edit.setValidator(get_input_validator())

        pwd_layout.addRow("旧密码:", self.old_pwd_edit)
        pwd_layout.addRow("新密码:", self.new_pwd_edit)
        pwd_layout.addRow("确认新密码:", self.confirm_pwd_edit)

        self.change_pwd_btn = QPushButton("修改密码")
        self.change_pwd_btn.clicked.connect(self.change_password)
        pwd_layout.addRow(self.change_pwd_btn)

        pwd_group.setLayout(pwd_layout)
        main_layout.addWidget(pwd_group)
        main_layout.addSpacing(20)

        # 通关记录区域
        record_group = QGroupBox("通关记录")
        record_layout = QVBoxLayout()

        self.record_list = QListWidget()
        record_layout.addWidget(self.record_list)

        record_group.setLayout(record_layout)
        main_layout.addWidget(record_group)

        # 底部按钮
        btn_layout = QHBoxLayout()
        self.back_btn = QPushButton("返回游戏")
        self.back_btn.clicked.connect(self.back_signal.emit)
        btn_layout.addWidget(self.back_btn)
        main_layout.addLayout(btn_layout)

    def set_user(self, username):
        """设置当前用户"""
        self.username = username
        self.user_label.setText(f"当前用户: {username}")

    def load_records(self):
        """加载用户通关记录"""
        self.record_list.clear()
        try:
            with open('users.txt', 'r') as f:
                for line in f:
                    if line.startswith(f"{self.username}:"):
                        parts = line.strip().split(':')
                        if len(parts) < 3:
                            self.record_list.addItem("暂无通关记录")
                            return
                        # 解析记录（格式: 关卡号:时间）
                        records = parts[2:]
                        for record in records:
                            if ':' in record:
                                level, time = record.split(':')
                                self.record_list.addItem(f"关卡{level}: 用时 {time}")
                        return
            self.record_list.addItem("暂无通关记录")
        except Exception as e:
            self.record_list.addItem(f"加载记录失败: {str(e)}")

    def change_password(self):
        """修改密码逻辑"""
        old_pwd = self.old_pwd_edit.text().strip()
        new_pwd = self.new_pwd_edit.text().strip()
        confirm_pwd = self.confirm_pwd_edit.text().strip()

        if not all([old_pwd, new_pwd, confirm_pwd]):
            QMessageBox.warning(self, "错误", "密码不能为空")
            return

        if new_pwd != confirm_pwd:
            QMessageBox.warning(self, "错误", "两次输入的新密码不一致")
            return

        try:
            with open('users.txt', 'r') as f:
                lines = f.readlines()

            # 查找并更新密码
            updated = False
            with open('users.txt', 'w') as f:
                for line in lines:
                    if line.startswith(f"{self.username}:"):
                        parts = line.strip().split(':')
                        if parts[1] != old_pwd:
                            QMessageBox.warning(self, "错误", "旧密码不正确")
                            f.writelines(lines)  # 写回原内容
                            return
                        # 保留记录部分，只更新密码
                        if len(parts) > 2:
                            f.write(f"{self.username}:{new_pwd}:{':'.join(parts[2:])}\n")
                        else:
                            f.write(f"{self.username}:{new_pwd}\n")
                        updated = True
                    else:
                        f.write(line)

            if updated:
                QMessageBox.information(self, "成功", "密码修改成功")
                self.old_pwd_edit.clear()
                self.new_pwd_edit.clear()
                self.confirm_pwd_edit.clear()
            else:
                QMessageBox.warning(self, "错误", "用户不存在")

        except Exception as e:
            QMessageBox.warning(self, "错误", f"修改密码失败: {str(e)}")