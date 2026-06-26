# -*- coding: utf-8 -*-
# @Time    : 2025/6/26 10:54
# @Author  : 小宇
# @File    : home_page.py
import hashlib

import cv2
import os
import time
from datetime import datetime
import mysql.connector
import numpy as np
from mysql.connector import Error
from mysql.connector.pooling import MySQLConnectionPool
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QSpacerItem, QSizePolicy, QMessageBox,
                             QListWidget, QListWidgetItem, QFrame, QGridLayout,
                             QScrollArea, QDialog, QStackedWidget, QInputDialog, QLineEdit, QFileDialog)
from PyQt5.QtCore import Qt, QSize, QTimer, pyqtSignal, QUrl, QPointF, QThread
from PyQt5.QtGui import QPixmap, QIcon, QFont, QImage, QPainter, QPen, QTransform, QPainterPath, QColor

from driving_detect import driving_detect

from vehicle_detector import VehicleDetector


# ====================== 工具类 ======================
class DBConnector:
    """数据库连接池管理"""

    def __init__(self, config):
        self.pool = MySQLConnectionPool(pool_name="vid_pool", pool_size=3, **config)

    def execute_query(self, sql, params=None):
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            if sql.lower().startswith("select"):
                result = cursor.fetchall()
            else:
                conn.commit()
                result = cursor.rowcount
            return result
        except Error as e:
            print(f"数据库操作失败: {e}")
            return []
        finally:
            conn.close()


def get_video_thumbnail(video_path, size=(180, 100)):
    """获取视频缩略图"""
    try:
        cap = cv2.VideoCapture(video_path)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                frame = cv2.resize(frame, size)
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = frame_rgb.shape
                return QImage(frame_rgb.data, w, h, ch * w, QImage.Format_RGB888)
            cap.release()
    except Exception as e:
        print(f"加载缩略图失败: {e}")
    return None


def get_current_time():
    """获取当前格式化时间"""
    return datetime.now().strftime("%Y.%m.%d %H:%M:%S")


def get_icon(icon_path, size=QSize(40, 40)):
    """获取并处理图标"""
    pixmap = QPixmap(icon_path)
    return QIcon(pixmap.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation))


