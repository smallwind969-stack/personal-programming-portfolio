# -*- coding: utf-8 -*-
import random
import time
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *


class GameWidget(QWidget):
    show_signal = pyqtSignal()
    show_profile_signal = pyqtSignal(str)  # 传递当前用户名到个人中心
    back_to_choose_signal = pyqtSignal()  # 新增：返回关卡选择界面的信号

    def __init__(self, username, level=1, width=1000, height=700):
        super().__init__()
        self.username = username  # 接收当前登录用户名
        # 验证关卡有效性
        if not (1 <= level <= 6):
            raise ValueError("关卡号必须在1-6之间")
        self.level = level  # 当前关卡号
        self.w = width
        self.h = height

        # 计时器相关初始化
        self.elapsed_time = 0
        self.start_time = 0
        self.is_running = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)

        # 记录当前局的初始状态（用于复盘）
        self.current_game_initial_list = []  # 拼图初始顺序
        self.current_initial_empty_pos = (0, 0)  # 初始空白块位置

        self.current_empty_pos = (0, 0)  # 当前空白块位置
        self.labs = []
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.init_win()

        # 初始化主布局
        self.totalLayout = QHBoxLayout()
        self.setLayout(self.totalLayout)

        # 检查图片资源是否存在（若缺失则退出初始化）
        if not self.check_image_resources():
            self.close()
            return

        # 初始化第一局游戏
        self.new_game()  # 新对局（相当于移形换影的效果）

        # 绑定按钮事件：将原"退出"按钮改为"返回关卡选择"
        self.restartBtn.clicked.connect(self.restart_current_game)  # 复盘当前局
        self.moveBtn.clicked.connect(self.new_game)  # 新对局
        self.profileBtn.clicked.connect(self.show_profile)
        self.exitBtn.clicked.connect(self.back_to_choose)  # 改为返回关卡选择
        self.infoBtn.clicked.connect(self.show_game_info)

    def init_win(self):
        self.setWindowTitle('拼图游戏')
        self.resize(self.w, self.h)
        # 居中显示窗口
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

        try:
            self.setWindowIcon(QIcon("images/icon.png"))
        except Exception as e:
            print(f"图标加载失败: {e}")
            self.setWindowIcon(QIcon())

    def check_image_resources(self):
        """检查当前关卡的图片资源是否存在，返回是否通过检查"""
        required_files = [f"./images/img{self.level}/{i}.png" for i in range(1, 9)]
        missing = []
        for file in required_files:
            if QPixmap(file).isNull():
                missing.append(file)
        if missing:
            QMessageBox.warning(
                self,
                "资源缺失",
                f"缺少以下图片资源，请检查：\n{chr(10).join(missing)}",
                QMessageBox.Ok
            )
            return False
        return True

    def init_window_item(self, puzzle_order, empty_pos):
        """初始化界面元素，根据指定的拼图顺序和空白块位置"""
        # 清理现有布局
        while self.totalLayout.count():
            item = self.totalLayout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.hide()
                widget.deleteLater()
            else:
                layout = item.layout()
                if layout:
                    while layout.count():
                        sub_item = layout.takeAt(0)
                        sub_widget = sub_item.widget()
                        if sub_widget:
                            sub_widget.hide()
                            sub_widget.deleteLater()

        # 重新创建分栏布局
        self.left = QGridLayout()
        self.right = QVBoxLayout()
        self.totalLayout.addLayout(self.left, 7)
        self.totalLayout.addLayout(self.right, 3)

        # 记录当前局初始状态
        self.current_game_initial_list = puzzle_order.copy()
        self.current_initial_empty_pos = empty_pos
        self.current_empty_pos = empty_pos
        self.random_list = puzzle_order.copy()

        # 创建拼图标签
        self.labs.clear()
        for i in range(3):
            for j in range(3):
                idx = i * 3 + j
                gpm = QLabel(self)
                try:
                    # 加载对应关卡的图片
                    img_path = f'./images/img{self.level}/{self.random_list[idx]}.png'
                    pixmap = QPixmap(img_path)
                    if pixmap.isNull():
                        raise Exception(f"图片文件无效或损坏")
                    gpm.setPixmap(pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                except Exception as e:
                    gpm.setText(str(self.random_list[idx]))
                    gpm.setStyleSheet("font-size: 24px; font-weight: bold;")
                    print(f"图片加载失败 {img_path}: {e}")
                gpm.setAlignment(Qt.AlignCenter)
                gpm.setFixedSize(200, 200)
                gpm.setStyleSheet("border: 1px solid #ccc;")
                gpm.initial_index = idx
                self.labs.append(gpm)
                self.left.addWidget(gpm, i, j)

        # 隐藏空白块（值为9的块作为空白）
        empty_idx = empty_pos[0] * 3 + empty_pos[1]
        self.labs[empty_idx].hide()

        # 计时器显示
        self.timer_label = QLabel("用时: 00:00", self)
        self.timer_label.setAlignment(Qt.AlignCenter)
        self.timer_label.setFont(QFont("微软雅黑", 14))
        self.timer_label.setStyleSheet("color: #ff4500;")

        # 右侧按钮：将"退出"按钮文本改为"返回关卡选择"
        self.moveBtn = QPushButton('移形换影', self)
        self.restartBtn = QPushButton('重新开始', self)
        self.infoBtn = QPushButton('游戏说明', self)
        self.profileBtn = QPushButton('个人中心', self)
        self.exitBtn = QPushButton('返回关卡选择', self)  # 修改按钮文本

        # 绑定按钮事件：确保"返回关卡选择"按钮关联正确方法
        self.moveBtn.clicked.connect(self.new_game)
        self.restartBtn.clicked.connect(self.restart_current_game)
        self.infoBtn.clicked.connect(self.show_game_info)
        self.profileBtn.clicked.connect(self.show_profile)
        self.exitBtn.clicked.connect(self.back_to_choose)

        # 设置按钮样式和大小
        btn_style = """
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """
        for btn in [self.moveBtn, self.restartBtn, self.infoBtn, self.profileBtn, self.exitBtn]:
            btn.setFixedHeight(40)
            btn.setFont(QFont("微软雅黑", 12))
            btn.setStyleSheet(btn_style)

        # 添加右侧组件
        self.right.addWidget(self.timer_label)
        self.right.addSpacing(20)
        self.right.addWidget(self.moveBtn)
        self.right.addWidget(self.restartBtn)
        self.right.addWidget(self.infoBtn)
        self.right.addWidget(self.profileBtn)
        self.right.addWidget(self.exitBtn)
        self.right.addStretch()
        self.right.setContentsMargins(50, 50, 50, 50)

    def new_game(self):
        """创建新对局：生成新的拼图顺序和空白块位置"""
        # 生成可解的新拼图
        puzzle_order = list(range(1, 10))
        while True:
            random.shuffle(puzzle_order)
            inversions = self.count_inversions(puzzle_order)
            if inversions % 2 == 0:
                break

        # 找到空白块位置
        empty_idx = puzzle_order.index(9)
        empty_pos = (empty_idx // 3, empty_idx % 3)

        # 初始化界面并开始计时
        self.init_window_item(puzzle_order, empty_pos)
        self.elapsed_time = 0
        self.start_timer()

    def restart_current_game(self):
        """重新开始当前局：恢复到本局初始状态"""
        # 使用当前局的初始状态重新初始化界面
        self.init_window_item(self.current_game_initial_list, self.current_initial_empty_pos)
        # 重置计时器
        self.elapsed_time = 0
        self.start_timer()

    def count_inversions(self, puzzle_order):
        """计算逆序数（用于确保拼图可解）"""
        inversions = 0
        # 排除空白块(9)计算逆序数
        nums = [num for num in puzzle_order if num != 9]
        for i in range(len(nums)):
            for j in range(i + 1, len(nums)):
                if nums[i] > nums[j]:
                    inversions += 1
        return inversions

    def start_timer(self):
        """启动计时器"""
        self.start_time = time.time() - self.elapsed_time
        self.timer.start(1000)
        self.is_running = True

    def stop_timer(self):
        """停止计时器"""
        self.timer.stop()
        self.is_running = False

    def update_timer(self):
        """更新计时器显示"""
        self.elapsed_time = time.time() - self.start_time
        minutes = int(self.elapsed_time // 60)
        seconds = int(self.elapsed_time % 60)
        self.timer_label.setText(f"用时: {minutes:02d}:{seconds:02d}")

    def mousePressEvent(self, event):
        """处理鼠标点击事件，移动拼图"""
        if event.button() == Qt.LeftButton and self.is_running:
            # 获取当前空白块位置
            self.m, self.n = self.current_empty_pos

            # 计算点击位置所在的单元格
            pos = event.pos()
            for i in range(3):
                for j in range(3):
                    # 安全获取布局中的部件
                    item = self.left.itemAtPosition(i, j)
                    if not item:
                        continue
                    widget = item.widget()
                    if widget and widget.geometry().contains(pos):
                        # 检查是否可以移动（相邻位置）
                        if (i == self.m and abs(j - self.n) == 1) or (j == self.n and abs(i - self.m) == 1):
                            click_idx = i * 3 + j
                            empty_idx = self.m * 3 + self.n

                            # 交换拼图
                            self.labs[empty_idx].setPixmap(self.labs[click_idx].pixmap())
                            self.labs[empty_idx].show()
                            self.labs[click_idx].hide()

                            # 更新数据
                            self.random_list[empty_idx], self.random_list[click_idx] = \
                                self.random_list[click_idx], self.random_list[empty_idx]
                            self.current_empty_pos = (i, j)  # 更新空白块位置记录

                            # 检查是否完成拼图
                            if self.random_list == list(range(1, 10)):
                                self.stop_timer()
                                QMessageBox.information(
                                    self,
                                    "恭喜",
                                    f"恭喜您完成了拼图！用时: {self.timer_label.text().split(': ')[1]}",
                                    QMessageBox.Ok
                                )
                                self.save_record()
                        return

    def save_record(self):
        """保存通关记录到users.txt"""
        try:
            with open('users.txt', 'r') as f:
                lines = f.readlines()

            updated = False
            with open('users.txt', 'w') as f:
                for line in lines:
                    if line.startswith(f"{self.username}:"):
                        parts = line.strip().split(':')
                        if len(parts) < 2:
                            f.write(line)
                            continue
                        password = parts[1]
                        records_parts = parts[2:] if len(parts) > 2 else []

                        # 添加/更新当前关卡记录
                        current_time = self.timer_label.text().split(': ')[1]
                        new_record = f"{self.level}:{current_time}"
                        found = False
                        for i in range(len(records_parts)):
                            if records_parts[i].startswith(f'{self.level}:'):
                                # 只保留更优记录（时间更短）
                                existing_time = records_parts[i].split(':')[1]
                                if self.time_to_seconds(current_time) < self.time_to_seconds(existing_time):
                                    records_parts[i] = new_record
                                found = True
                                break
                        if not found:
                            records_parts.append(new_record)

                        f.write(f"{self.username}:{password}:{':'.join(records_parts)}\n")
                        updated = True
                    else:
                        f.write(line)

            # 处理新用户（首次通关）
            if not updated:
                password = self.get_password()
                with open('users.txt', 'a') as f:
                    f.write(f"{self.username}:{password}:{self.level}:{self.timer_label.text().split(': ')[1]}\n")

        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存记录失败: {str(e)}")

    def time_to_seconds(self, time_str):
        """将时间字符串转换为秒数（用于比较记录）"""
        minutes, seconds = map(int, time_str.split(':'))
        return minutes * 60 + seconds

    def get_password(self):
        """获取当前用户密码"""
        try:
            with open('users.txt', 'r') as f:
                for line in f:
                    if line.startswith(f"{self.username}:"):
                        return line.strip().split(':')[1]
        except Exception as e:
            print(f"获取密码失败: {e}")
            return ""

    def show_profile(self):
        """发送信号显示个人中心"""
        self.show_profile_signal.emit(self.username)
        self.hide()  # 隐藏游戏窗口

    def back_to_choose(self):
        """新增：返回关卡选择界面的逻辑"""
        # 停止计时器
        if self.is_running:
            self.stop_timer()
        # 确认是否返回
        reply = QMessageBox.question(
            self, "确认返回", "确定要返回关卡选择界面吗？当前进度不会保存",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.hide()  # 隐藏游戏窗口
            self.back_to_choose_signal.emit()  # 发送信号通知主程序显示关卡选择

    def show_game_info(self):
        """更新游戏说明，补充返回按钮功能说明"""
        info = """
        拼图游戏规则：
        1. 点击空白块相邻的拼图块进行移动
        2. 将所有拼图块按1-8的顺序排列完成游戏
        3. "重新开始"按钮：复盘当前对局（恢复初始状态）
        4. "移形换影"按钮：进入全新对局（重新打乱拼图）
        5. "返回关卡选择"按钮：回到关卡列表，当前进度不保存
        6. 完成后会自动记录您的最佳成绩
        """
        QMessageBox.information(self, "游戏说明", info, QMessageBox.Ok)

    def closeEvent(self, event):
        """保留窗口关闭确认（若用户通过窗口右上角关闭按钮操作）"""
        reply = QMessageBox.question(
            self, "确认退出", "确定要退出游戏吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()