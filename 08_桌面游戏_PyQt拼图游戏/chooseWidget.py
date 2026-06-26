# -*- coding: utf-8 -*-
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *


class ChooseWidget(QWidget):
    # 定义信号，用于传递关卡号给主程序
    level_chosen = pyqtSignal(int)

    def __init__(self, width=800, height=600):
        super().__init__()
        self.w = width
        self.h = height
        self.setWindowTitle("选择关卡")
        self.resize(self.w, self.h)
        # 图标加载增加异常处理
        try:
            self.setWindowIcon(QIcon("images/icon.png"))
        except Exception as e:
            print(f"图标加载失败: {e}")
            self.setWindowIcon(QIcon())

        self.init_ui()

    def init_ui(self):
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignCenter)

        # 标题
        title_label = QLabel("选择关卡")
        title_font = QFont("微软雅黑", 24, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        main_layout.addSpacing(30)

        # 关卡按钮布局
        grid_layout = QGridLayout()
        grid_layout.setSpacing(20)

        # 创建关卡按钮（支持1-6关）
        for i in range(1, 7):
            btn = QPushButton(str(i))
            btn.setFixedSize(80, 80)
            btn.setFont(QFont("微软雅黑", 16))
            # 绑定带参数的点击事件（确保关卡号正确传递）
            btn.clicked.connect(lambda checked, x=i: self.on_level_click(x))
            grid_layout.addWidget(btn, (i - 1) // 3, (i - 1) % 3)

        main_layout.addLayout(grid_layout)
        main_layout.addSpacing(40)

        # 返回按钮
        back_btn = QPushButton("返回")
        back_btn.setFixedSize(120, 40)
        back_btn.clicked.connect(self.close)
        main_layout.addWidget(back_btn, alignment=Qt.AlignCenter)

    def on_level_click(self, level):
        """处理关卡选择，发送信号打开对应游戏界面"""
        if 1 <= level <= 6:  # 验证关卡范围
            # 发送信号前确保窗口已隐藏，避免界面闪烁
            self.hide()
            self.level_chosen.emit(level)
        else:
            QMessageBox.warning(self, "错误", "无效的关卡号")