# ====================== 新增图片相关UI组件 ======================
class PhotoItemWidget(QFrame):
    """图片列表项组件"""
    view_signal = pyqtSignal(str)
    delete_signal = pyqtSignal(str)


    def __init__(self, photo_path, create_time, parent=None):
        super().__init__(parent)
        self.photo_path = photo_path
        self.create_time = create_time.strftime("%Y-%m-%d %H:%M:%S") if isinstance(create_time, datetime) else str(
            create_time)
        self.init_ui()


    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)

        # 图片缩略图
        self.photo_label = QLabel()
        self.photo_label.setFixedSize(180, 180)
        self.photo_label.setStyleSheet("border: 1px solid #555; border-radius: 5px;")
        self.photo_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.photo_label)

        # 时间标签
        time_label = QLabel(self.create_time)
        time_label.setStyleSheet("color: white; font-size: 12px;")
        time_label.setAlignment(Qt.AlignLeft)
        main_layout.addWidget(time_label)

        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(5)

        view_btn = QPushButton("查看")
        view_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3498db; color: white; 
                    border: none; border-radius: 3px; 
                    padding: 5px 10px; font-size: 11px;
                }
                QPushButton:hover { background-color: #2980b9; }
            """)
        view_btn.clicked.connect(lambda: self.view_signal.emit(self.photo_path))
        btn_layout.addWidget(view_btn)

        delete_btn = QPushButton("删除")
        delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c; color: white; 
                    border: none; border-radius: 3px; 
                    padding: 5px 10px; font-size: 11px;
                }
                QPushButton:hover { background-color: #c0392b; }
            """)
        delete_btn.clicked.connect(lambda: self.delete_signal.emit(self.photo_path))
        btn_layout.addWidget(delete_btn)

        main_layout.addLayout(btn_layout)
        self.load_photo_thumbnail()


    def load_photo_thumbnail(self):
        """加载图片缩略图"""
        if os.path.exists(self.photo_path):
            pixmap = QPixmap(self.photo_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    self.photo_label.width(),
                    self.photo_label.height(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.photo_label.setPixmap(scaled_pixmap)
            else:
                self.photo_label.setText("无法加载")
        else:
            self.photo_label.setText("文件不存在")


class PhotoViewerDialog(QDialog):
    """图片查看器对话框，支持旋转和缩放"""

    def __init__(self, photo_path, parent=None):
        super().__init__(parent)
        self.photo_path = photo_path
        self.rotation = 0  # 旋转角度
        self.scale_factor = 1.0  # 缩放因子
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("图片查看器")
        self.setMinimumSize(800, 600)

        # 主布局
        main_layout = QVBoxLayout(self)

        # 图片显示区域
        self.photo_label = QLabel()
        self.photo_label.setAlignment(Qt.AlignCenter)
        self.photo_label.setStyleSheet("background-color: #f0f0f0;")
        main_layout.addWidget(self.photo_label)

        # 控制按钮布局
        control_layout = QHBoxLayout()

        # 旋转按钮
        rotate_left_btn = QPushButton("向左旋转")
        rotate_left_btn.clicked.connect(self.rotate_left)
        rotate_right_btn = QPushButton("向右旋转")
        rotate_right_btn.clicked.connect(self.rotate_right)

        # 缩放按钮
        zoom_in_btn = QPushButton("放大")
        zoom_in_btn.clicked.connect(self.zoom_in)
        zoom_out_btn = QPushButton("缩小")
        zoom_out_btn.clicked.connect(self.zoom_out)
        reset_btn = QPushButton("重置")
        reset_btn.clicked.connect(self.reset_view)

        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)

        # 添加按钮到布局
        control_layout.addWidget(rotate_left_btn)
        control_layout.addWidget(rotate_right_btn)
        control_layout.addSpacing(20)
        control_layout.addWidget(zoom_in_btn)
        control_layout.addWidget(zoom_out_btn)
        control_layout.addWidget(reset_btn)
        control_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        control_layout.addWidget(close_btn)

        main_layout.addLayout(control_layout)

        # 加载图片
        self.load_photo()

    def load_photo(self):
        """加载原始图片"""
        if os.path.exists(self.photo_path):
            self.original_pixmap = QPixmap(self.photo_path)
            if not self.original_pixmap.isNull():
                self.update_photo_display()
            else:
                self.photo_label.setText("无法加载图片")
        else:
            self.photo_label.setText("图片文件不存在")

    def update_photo_display(self):
        """更新图片显示（应用旋转和缩放）"""
        if not hasattr(self, 'original_pixmap'):
            return

        # 应用旋转
        transformed = self.original_pixmap.transformed(QTransform().rotate(self.rotation))

        # 应用缩放
        scaled = transformed.scaled(
            transformed.width() * self.scale_factor,
            transformed.height() * self.scale_factor,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.photo_label.setPixmap(scaled)

    def rotate_left(self):
        """向左旋转90度"""
        self.rotation -= 90
        self.update_photo_display()

    def rotate_right(self):
        """向右旋转90度"""
        self.rotation += 90
        self.update_photo_display()

    def zoom_in(self):
        """放大图片（10%步长）"""
        self.scale_factor *= 1.1
        self.update_photo_display()

    def zoom_out(self):
        """缩小图片（10%步长）"""
        self.scale_factor *= 0.9
        self.update_photo_display()

    def reset_view(self):
        """重置视图到原始状态"""
        self.rotation = 0
        self.scale_factor = 1.0
        self.update_photo_display()


class PhotoListPage(QWidget):
    """图片列表页面"""
    switch_to_page = pyqtSignal(str)
    refresh_list = pyqtSignal()  # 用于接收外部刷新通知

    def __init__(self, db_connector, photo_dir, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.photo_dir = photo_dir
        self.photos = []
        self.init_ui()
        self.load_photos_from_db()
        self.refresh_list.connect(self.load_photos_from_db)

    def init_ui(self):
        self.setStyleSheet("background-color: #1a1a1a;")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # 标题栏
        title_layout = QHBoxLayout()
        title_label = QLabel("图片列表")
        title_label.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        back_btn = QPushButton("返回")
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db; color: white; 
                border: none; border-radius: 5px; 
                padding: 8px 15px; font-size: 14px;
            }
            QPushButton:hover { background-color: #2980b9; }
        """)
        back_btn.clicked.connect(lambda: self.switch_to_page.emit("home"))
        title_layout.addWidget(title_label)
        title_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        title_layout.addWidget(back_btn)
        main_layout.addLayout(title_layout)

        # 图片列表区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("background-color: #252525; border-radius: 5px;")
        self.list_widget = QWidget()
        self.list_layout = QGridLayout(self.list_widget)
        self.list_layout.setSpacing(20)
        self.list_layout.setContentsMargins(20, 20, 20, 20)
        scroll_area.setWidget(self.list_widget)
        main_layout.addWidget(scroll_area)

    def load_photos_from_db(self):
        """从数据库加载图片记录"""
        sql = "SELECT photo_path, create_time FROM photos ORDER BY create_time DESC"
        try:
            self.photos = self.db_connector.execute_query(sql)
            self.refresh_photo_list()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"获取图片列表失败: {e}")

    def refresh_photo_list(self):
        """刷新图片列表显示"""
        # 清空现有列表
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

        # 添加新的图片项
        column, row = 0, 0
        for photo_path, create_time in self.photos:
            if not os.path.exists(photo_path):
                continue  # 跳过不存在的图片文件

            photo_item = PhotoItemWidget(photo_path, create_time)
            photo_item.view_signal.connect(self.view_photo)
            photo_item.delete_signal.connect(self.delete_photo)

            self.list_layout.addWidget(photo_item, row, column)

            # 计算网格位置（每行显示3个图片）
            column += 1
            if column >= 3:
                column = 0
                row += 1

    def view_photo(self, photo_path):
        """查看图片"""
        dialog = PhotoViewerDialog(photo_path, self)
        dialog.exec_()

    def delete_photo(self, photo_path):
        """删除图片"""
        reply = QMessageBox.question(self, "确认", f"确定要删除图片 {os.path.basename(photo_path)} 吗？",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                # 从文件系统删除
                if os.path.exists(photo_path):
                    os.remove(photo_path)

                # 从数据库删除
                sql = "DELETE FROM photos WHERE photo_path = %s"
                self.db_connector.execute_query(sql, (photo_path,))

                # 刷新列表
                self.load_photos_from_db()
                QMessageBox.information(self, "成功", "图片已删除")

            except Exception as e:
                QMessageBox.warning(self, "错误", f"删除图片失败: {e}")
# ====================== UI组件 ======================
class VideoItemWidget(QFrame):
    """视频列表项组件"""
    play_signal = pyqtSignal(str)
    delete_signal = pyqtSignal(str)

    def __init__(self, video_path, create_time, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.create_time = create_time.strftime("%Y-%m-%d %H:%M:%S") if isinstance(create_time, datetime) else str(
            create_time)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)

        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(180, 100)
        self.thumbnail_label.setStyleSheet("border: 1px solid #555; border-radius: 5px;")
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.thumbnail_label)

        time_label = QLabel(self.create_time)
        time_label.setStyleSheet("color: white; font-size: 12px;")
        time_label.setAlignment(Qt.AlignLeft)
        main_layout.addWidget(time_label)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(5)

        play_btn = QPushButton("播放")
        play_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db; color: white; 
                border: none; border-radius: 3px; 
                padding: 5px 10px; font-size: 11px;
            }
            QPushButton:hover { background-color: #2980b9; }
        """)
        play_btn.clicked.connect(lambda: self.play_signal.emit(self.video_path))
        btn_layout.addWidget(play_btn)

        delete_btn = QPushButton("删除")
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c; color: white; 
                border: none; border-radius: 3px; 
                padding: 5px 10px; font-size: 11px;
            }
            QPushButton:hover { background-color: #c0392b; }
        """)
        delete_btn.clicked.connect(lambda: self.delete_signal.emit(self.video_path))
        btn_layout.addWidget(delete_btn)

        main_layout.addLayout(btn_layout)
        self.load_thumbnail()

    def load_thumbnail(self):
        """异步加载缩略图"""
        if os.path.exists(self.video_path):
            q_img = get_video_thumbnail(self.video_path)
            if q_img:
                self.thumbnail_label.setPixmap(QPixmap.fromImage(q_img))
            else:
                self.thumbnail_label.setText("无法加载")
        else:
            self.thumbnail_label.setText("文件不存在")


class VideoPlayerDialog(QDialog):
    """视频播放对话框（修复倍速播放速度问题）"""

    def __init__(self, video_path, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.is_playing = False
        self.play_timer = QTimer(self)
        self.play_timer.timeout.connect(self.update_frame)
        self.cap = None  # 视频捕获对象

        # 倍速控制（仅保留1,2,4倍）
        self.speeds = [1, 2, 4]
        self.current_speed = 1  # 当前倍速（默认1倍）
        self.video_fps = 1  # 视频实际帧率
        self.frame_step = 1  # 每步读取的帧数（1倍速读1帧，2倍速读2帧...）

        self.init_ui()
        self.get_video_info()  # 获取视频信息

    def get_video_info(self):
        """获取视频帧率和总时长"""
        if os.path.exists(self.video_path):
            temp_cap = cv2.VideoCapture(self.video_path)
            if temp_cap.isOpened():
                self.video_fps = temp_cap.get(cv2.CAP_PROP_FPS) or 10
                # 1倍速时的基础间隔（确保每秒播放fps帧）
                self.base_interval = int(4000 / self.video_fps)
                temp_cap.release()
                print(f"视频帧率: {self.video_fps}, 基础间隔: {self.base_interval}ms")

    def init_ui(self):
        self.setWindowTitle("视频播放")
        self.setMinimumSize(800, 500)

        main_layout = QVBoxLayout(self)
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: black;")
        main_layout.addWidget(self.video_label)

        # 控制布局
        control_layout = QHBoxLayout()

        # 倍速选择按钮
        speed_layout = QHBoxLayout()
        speed_label = QLabel("倍速: ")
        speed_label.setStyleSheet("color: #333;")
        speed_layout.addWidget(speed_label)

        self.speed_buttons = []
        for speed in self.speeds:
            btn = QPushButton(f"{speed}x")
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #f0f0f0; color: #333;
                    border: 1px solid #ccc; border-radius: 3px;
                    padding: 5px 10px;
                }
                QPushButton:checked {
                    background-color: #3498db; color: white;
                    border-color: #2980b9;
                }
            """)
            btn.setCheckable(True)
            if speed == 1:
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, s=speed: self.set_speed(s))
            self.speed_buttons.append(btn)
            speed_layout.addWidget(btn)

        control_layout.addLayout(speed_layout)
        control_layout.addSpacing(20)

        # 控制按钮
        self.play_btn = QPushButton("播放")
        self.play_btn.clicked.connect(self.toggle_play)
        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self.stop_play)
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.close)

        control_layout.addWidget(self.play_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addWidget(self.close_btn)
        control_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        main_layout.addLayout(control_layout)

    def set_speed(self, speed):
        """设置倍速（通过跳读帧实现）"""
        self.current_speed = speed
        # 更新按钮状态
        for btn in self.speed_buttons:
            btn.setChecked(int(btn.text().replace('x', '')) == speed)

        # 计算每步需要跳读的帧数
        self.frame_step = speed  # 1倍速读1帧，2倍速读2帧，4倍速读4帧

        # 正在播放时保持定时器间隔不变（确保每秒处理的帧数固定）
        if self.is_playing:
            self.play_timer.setInterval(self.base_interval)

    def toggle_play(self):
        if self.is_playing:
            self.play_timer.stop()
            self.play_btn.setText("播放")
        else:
            if not self.cap or not self.cap.isOpened():
                self.cap = cv2.VideoCapture(self.video_path)
            # 定时器间隔固定为基础间隔（确保每秒播放fps帧）
            self.play_timer.start(self.base_interval)
            self.play_btn.setText("暂停")
        self.is_playing = not self.is_playing

    def stop_play(self):
        self.play_timer.stop()
        self.play_btn.setText("播放")
        self.is_playing = False
        self.video_label.clear()
        if self.cap:
            self.cap.release()
            self.cap = None

    def update_frame(self):
        """通过跳读帧实现倍速播放"""
        if not self.cap or not self.cap.isOpened():
            return

        for _ in range(self.frame_step):
            ret, frame = self.cap.read()
            if not ret:  # 视频结束
                self.stop_play()
                return

        # 显示最后读取的一帧
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        q_img = QImage(frame_rgb.data, w, h, ch * w, QImage.Format_RGB888)
        self.video_label.setPixmap(
            QPixmap.fromImage(q_img).scaled(780, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

    def closeEvent(self, event):
        if self.cap is not None:
            self.cap.release()
        super().closeEvent(event)


# ====================== 页面 ======================
class PersonalInfoDialog(QDialog):
    """个人信息弹窗（优化密码显示和修改密码界面）"""
    def __init__(self, username, db_connector, parent=None):
        super().__init__(parent)
        self.username = username
        self.db_connector = db_connector
        self.headphoto_path = ""
        self.init_ui()
        self.load_user_info()

    def init_ui(self):
        self.setWindowTitle("个人信息")
        self.setStyleSheet("""
            QDialog {
                background-color: #f0f0f0; 
                border: 1px solid #ccc;
                border-radius: 8px;
            }
            QLabel {
                color: #333;
                font-size: 14px;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                margin: 5px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            /* 粉色显示框样式 */
            .info-label {
                background-color: #ffddee;  /* 浅粉色背景 */
                border: 1px solid #ffbbbb;  /* 粉色边框 */
                border-radius: 4px;
                padding: 6px 10px;
                color: #d8366f;  /* 深粉色文字 */
            }
        """)
        self.setFixedSize(350, 400)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 头像区域（保持不变）
        self.avatar_frame = QFrame()
        self.avatar_frame.setFixedSize(120, 160)
        self.avatar_frame.setStyleSheet("background-color: #f5f5f5; border-radius: 10px;")
        avatar_layout = QVBoxLayout(self.avatar_frame)
        avatar_layout.setAlignment(Qt.AlignCenter)
        avatar_layout.setSpacing(10)

        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(80, 80)
        self.avatar_label.setStyleSheet("border: 2px solid #3498db; border-radius: 40px;")
        self.avatar_label.setAlignment(Qt.AlignCenter)
        avatar_layout.addWidget(self.avatar_label, alignment=Qt.AlignCenter)

        self.change_avatar_btn = QPushButton("更换头像")
        self.change_avatar_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db; color: white;
                border: none; border-radius: 5px;
                padding: 6px 12px; font-size: 12px;
            }
            QPushButton:hover { background-color: #2980b9; }
        """)
        self.change_avatar_btn.clicked.connect(self.change_avatar)
        avatar_layout.addWidget(self.change_avatar_btn, alignment=Qt.AlignCenter)
        main_layout.addWidget(self.avatar_frame, alignment=Qt.AlignCenter)

        # 信息显示区域（统一粉色样式）
        self.info_layout = QVBoxLayout()
        # 定义统一的粉色样式（与编辑框保持一致）
        pink_style = """
              background-color: #ffddee;  /* 浅粉色背景 */
              border: 1px solid #ffbbbb;  /* 粉色边框 */
              border-radius: 6px;         /* 统一圆角 */
              padding: 8px 12px;          /* 统一内边距 */
              color: #d8366f;             /* 深粉色文字 */
              font-size: 15px;            /* 统一字体大小 */
          """

        # 用户ID显示框（粉色样式）
        self.userid_label = QLabel()
        self.userid_label.setStyleSheet(pink_style)  # 应用统一样式
        self.info_layout.addWidget(self.userid_label)

        # 用户名显示框（粉色样式）
        self.username_label = QLabel()
        self.username_label.setStyleSheet(pink_style)  # 应用统一样式
        self.info_layout.addWidget(self.username_label)

        # 密码显示框（粉色样式，使用输入框模拟标签）
        self.password_edit = QLineEdit()
        self.password_edit.setReadOnly(True)  # 只读模式，禁止编辑
        self.password_edit.setEchoMode(QLineEdit.Password)  # 密码圆点显示
        self.password_edit.setStyleSheet(pink_style)  # 应用统一样式
        self.info_layout.addWidget(self.password_edit)

        main_layout.addLayout(self.info_layout)

        # 操作按钮（增大按钮尺寸）
        self.btn_layout = QHBoxLayout()
        self.edit_name_btn = QPushButton("修改名称")
        self.edit_pwd_btn = QPushButton("修改密码")
        self.logout_btn = QPushButton("退出登录")

        # 统一增大按钮尺寸
        for btn in [self.edit_name_btn, self.edit_pwd_btn, self.logout_btn]:
            btn.setMinimumHeight(40)  # 增大按钮高度
            btn.setStyleSheet("""
                       QPushButton {
                           background-color: #3498db;
                           color: white;
                           border: none;
                           border-radius: 6px;  # 增大圆角
                           padding: 10px 15px;
                           font-size: 14px;    # 增大字体
                       }
                       QPushButton:hover {
                           background-color: #2980b9;
                       }
                   """)

        self.edit_name_btn.clicked.connect(self.edit_username)
        self.edit_pwd_btn.clicked.connect(self.edit_password)
        self.logout_btn.clicked.connect(self.logout)
        self.btn_layout.addWidget(self.edit_name_btn)
        self.btn_layout.addWidget(self.edit_pwd_btn)
        self.btn_layout.addWidget(self.logout_btn)
        main_layout.addLayout(self.btn_layout)

    def load_user_info(self):
        """加载用户信息（密码显示为圆点）"""
        sql = "SELECT userid, username, password, headphoto FROM users WHERE username = %s"
        result = self.db_connector.execute_query(sql, (self.username,))
        if result:
            userid, username, password, headphoto = result[0]
            self.headphoto_path = str(headphoto).strip().replace("\\", "/") if headphoto else ""

            # 显示处理：使用密码输入框显示为圆点
            self.userid_label.setText(f"用户ID：{userid}")
            self.username_label.setText(f"用户名：{username}")
            self.password_edit.setText("*" * len(password))  # 用相同长度的*填充

            self.update_avatar_display()

    def update_avatar_display(self):
        """头像显示逻辑（保持不变）"""
        if self.headphoto_path:
            if not os.path.isabs(self.headphoto_path):
                base_dir = os.path.dirname(os.path.abspath(__file__))
                self.headphoto_path = os.path.join(base_dir, self.headphoto_path)
            if os.path.exists(self.headphoto_path):
                self.set_rounded_avatar(self.headphoto_path)
                return

        default_avatar = os.path.join(os.path.dirname(os.path.abspath(__file__)), "avatars", "avatar_default.png")
        if os.path.exists(default_avatar):
            self.set_rounded_avatar(default_avatar)
        else:
            self.avatar_label.setText("无头像")
            self.avatar_label.setStyleSheet("""
                border: 2px solid #3498db; 
                border-radius: 40px;
                background-color: #e0e0e0;
                color: #333;
                font-size: 12px;
            """)

    def set_rounded_avatar(self, image_path):
        """圆形头像处理（保持不变）"""
        try:
            original_pixmap = QPixmap(image_path)
            if original_pixmap.isNull():
                raise Exception("无法加载图片")

            size = self.avatar_label.size()
            rounded_pixmap = QPixmap(size)
            rounded_pixmap.fill(Qt.transparent)

            painter = QPainter(rounded_pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)

            path = QPainterPath()
            path.addEllipse(0, 0, size.width(), size.height())
            painter.setClipPath(path)

            scaled_pixmap = original_pixmap.scaled(
                size, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            x = (size.width() - scaled_pixmap.width()) // 2
            y = (size.height() - scaled_pixmap.height()) // 2
            painter.drawPixmap(x, y, scaled_pixmap)

            painter.setPen(QPen(QColor(52, 152, 219), 2))
            painter.drawEllipse(1, 1, size.width() - 2, size.height() - 2)
            painter.end()

            self.avatar_label.setPixmap(rounded_pixmap)

        except Exception as e:
            print(f"设置头像失败: {e}")
            self.avatar_label.setText("加载失败")
            self.avatar_label.setStyleSheet("""
                border: 2px solid #e74c3c; 
                border-radius: 40px;
                background-color: #e0e0e0;
                color: #e74c3c;
                font-size: 12px;
            """)

    def change_avatar(self):
        """更换头像逻辑（保持不变）"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "选择头像", "",
                "图片文件 (*.png *.jpg *.jpeg *.bmp);;所有文件 (*)"
            )
            if not file_path:
                return

            test_pixmap = QPixmap(file_path)
            if test_pixmap.isNull():
                raise Exception("选择的文件不是有效的图片")

            avatar_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "avatars")
            os.makedirs(avatar_dir, exist_ok=True)

            user_id = self.userid_label.text().split("：")[-1]
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"avatar_{user_id}_{timestamp}.png"
            save_path = os.path.join(avatar_dir, filename)

            if not test_pixmap.save(save_path, "PNG"):
                raise Exception("保存图片失败")

            sql = "UPDATE users SET headphoto = %s WHERE username = %s"
            result = self.db_connector.execute_query(sql, (save_path, self.username))

            if result > 0:
                self.headphoto_path = save_path
                self.update_avatar_display()
                if hasattr(self.parent(), 'update_avatar'):
                    self.parent().update_avatar(save_path)
                QMessageBox.information(self, "成功", "头像更新成功")

                if self.headphoto_path and os.path.exists(
                        self.headphoto_path) and "avatar_default.png" not in self.headphoto_path:
                    try:
                        os.remove(self.headphoto_path)
                    except Exception as e:
                        print(f"删除旧头像失败: {e}")
            else:
                raise Exception("数据库更新失败")

        except Exception as e:
            QMessageBox.warning(self, "错误", f"更换头像失败：{str(e)}")

    def edit_username(self):
        """修改用户名（使用自定义对话框，统一粉色输入框样式）"""
        # 创建自定义对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("修改名称")
        dialog.setStyleSheet("background-color: #f0f0f0; border-radius: 8px;")
        dialog.setFixedSize(300, 200)  # 固定尺寸

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 标签
        label = QLabel("请输入新的用户名：")
        label.setFont(QFont("微软雅黑", 13))  # 统一字体大小

        # 粉色输入框
        self.new_name_input = QLineEdit()
        self.new_name_input.setMinimumHeight(40)  # 增大高度
        self.new_name_input.setStyleSheet("""
            background-color: #ffddee;  /* 浅粉色背景 */
            border: 1px solid #ffbbbb;  /* 粉色边框 */
            border-radius: 6px;         /* 圆角 */
            padding: 8px 12px;          /* 内边距 */
            color: #d8366f;             /* 深粉色文字 */
            font-size: 14px;            /* 字体大小 */
        """)

        # 按钮布局

        btn_layout = QHBoxLayout()
        confirm_btn = QPushButton("确认")
        cancel_btn = QPushButton("取消")
        for btn in [confirm_btn,cancel_btn]:
            btn.setMinimumHeight(60)
        # 按钮样式
        confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 15px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 15px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)

        confirm_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(confirm_btn)
        btn_layout.addWidget(cancel_btn)

        # 添加控件到布局
        layout.addWidget(label)
        layout.addWidget(self.new_name_input)
        layout.addLayout(btn_layout)

        # 显示对话框并处理结果
        if dialog.exec_() and self.new_name_input.text():
            new_name = self.new_name_input.text()
            sql = "UPDATE users SET username = %s WHERE username = %s"
            result = self.db_connector.execute_query(sql, (new_name, self.username))
            if result > 0:
                QMessageBox.information(self, "成功", "用户名修改成功")
                self.username = new_name
                self.load_user_info()
                if hasattr(self.parentWidget(), 'update_user_info'):
                    self.parentWidget().update_user_info(new_name)
            else:
                QMessageBox.warning(self, "失败", "用户名修改失败，请重试")

    def edit_password(self):
        """修改密码（统一粉色输入框样式）"""
        dialog = QDialog(self)
        dialog.setWindowTitle("修改密码")
        dialog.setStyleSheet("background-color: #f0f0f0; border-radius: 8px;")
        dialog.setFixedSize(350, 350)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 25, 20, 25)
        layout.setSpacing(18)

        # 原密码输入框（粉色样式）
        old_pwd_label = QLabel("原密码:")
        old_pwd_label.setFont(QFont("微软雅黑", 13))
        self.old_pwd_input = QLineEdit()
        self.old_pwd_input.setEchoMode(QLineEdit.Password)
        self.old_pwd_input.setMinimumHeight(40)
        self.old_pwd_input.setStyleSheet("""
            background-color: #ffddee;
            border: 1px solid #ffbbbb;
            border-radius: 6px;
            padding: 8px 12px;
            color: #d8366f;
            font-size: 14px;
        """)  # 与用户名输入框样式完全一致

        # 新密码输入框（粉色样式）
        new_pwd_label = QLabel("新密码:")
        new_pwd_label.setFont(QFont("微软雅黑", 13))
        self.new_pwd_input = QLineEdit()
        self.new_pwd_input.setEchoMode(QLineEdit.Password)
        self.new_pwd_input.setMinimumHeight(40)
        self.new_pwd_input.setStyleSheet("""
            background-color: #ffddee;
            border: 1px solid #ffbbbb;
            border-radius: 6px;
            padding: 8px 12px;
            color: #d8366f;
            font-size: 14px;
        """)  # 统一样式

        # 确认新密码输入框（粉色样式）
        confirm_label = QLabel("确认新密码:")
        confirm_label.setFont(QFont("微软雅黑", 13))
        self.confirm_pwd_input = QLineEdit()
        self.confirm_pwd_input.setEchoMode(QLineEdit.Password)
        self.confirm_pwd_input.setMinimumHeight(40)
        self.confirm_pwd_input.setStyleSheet("""
            background-color: #ffddee;
            border: 1px solid #ffbbbb;
            border-radius: 6px;
            padding: 8px 12px;
            color: #d8366f;
            font-size: 14px;
        """)  # 统一样式

        # 按钮布局（保持不变）
        btn_layout = QHBoxLayout()
        confirm_btn = QPushButton("确认修改")
        cancel_btn = QPushButton("取消")

        # 统一增大按钮尺寸
        for btn in [confirm_btn, cancel_btn]:
            btn.setMinimumHeight(45)  # 增大按钮高度
            btn.setStyleSheet("""
                   QPushButton {
                       color: white;
                       border: none;
                       border-radius: 6px;  # 增大圆角
                       padding: 10px 15px;
                       font-size: 15px;    # 增大字体
                   }
                   QPushButton:hover {
                       background-color: #2980b9;
                   }
               """)

        confirm_btn.setStyleSheet("""
               QPushButton {
                   background-color: #3498db;
                   color: white;
                   border: none;
                   border-radius: 6px;
                   padding: 10px 15px;
                   font-size: 15px;
               }
               QPushButton:hover {
                   background-color: #2980b9;
               }
           """)

        cancel_btn.setStyleSheet("""
               QPushButton {
                   background-color: #e74c3c;
                   color: white;
                   border: none;
                   border-radius: 6px;
                   padding: 10px 15px;
                   font-size: 15px;
               }
               QPushButton:hover {
                   background-color: #c0392b;
               }
           """)

        confirm_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)

        btn_layout.addWidget(confirm_btn)
        btn_layout.addWidget(cancel_btn)

        # 添加控件到布局
        layout.addWidget(old_pwd_label)
        layout.addWidget(self.old_pwd_input)
        layout.addWidget(new_pwd_label)
        layout.addWidget(self.new_pwd_input)
        layout.addWidget(confirm_label)
        layout.addWidget(self.confirm_pwd_input)
        layout.addLayout(btn_layout)

        # 显示对话框
        if dialog.exec_():
            old_pwd = self.old_pwd_input.text()
            new_pwd = self.new_pwd_input.text()
            confirm_pwd = self.confirm_pwd_input.text()

            # 验证原密码
            if not old_pwd:
                # 修改空输入警告弹窗样式
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setText("请输入原密码")
                msg_box.setWindowTitle("提示")
                msg_box.setStyleSheet("""
                    QMessageBox {
                        background-color: #333333;  /* 深灰背景 */
                        color: white;               /* 白色文本 */
                        font-size: 14px;
                    }
                    QMessageBox QLabel {
                        color: white;               /* 标签文本白色 */
                    }
                    QMessageBox QPushButton {
                        background-color: #555555;  /* 按钮背景 */
                        color: white;               /* 按钮文本白色 */
                        border: none;
                        padding: 5px 15px;
                        border-radius: 3px;
                    }
                    QMessageBox QPushButton:hover {
                        background-color: #777777;  /* 按钮悬停效果 */
                    }
                """)
                msg_box.exec_()
                return

            # 获取数据库中存储的加密密码
            sql = "SELECT password FROM users WHERE username = %s"
            result = self.db_connector.execute_query(sql, (self.username,))

            if not result:
                # 修改数据库错误弹窗样式
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setText("用户信息获取失败")
                msg_box.setWindowTitle("错误")
                msg_box.setStyleSheet("""
                    QMessageBox {
                        background-color: #333333;
                        color: white;
                        font-size: 14px;
                    }
                    QMessageBox QLabel {
                        color: white;
                    }
                    QMessageBox QPushButton {
                        background-color: #555555;
                        color: white;
                        border: none;
                        padding: 5px 15px;
                        border-radius: 3px;
                    }
                """)
                msg_box.exec_()
                return

            stored_pwd = result[0][0]

            # 验证原密码是否正确
            if self.encrypt_password(old_pwd) != stored_pwd:
                # 修改密码错误弹窗样式
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setText("原密码不正确")
                msg_box.setWindowTitle("验证失败")
                msg_box.setStyleSheet("""
                    QMessageBox {
                        background-color: #333333;
                        color: white;
                        font-size: 14px;
                    }
                    QMessageBox QLabel {
                        color: white;
                    }
                    QMessageBox QPushButton {
                        background-color: #555555;
                        color: white;
                        border: none;
                        padding: 5px 15px;
                        border-radius: 3px;
                    }
                """)
                msg_box.exec_()
                return

            # 验证新密码
            if not new_pwd:
                # 修改新密码空输入弹窗样式
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setText("新密码不能为空")
                msg_box.setWindowTitle("提示")
                msg_box.setStyleSheet("""
                    QMessageBox {
                        background-color: #333333;
                        color: white;
                        font-size: 14px;
                    }
                    QMessageBox QLabel {
                        color: white;
                    }
                    QMessageBox QPushButton {
                        background-color: #555555;
                        color: white;
                        border: none;
                        padding: 5px 15px;
                        border-radius: 3px;
                    }
                """)
                msg_box.exec_()
                return

            if new_pwd != confirm_pwd:
                # 修改密码不一致弹窗样式
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setText("两次输入的新密码不一致")
                msg_box.setWindowTitle("提示")
                msg_box.setStyleSheet("""
                    QMessageBox {
                        background-color: #333333;
                        color: white;
                        font-size: 14px;
                    }
                    QMessageBox QLabel {
                        color: white;
                    }
                    QMessageBox QPushButton {
                        background-color: #555555;
                        color: white;
                        border: none;
                        padding: 5px 15px;
                        border-radius: 3px;
                    }
                """)
                msg_box.exec_()
                return

            # 加密新密码并更新数据库
            encrypted_pwd = self.encrypt_password(new_pwd)
            sql = "UPDATE users SET password = %s WHERE username = %s"
            result = self.db_connector.execute_query(sql, (encrypted_pwd, self.username))

            if result > 0:
                # 修改成功弹窗样式
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Information)
                msg_box.setText("密码修改成功")
                msg_box.setWindowTitle("成功")
                msg_box.setStyleSheet("""
                    QMessageBox {
                        background-color: #333333;
                        color: white;
                        font-size: 14px;
                    }
                    QMessageBox QLabel {
                        color: white;
                    }
                    QMessageBox QPushButton {
                        background-color: #555555;
                        color: white;
                        border: none;
                        padding: 5px 15px;
                        border-radius: 3px;
                    }
                """)
                msg_box.exec_()
                self.load_user_info()  # 刷新显示
            else:
                # 修改失败弹窗样式
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setText("密码修改失败，请重试")
                msg_box.setWindowTitle("失败")
                msg_box.setStyleSheet("""
                    QMessageBox {
                        background-color: #333333;
                        color: white;
                        font-size: 14px;
                    }
                    QMessageBox QLabel {
                        color: white;
                    }
                    QMessageBox QPushButton {
                        background-color: #555555;
                        color: white;
                        border: none;
                        padding: 5px 15px;
                        border-radius: 3px;
                    }
                """)
                msg_box.exec_()

    def logout(self):
        """退出（保持不变）"""
        reply = QMessageBox.question(
            self, "确认退出", "确定要退出系统吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            QMessageBox.information(self, "成功", "已退出登录")
            self.accept()
            if hasattr(self.parentWidget(), 'logout_handle'):
                self.parentWidget().logout_handle()


class VideoListPage(QWidget):
    """视频列表页面"""
    switch_to_page = pyqtSignal(str)
    refresh_list = pyqtSignal()  # 用于接收外部刷新通知

    def __init__(self, db_connector, video_dir, parent=None):
        super().__init__(parent)
        self.db_connector = db_connector
        self.video_dir = video_dir
        self.videos = []
        self.init_ui()
        self.load_videos_from_db()
        self.refresh_list.connect(self.load_videos_from_db)  # 绑定刷新信号到加载方法

    def init_ui(self):
        self.setStyleSheet("background-color: #1a1a1a;")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        title_layout = QHBoxLayout()
        title_label = QLabel("视频列表")
        title_label.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        back_btn = QPushButton("返回")
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db; color: white; 
                border: none; border-radius: 5px; 
                padding: 8px 15px; font-size: 14px;
            }
            QPushButton:hover { background-color: #2980b9; }
        """)
        back_btn.clicked.connect(lambda: self.switch_to_page.emit("home"))
        title_layout.addWidget(title_label)
        title_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        title_layout.addWidget(back_btn)
        main_layout.addLayout(title_layout)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("background-color: #252525; border-radius: 5px;")
        self.list_widget = QWidget()
        self.list_layout = QGridLayout(self.list_widget)
        self.list_layout.setSpacing(20)
        self.list_layout.setContentsMargins(20, 20, 20, 20)
        scroll_area.setWidget(self.list_widget)
        main_layout.addWidget(scroll_area)

    def load_videos_from_db(self):
        """从数据库加载视频记录"""
        sql = "SELECT video_path, create_time FROM videos ORDER BY create_time DESC"
        try:
            self.videos = self.db_connector.execute_query(sql)
            self.refresh_video_list()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"获取视频列表失败: {e}")

    def refresh_video_list(self):
        """刷新视频列表显示"""
        # 清空现有列表
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

        # 添加新的视频项
        column, row = 0, 0
        for video_path, create_time in self.videos:
            if not os.path.exists(video_path):
                continue  # 跳过不存在的视频文件

            video_item = VideoItemWidget(video_path, create_time)
            video_item.play_signal.connect(self.play_video)
            video_item.delete_signal.connect(self.delete_video)

            self.list_layout.addWidget(video_item, row, column)

            # 计算网格位置
            column += 1
            if column >= 3:  # 每行显示3个视频
                column = 0
                row += 1

    def play_video(self, video_path):
        """播放视频"""
        dialog = VideoPlayerDialog(video_path, self)
        dialog.exec_()

    def delete_video(self, video_path):
        """删除视频"""
        reply = QMessageBox.question(self, "确认", f"确定要删除视频 {os.path.basename(video_path)} 吗？",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                # 从文件系统删除
                if os.path.exists(video_path):
                    os.remove(video_path)

                # 从数据库删除
                sql = "DELETE FROM videos WHERE video_path = %s"
                self.db_connector.execute_query(sql, (video_path,))

                # 刷新列表
                self.load_videos_from_db()
                QMessageBox.information(self, "成功", "视频已删除")

            except Exception as e:
                QMessageBox.warning(self, "错误", f"删除视频失败: {e}")

    def closeEvent(self, event):
        """页面关闭时清理资源"""
        # 清空列表
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
        super().closeEvent(event)

class DetectionThread(QThread):
    """车辆检测异步线程"""
    detection_complete = pyqtSignal(list, list)  # 发送检测结果的信号
    error_occurred = pyqtSignal(str)  # 发送错误信息的信号

    def __init__(self, detector, frame):
        super().__init__()
        self.detector = detector  # 车辆检测器实例
        self.frame = frame  # 待检测的视频帧

    def run(self):
        """线程执行函数：执行检测并发送结果"""
        try:
            # 执行核心检测逻辑
            labels, boxes = self.detector.detect(self.frame)
            self.detection_complete.emit(labels, boxes)
        except Exception as e:
            # 捕获检测过程中的错误并发送
            self.error_occurred.emit(f"检测方法出错: {str(e)}")

class HomePage(QWidget):
    """主页面"""
    switch_to_page = pyqtSignal(str)

    def __init__(self, username, parent=None):
        super().__init__(parent)
        self.username = username
        self.db_config = {
            'host': 'localhost',
            'user': 'root',
            'password': os.getenv('MYSQL_PASSWORD', ''),
            'database': 'ai250317',
            'port': 3306,
            'charset': 'utf8mb4'
        }
        self.recording_start_time = None  # 记录当前录制视频的开始时间（用于判断是否满20秒）
        self.db_connector = DBConnector(self.db_config)
        self.video_dir = "recorded_videos"
        self.drive_video_cap = None
        self.drive_video_timer = None #导航视频的相关属性
        os.makedirs(self.video_dir, exist_ok=True)

        # 异步检测相关属性
        self.detection_thread = None  # 检测线程实例
        self.last_labels = []  # 上一次检测的标签
        self.last_boxes = []  # 上一次检测的边界框
        self.detection_counter = 0  # 检测频率计数器
        self.detection_frequency = 1  # 每3帧检测一次（可调整）



        # 初始化车辆检测器（添加异常捕获）
        try:
            self.vehicle_detector = VehicleDetector(
                weights='yolov7.pt',  # 确保路径正确
                device='cpu'
            )
            # 验证模型是否加载成功（假设VehicleDetector有验证方法）
            if not hasattr(self.vehicle_detector, 'model') or self.vehicle_detector.model is None:
                raise Exception("模型未成功加载")
            print("车辆检测器初始化成功")
        except Exception as e:
            QMessageBox.critical(self, "初始化失败", f"车辆检测器加载失败：\n{str(e)}")
            self.vehicle_detector = None  # 标记为无效
            print(f"VehicleDetector初始化失败: {e}")

        # 疲劳驾驶检测模型
        self.detector = driving_detect()

        # 初始化UI
        self.init_ui()
        # 摄像头与检测相关初始化
        self.cap = None
        self.is_recording = False
        self.frame_count = 0
        self.save_interval = 20 * 10  # 20秒，假设帧率为10帧/秒
        self.video_writer = None
        self.current_video_path = ""

        # 关联信号与页面切换逻辑
        self.switch_to_page.connect(self.handle_page_switch)
        #拍照后刷新图片列表的信号关联
        self.photo_page.refresh_list.connect(self.photo_page.load_photos_from_db)

    def init_ui(self):
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 初始化堆叠窗口
        self.stacked_widget = QStackedWidget()
        self.init_stacked_pages()
        main_layout.addWidget(self.stacked_widget, stretch=1)

        # 底部导航
        self.init_bottom_nav(main_layout)

    def init_stacked_pages(self):
        """初始化堆叠页面（添加图片列表页）"""
        # 主页面
        self.main_page = QWidget()
        self.init_main_page()
        self.stacked_widget.addWidget(self.main_page)

        # 视频列表页
        self.video_page = VideoListPage(self.db_connector, self.video_dir)
        self.video_page.switch_to_page.connect(self.switch_to_page)
        self.stacked_widget.addWidget(self.video_page)

        # 新增：图片列表页
        self.photo_dir = "captured_photos"
        os.makedirs(self.photo_dir, exist_ok=True)
        self.photo_page = PhotoListPage(self.db_connector, self.photo_dir)
        self.photo_page.switch_to_page.connect(self.switch_to_page)
        self.stacked_widget.addWidget(self.photo_page)

    def init_main_page(self):
        """初始化主页面内容"""
        main_layout = QVBoxLayout(self.main_page)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # 初始化时间刷新
        self.init_time_refresh()

        # 添加中间功能区
        self.init_middle_controls(main_layout)

    def init_time_refresh(self):
        """初始化定时器，每秒刷新一次时间"""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_current_time)
        self.timer.start(1000)  # 每秒触发一次
        self.update_current_time()  # 立即更新一次时间

    def update_current_time(self):
        """更新当前时间显示"""
        if hasattr(self, 'time_label'):
            self.time_label.setText(get_current_time())

    def init_bottom_nav(self, main_layout):
        """初始化底部导航栏（修改pictures按钮绑定）"""
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(20)
        bottom_layout.setAlignment(Qt.AlignCenter)

        # 按钮与功能的映射（修改pictures按钮的回调函数）
        button_actions = [
            ("images/alarm.png", self.trigger_driving_detection),  # 疲劳驾驶检测
            ("images/road.png", self.play_drive_video),  # 导航
            ("images/photos.png", self.take_photo),  # 拍照
            ("images/home.png", self.stub_method),  # 主页
            ("images/video.png", self.open_video_list),  # 录像（视频列表）
            ("images/pictures.png", self.open_photo_list),  # 相册（图片列表）- 修改这里
            ("images/person.png", self.show_personal_info),  # 个人中心
        ]

        for icon_path, func in button_actions:
            btn = QPushButton()
            btn.setIcon(get_icon(icon_path))
            btn.setIconSize(QSize(40, 40))
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                }
                QPushButton:hover {
                    opacity: 0.8;
                }
            """)
            btn.clicked.connect(func)
            bottom_layout.addWidget(btn)

        main_layout.addLayout(bottom_layout)

    def show_personal_info(self):
        """显示个人信息弹窗"""
        dialog = PersonalInfoDialog(self.username, self.db_connector, self)
        dialog.exec_()

    def logout_handle(self):
        """退出登录处理逻辑：关闭主窗口，返回登录界面（不删除用户）"""
        # 1. 停止可能的检测/录制任务，释放资源
        self.stop_detection()
        from page.loginwidget import StackedWidgetDemo
        # 2. 关闭当前主窗口（StackedWidgetDemo）
        main_window = None
        if hasattr(self, 'parent') and isinstance(self.parent(), StackedWidgetDemo):
            main_window = self.parent()
        elif self.window() and isinstance(self.window(), StackedWidgetDemo):
            main_window = self.window()

        if main_window:
            main_window.close()  # 关闭主窗口

            # 3. 显示登录界面（局部导入避免循环依赖）
            from page.loginwidget import LoginWidget
            login_window = LoginWidget(db_config=self.db_config)  # 创建登录窗口实例
            login_window.show()  # 显示登录界面
        else:
            # 异常情况：直接关闭当前页面
            self.close()

    def play_drive_video(self):
        """播放drive_video文件夹下的drive.mp4并进行车辆检测"""
        # 视频路径：与home_page上一级文件夹同级的drive_video/drive.mp4
        import sys
        from pathlib import Path
        current_dir = Path(__file__).parent
        video_path = current_dir.parent.parent / 'yolov7-main' / "drive_video" / "drive.mp4"

        if not video_path.exists():
            QMessageBox.warning(self, "错误", f"视频文件不存在：\n{video_path}")
            return

        # 停止可能正在进行的摄像头检测
        if self.is_recording:
            self.stop_detection()

        # 打开视频文件
        self.drive_video_cap = cv2.VideoCapture(str(video_path))
        if not self.drive_video_cap.isOpened():
            QMessageBox.warning(self, "错误", "无法打开视频文件")
            return

        # 启动视频播放定时器，绑定到车辆检测处理方法
        self.drive_video_timer = QTimer(self)
        self.drive_video_timer.timeout.connect(self.process_vehicle_detection_frame)
        # 根据视频帧率设置定时器间隔
        fps = self.drive_video_cap.get(cv2.CAP_PROP_FPS) or 25
        self.drive_video_timer.start(int(1000 / fps))  # 毫秒级间隔

    def process_vehicle_detection_frame(self):
        """处理导航视频帧并进行车辆检测（异步优化版）"""
        try:
            # 检查车辆检测器是否有效
            if not self.vehicle_detector:
                QMessageBox.warning(self, "错误", "车辆检测器未初始化")
                self.drive_video_timer.stop()
                return

            # 读取视频帧
            ret, frame = self.drive_video_cap.read()
            if not ret:
                # 视频结束，释放资源
                self.drive_video_timer.stop()
                self.drive_video_cap.release()
                self.car_video_label.setPixmap(
                    QPixmap("images/car.png").scaled(600, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                return

            # 检查帧是否有效
            if frame is None or frame.size == 0:
                raise Exception("读取到空帧")

            # 显示用的帧（始终使用当前帧，避免画面冻结）
            display_frame = frame.copy()

            # 检测频率控制：每N帧执行一次检测
            self.detection_counter = (self.detection_counter + 1) % self.detection_frequency

            # 仅在计数器为0且无活跃线程时启动检测
            if self.detection_counter == 0 and (not self.detection_thread or not self.detection_thread.isRunning()):
                # 创建新的检测线程
                self.detection_thread = DetectionThread(self.vehicle_detector, frame)
                # 绑定信号处理函数
                self.detection_thread.detection_complete.connect(self.update_detection_results)
                self.detection_thread.error_occurred.connect(self.handle_detection_error)
                self.detection_thread.start()

            # 绘制上一次的检测结果（保证画面流畅）
            self.draw_detection_results(display_frame)

            # 转换为Qt图像格式并显示
            try:
                frame_rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                h, w, ch = frame_rgb.shape
                q_img = QImage(frame_rgb.data, w, h, ch * w, QImage.Format_RGB888)
                if q_img.isNull():
                    raise Exception("转换为QImage失败")
                self.car_video_label.setPixmap(
                    QPixmap.fromImage(q_img).scaled(600, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            except Exception as e:
                raise Exception(f"图像格式转换失败: {str(e)}")

        except Exception as e:
            # 捕获所有异常，显示错误并停止视频播放
            error_msg = f"视频处理失败: {str(e)}"
            print(error_msg)
            QMessageBox.critical(self, "处理错误", error_msg)
            # 停止定时器和视频捕获，避免崩溃扩散
            if self.drive_video_timer and self.drive_video_timer.isActive():
                self.drive_video_timer.stop()
            if self.drive_video_cap and self.drive_video_cap.isOpened():
                self.drive_video_cap.release()
            # 恢复初始显示
            self.car_video_label.setPixmap(
                QPixmap("images/car.png").scaled(600, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def update_detection_results(self, labels, boxes):
        """更新检测结果（由检测线程触发）"""
        self.last_labels = labels
        self.last_boxes = boxes

    def handle_detection_error(self, error_msg):
        """处理检测线程中的错误（由检测线程触发）"""
        print(f"异步检测错误: {error_msg}")
        # 可根据需要显示错误提示，避免频繁弹窗干扰
        # QMessageBox.warning(self, "检测错误", error_msg)

    def draw_detection_results(self, frame):
        """绘制检测结果（独立提取为函数）"""
        if self.last_labels and self.last_boxes and len(self.last_labels) == len(self.last_boxes):
            for i, box in enumerate(self.last_boxes):
                # 检查box格式是否正确（必须是4个整数坐标）
                if len(box) != 4:
                    continue
                try:
                    cls_name = self.last_labels[i].split()[0]
                    # 避免索引越界（names列表中可能没有cls_name）
                    if cls_name not in self.vehicle_detector.names:
                        continue
                    cls_id = self.vehicle_detector.names.index(cls_name)
                    color = self.vehicle_detector.colors[cls_id] if cls_id < len(
                        self.vehicle_detector.colors) else (0, 255, 0)
                    # 绘制边界框（确保坐标在有效范围内）
                    x1, y1, x2, y2 = map(int, box)
                    x1 = max(0, min(x1, frame.shape[1]))
                    y1 = max(0, min(y1, frame.shape[0]))
                    x2 = max(0, min(x2, frame.shape[1]))
                    y2 = max(0, min(y2, frame.shape[0]))
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(frame, self.last_labels[i], (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                except Exception as e:
                    print(f"绘制第{i}个检测结果失败: {e}")
                    continue

    def open_photo_list(self):
        """打开图片列表页面"""
        self.switch_to_page.emit("photo_list")

    def stub_method(self):
        pass

    def open_video_list(self):
        """打开视频列表页面"""
        self.switch_to_page.emit("video_list")

    def update_user_info(self, new_username):
        """更新用户名显示"""
        self.username = new_username
        if hasattr(self, 'username_label'):
            self.username_label.setText(f"你好，{new_username}")

    def init_middle_controls(self, main_layout):
        """初始化中间控制区域"""
        # 中间功能布局（水平分栏）
        middle_layout = QHBoxLayout()
        middle_layout.setSpacing(80)

        # 左侧功能按钮
        left_layout = QVBoxLayout()
        left_layout.setAlignment(Qt.AlignTop)

        left_buttons = [
            {"text": "中心锁", "icon": "images/lock.png", "size": 64},
            {"text": "油箱", "icon": "images/oil.png", "size": 64},
            {"text": "主题", "icon": "images/clothes.png", "size": 64},
        ]

        for btn_info in left_buttons:
            btn = QPushButton()
            btn.setText(btn_info["text"])
            btn.setIcon(get_icon(btn_info["icon"], QSize(btn_info["size"], btn_info["size"])))
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: white;
                    border: none;
                    font-size: 14px;
                    padding: 10px 0;
                    text-align: center;
                }
                QPushButton:hover {
                    color: #ccc;
                }
            """)
            left_layout.addWidget(btn)

        left_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        middle_layout.addLayout(left_layout, stretch=1)

        # 中间区域（用户信息 + 车辆图/视频显示）
        center_layout = QVBoxLayout()

        # 用户信息和系统时间（纵向排列）
        user_info_layout = QVBoxLayout()
        user_info_layout.setAlignment(Qt.AlignCenter)
        user_info_layout.setSpacing(5)  # 垂直间距

        # 用户名
        self.username_label = QLabel(f"你好，{self.username}")
        self.username_label.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        self.username_label.setAlignment(Qt.AlignCenter)

        # 系统时间（动态更新）
        self.time_label = QLabel(get_current_time())
        self.time_label.setStyleSheet("color: white; font-size: 14px;")
        self.time_label.setAlignment(Qt.AlignCenter)

        # 天气信息
        self.weather_label = QLabel("天气：小雨，温度：8℃-10℃")
        self.weather_label.setStyleSheet("color: white; font-size: 14px;")
        self.weather_label.setAlignment(Qt.AlignCenter)

        user_info_layout.addWidget(self.username_label)
        user_info_layout.addWidget(self.time_label)
        user_info_layout.addWidget(self.weather_label)

        center_layout.addLayout(user_info_layout)
        center_layout.addSpacing(15)  # 与车辆图片/视频显示的间距

        # 车辆图片/视频显示标签
        self.car_video_label = QLabel()
        self.car_video_label.setAlignment(Qt.AlignCenter)
        self.car_video_label.setPixmap(
            QPixmap("images/car.png").scaled(600, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        center_layout.addWidget(self.car_video_label)

        middle_layout.addLayout(center_layout, stretch=2)

        # 右侧功能按钮
        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignTop)

        right_buttons = [
            {"text": "空调", "icon": "images/conditioner.png", "size": 64},
            {"text": "座椅", "icon": "images/chair.png", "size": 64},
            {"text": "灯光", "icon": "images/lights.png", "size": 64},
        ]

        for btn_info in right_buttons:
            btn = QPushButton()
            btn.setText(btn_info["text"])
            btn.setIcon(get_icon(btn_info["icon"], QSize(btn_info["size"], btn_info["size"])))
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: white;
                    border: none;
                    font-size: 14px;
                    padding: 10px 0;
                    text-align: center;
                }
                QPushButton:hover {
                    color: #ccc;
                }
            """)
            right_layout.addWidget(btn)

        right_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        middle_layout.addLayout(right_layout, stretch=1)

        main_layout.addLayout(middle_layout)

    def trigger_driving_detection(self):
        """触发疲劳驾驶检测"""
        if not self.is_recording:
            # 打开摄像头
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                QMessageBox.warning(self, "错误", "无法打开摄像头")
                return

            # 启动定时器
            self.frame_timer = QTimer(self)
            self.frame_timer.timeout.connect(self.process_frame)
            self.frame_timer.start(33)  # 约30fps
            self.is_recording = True

            # 初始化视频写入器
            self.start_new_video()
            self.recording_start_time = datetime.now()  # 记录开始时间（用于判断是否满20秒）
        else:
            # 停止检测时判断是否满20秒
            self.stop_detection()

    def start_new_video(self):
        """开始一个新的视频录制"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        self.current_video_path = os.path.join(self.video_dir, f"video_{timestamp}.mp4")

        # 获取摄像头参数
        fps = self.cap.get(cv2.CAP_PROP_FPS) or 10
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # 创建视频写入器
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.video_writer = cv2.VideoWriter(self.current_video_path, fourcc, fps, (width, height))
        self.frame_count = 0
        # 重置开始时间
        self.recording_start_time = datetime.now()

    def process_frame(self):
        """处理摄像头帧"""
        ret, frame = self.cap.read()
        if ret:
            # 疲劳驾驶检测
            labels, boxes = self.detector.detect(frame)

            # 在画面上绘制检测结果
            if labels and boxes:
                for i, box in enumerate(boxes):
                    cv2.rectangle(frame, (box[0], box[1]), (box[2], box[3]), (0, 255, 0), 2)
                    cv2.putText(frame, labels[i], (box[0], box[1] - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            # 转换颜色空间并显示在界面
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame_rgb.shape
            q_img = QImage(frame_rgb.data, w, h, ch * w, QImage.Format_RGB888)
            self.car_video_label.setPixmap(
                QPixmap.fromImage(q_img).scaled(600, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))

            # 写入视频
            self.video_writer.write(frame)
            self.frame_count += 1

            # 检查是否达到20秒（通过时间差判断，更准确）
            elapsed_time = (datetime.now() - self.recording_start_time).total_seconds()
            if elapsed_time >= 20:  # 满20秒才保存
                self.video_writer.release()
                # 保存到数据库
                self.save_video_to_db(self.current_video_path, datetime.now())
                # 通知视频列表刷新
                self.video_page.refresh_list.emit()  # 触发列表刷新
                # 开始新的视频录制
                self.start_new_video()
        else:
            self.stop_detection()

    def save_video_to_db(self, video_path, create_time):
        """将视频信息保存到数据库"""
        try:
            sql = "INSERT INTO videos (video_path, video_state, create_time) VALUES (%s, %s, %s)"
            video_state = 1  # 1表示正常
            create_time_str = create_time.strftime("%Y-%m-%d %H:%M:%S")
            # 执行SQL并检查结果
            result = self.db_connector.execute_query(sql, (video_path, video_state, create_time_str))
            if result <= 0:
                print("视频未成功写入数据库")
        except Exception as e:
            print(f"保存视频到数据库失败: {e}")

    def stop_detection(self):
        """停止检测（仅保存满20秒的视频）"""
        if self.is_recording:
            self.frame_timer.stop()
            # 计算录制时长
            elapsed_time = (
                    datetime.now() - self.recording_start_time).total_seconds() if self.recording_start_time else 0
            if self.video_writer:
                self.video_writer.release()
                # 仅保存满20秒的视频
                if elapsed_time >= 20 and os.path.exists(self.current_video_path):
                    # 写入数据库
                    self.save_video_to_db(self.current_video_path, datetime.now())
                    # 通知列表刷新
                    self.video_page.refresh_list.emit()
                else:
                    # 不足20秒，删除无效文件
                    if os.path.exists(self.current_video_path):
                        os.remove(self.current_video_path)
                        print(f"删除未达20秒的视频: {self.current_video_path}")
            if self.cap and self.cap.isOpened():
                self.cap.release()
            self.is_recording = False
            self.recording_start_time = None  # 重置开始时间

    def take_photo(self):
        """截取摄像头当前帧（带检测标记）并保存，仅在检测功能启动时可用"""
        # 确保检测功能已启动（摄像头已打开且处于录制状态）
        if not self.is_recording or not self.cap or not self.cap.isOpened():
            # 修改弹窗样式：将警告弹窗的文本和背景色改为白色相关
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setText("摄像头未开启，请先启动驾驶检测功能")
            msg_box.setWindowTitle("错误")
            # 设置弹窗样式表（白色文本+深灰背景，确保可读性）
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #333333;  /* 深灰背景 */
                    color: white;               /* 白色文本 */
                    font-size: 14px;
                }
                QMessageBox QLabel {
                    color: white;               /* 标签文本白色 */
                }
                QMessageBox QPushButton {
                    background-color: #555555;  /* 按钮背景 */
                    color: white;               /* 按钮文本白色 */
                    border: none;
                    padding: 5px 15px;
                    border-radius: 3px;
                }
                QMessageBox QPushButton:hover {
                    background-color: #777777;  /* 按钮悬停效果 */
                }
            """)
            msg_box.exec_()
            return

        # 尝试获取当前处理后的帧（带检测标记）
        try:
            # 创建照片保存目录
            photo_dir = "captured_photos"
            os.makedirs(photo_dir, exist_ok=True)

            # 生成唯一文件名（基于时间戳）
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            photo_path = os.path.join(photo_dir, f"photo_{timestamp}.jpg")

            # 获取当前显示的带检测标记的帧
            pixmap = self.car_video_label.pixmap()
            if pixmap and not pixmap.isNull():
                # 转换为QImage
                q_image = pixmap.toImage()
                # 转换为RGB格式
                if q_image.format() != QImage.Format_RGB888:
                    q_image = q_image.convertToFormat(QImage.Format_RGB888)
                # 转换为OpenCV格式
                width = q_image.width()
                height = q_image.height()
                ptr = q_image.bits()
                ptr.setsize(height * width * 3)
                frame = np.frombuffer(ptr, np.uint8).reshape((height, width, 3))
                # 转换为BGR格式（OpenCV默认格式）
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

                # 保存图片
                cv2.imwrite(photo_path, frame)

                # 获取当前截图保存时间
                capture_time = datetime.now()

                # 显示拍照成功提示（同样应用白色文本样式）
                success_box = QMessageBox(self)
                success_box.setIcon(QMessageBox.Information)
                success_box.setText(f"照片已保存至：\n{photo_path}")
                success_box.setWindowTitle("成功")
                success_box.setStyleSheet("""
                    QMessageBox {
                        background-color: #333333;
                        color: white;
                        font-size: 14px;
                    }
                    QMessageBox QLabel {
                        color: white;
                    }
                    QMessageBox QPushButton {
                        background-color: #555555;
                        color: white;
                        border: none;
                        padding: 5px 15px;
                        border-radius: 3px;
                    }
                    QMessageBox QPushButton:hover {
                        background-color: #777777;
                    }
                """)
                success_box.exec_()

                # 将照片路径和保存时间写入数据库
                self.save_photo_to_db(photo_path, capture_time)

                # 拍照成功后立即刷新图片列表
                self.photo_page.refresh_list.emit()

            else:
                # 无法获取画面的警告弹窗（白色文本）
                err_box = QMessageBox(self)
                err_box.setIcon(QMessageBox.Warning)
                err_box.setText("无法获取当前检测画面")
                err_box.setWindowTitle("错误")
                err_box.setStyleSheet("""
                    QMessageBox {
                        background-color: #333333;
                        color: white;
                        font-size: 14px;
                    }
                    QMessageBox QLabel {
                        color: white;
                    }
                    QMessageBox QPushButton {
                        background-color: #555555;
                        color: white;
                        border: none;
                        padding: 5px 15px;
                        border-radius: 3px;
                    }
                """)
                err_box.exec_()

        except Exception as e:
            # 保存失败的警告弹窗（白色文本）
            exc_box = QMessageBox(self)
            exc_box.setIcon(QMessageBox.Warning)
            exc_box.setText(f"保存照片失败：{str(e)}")
            exc_box.setWindowTitle("错误")
            exc_box.setStyleSheet("""
                QMessageBox {
                    background-color: #333333;
                    color: white;
                    font-size: 14px;
                }
                QMessageBox QLabel {
                    color: white;
                }
                QMessageBox QPushButton {
                    background-color: #555555;
                    color: white;
                    border: none;
                    padding: 5px 15px;
                    border-radius: 3px;
                }
            """)
            exc_box.exec_()

        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存照片失败：{str(e)}")

    def save_photo_to_db(self, photo_path, create_time):
        """将照片路径和保存时间写入数据库"""
        try:
            # 插入照片路径和保存时间（photo_id由数据库自动递增）
            sql = "INSERT INTO photos (photo_path, create_time) VALUES (%s, %s)"
            # 格式化时间为数据库兼容的字符串格式
            create_time_str = create_time.strftime("%Y-%m-%d %H:%M:%S")
            result = self.db_connector.execute_query(sql, (photo_path, create_time_str))
            if result <= 0:
                print("照片信息未成功写入数据库")
            else:
                print(f"照片信息已写入数据库：{photo_path}（保存时间：{create_time_str}）")

                # 新增：数据库写入成功后也发送刷新信号（双重保障）
                self.photo_page.refresh_list.emit()
        except Exception as e:
            print(f"保存照片到数据库失败: {e}")

    def closeEvent(self, event):
        """关闭窗口时释放资源"""
        self.stop_detection()
        super().closeEvent(event)

    def handle_page_switch(self, page_name):#页面切换处理方法
        """根据页面名称切换到对应的页面"""
        if page_name == "video_list":
            self.stacked_widget.setCurrentIndex(1)  # 视频列表页
        elif page_name == "photo_list":  # 新增图片列表页切换
            self.stacked_widget.setCurrentIndex(2)
        elif page_name == "home":
            self.stacked_widget.setCurrentIndex(0)  # 主页面
