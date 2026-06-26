# -*- coding: utf-8 -*-
# @Time    : 2025/6/16
# @Author  : 小宇
# @File    : loginwidget.py

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from code import Code
from page.registration import RegisterWidget
from page.database import DatabaseManager
from page.home_page import HomePage
from page.music_page import MusicPage
from page.phone_page import PhonePage

class LoginWidget(QWidget):
    def __init__(self, db_config, w=800, h=600):
        super().__init__()
        self.w = w
        self.h = h
        self.resize(self.w, self.h)
        self.setWindowTitle('智能座舱 - 登录')
        self.setWindowIcon(QIcon(QPixmap("images/icon.png")))
        self.current_captcha = ""
        self.captcha_label = Code(self)
        self.captcha_label.setFixedSize(120, 40)
        self.init_window_items()
        self.main_window = None  # 主界面引用

        # 数据库配置与管理器
        self.db_config = db_config
        self.db_manager = DatabaseManager(db_config)

        # 生成初始验证码
        self.generate_captcha()
        self.captcha_label.code_updated.connect(self.update_captcha)

    def init_window_items(self):
        """初始化界面控件"""
        self.total_layout = QVBoxLayout()
        self.total_layout.setAlignment(Qt.AlignCenter)
        self.setLayout(self.total_layout)

        # 标题
        title_label = QLabel("智能座舱系统")
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
        self.pwd_edit.setEchoMode(QLineEdit.Password)  # 默认加密显示
        # 添加密码显示/隐藏切换按钮
        self.eye_btn = QPushButton()
        self.eye_btn.setIcon(QIcon(QPixmap("images/eye_close.png")))  # 默认显示关闭图标
        self.eye_btn.setIconSize(QSize(24, 24))
        self.eye_btn.setStyleSheet("""
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
        self.eye_btn.setCheckable(True)  # 用于切换状态
        self.eye_btn.clicked.connect(self.toggle_password_visibility)  # 绑定切换事件
        # 将组件添加到布局（标签+输入框+眼睛图标）
        pwd_layout.addWidget(pwd_label)
        pwd_layout.addWidget(self.pwd_edit)
        pwd_layout.addWidget(self.eye_btn)
        self.total_layout.addLayout(pwd_layout)
        self.total_layout.addSpacing(20)

        # 验证码输入
        captcha_layout = QHBoxLayout()
        captcha_label = QLabel("验证码:")
        captcha_label.setFont(QFont("微软雅黑", 12))
        self.captcha_edit = QLineEdit()
        captcha_layout.addWidget(captcha_label)
        captcha_layout.addWidget(self.captcha_edit)
        captcha_layout.addWidget(self.captcha_label)
        self.total_layout.addLayout(captcha_layout)
        self.total_layout.addSpacing(40)

        # 按钮布局
        btn_layout = QHBoxLayout()
        self.login_btn = QPushButton("登录")
        self.register_btn = QPushButton("注册")
        self.quit_btn = QPushButton("退出")
        btn_layout.addWidget(self.login_btn)
        btn_layout.addWidget(self.register_btn)
        btn_layout.addWidget(self.quit_btn)
        self.total_layout.addLayout(btn_layout)

        # 信号连接
        self.login_btn.clicked.connect(self.handle_login)
        self.register_btn.clicked.connect(self.show_register)
        self.quit_btn.clicked.connect(self.close)

    def toggle_password_visibility(self):
        """切换密码的显示状态（加密/明文）"""
        if self.eye_btn.isChecked():
            # 切换为明文显示
            self.pwd_edit.setEchoMode(QLineEdit.Normal)
            self.eye_btn.setIcon(QIcon(QPixmap("images/eye_open.png")))
        else:
            # 切换为加密显示
            self.pwd_edit.setEchoMode(QLineEdit.Password)
            self.eye_btn.setIcon(QIcon(QPixmap("images/eye_close.png")))

    def generate_captcha(self):
        """生成新的验证码"""
        self.captcha_label.ui_init()
        self.current_captcha = self.captcha_label.text.lower()

    def update_captcha(self):
        """更新当前验证码文本"""
        self.current_captcha = self.captcha_label.text.lower()

    def handle_login(self):
        """处理登录逻辑（数据库验证）"""
        username = self.user_edit.text().strip()
        password = self.pwd_edit.text().strip()
        captcha = self.captcha_edit.text().strip().lower()

        # 输入验证
        if not all([username, password, captcha]):
            QMessageBox.warning(self, "登录失败", "用户名、密码和验证码不能为空")
            return
        if captcha != self.current_captcha:
            QMessageBox.warning(self, "登录失败", "验证码错误，请重新输入")
            self.generate_captcha()
            return

        # 数据库验证
        user_info = self.db_manager.validate_user(username, password)
        if user_info:
            userid, username, userstate = user_info
            if userstate == 1:  # 有效用户
                self.show_main_window(username, userid)
            else:
                QMessageBox.warning(self, "登录失败", "用户状态异常，请联系管理员")
        else:
            QMessageBox.warning(self, "登录失败", "用户名或密码错误")

    def show_main_window(self, username, userid):
        """显示主界面并传递用户信息（示例：创建一个简单主窗口）"""
        self.main_window = StackedWidgetDemo(username, userid)
        self.main_window.show()
        self.hide()

    def show_register(self):
        """显示注册界面"""
        self.register_window = RegisterWidget(self.db_config)
        self.register_window.back_to_login_signal.connect(self.show)
        self.register_window.show()
        self.hide()

    def closeEvent(self, event):
        """关闭窗口时清理资源"""
        self.db_manager.close_connection()  # 关闭数据库连接
        if self.main_window:
            self.main_window.close()
        super().closeEvent(event)



class StackedWidgetDemo(QMainWindow):
    def __init__(self, username="linshiyu", userid=None):
        super().__init__()
        self.current_username = username
        self.userid = userid
        self.login_window = None  # 登录窗口引用
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('智能座舱系统')
        self.setWindowIcon(QIcon(QPixmap("images/icon.png")))
        self.setGeometry(100, 100, 1000, 600)
        self.setStyleSheet("background-color: #2b2b2b;")

        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 左侧导航栏
        self.left_nav = QWidget()
        self.left_nav.setFixedWidth(80)
        self.left_nav_layout = QVBoxLayout(self.left_nav)
        self.left_nav_layout.setAlignment(Qt.AlignTop)
        self.left_nav_layout.setContentsMargins(0, 20, 0, 20)
        self.init_left_nav()

        main_layout.addWidget(self.left_nav)

        # 右侧内容区
        self.stacked_widget = QStackedWidget()
        self.init_stacked_pages()
        main_layout.addWidget(self.stacked_widget, stretch=1)

    def init_left_nav(self):
        # 导航按钮配置（保持原有配置不变）
        self.nav_buttons = [
            {"icon": "images/music.png", "size": 40, "page": 1},  # 音乐
            {"icon": "images/phone.png", "size": 40, "page": 2},  # 电话
            {"icon": "images/direction.png", "size": 40, "page": 3},  # 地图导航
            {"icon": "images/home.png", "size": 40, "page": 0},  # 首页
        ]

        # 创建按钮并添加到布局
        for btn_info in self.nav_buttons:
            btn = QPushButton()
            btn.setIcon(QIcon(QPixmap(btn_info["icon"])))
            btn.setIconSize(QSize(btn_info["size"], btn_info["size"]))
            btn.setStyleSheet("""
                   QPushButton {
                       background-color: transparent;
                       border: none;
                       padding: 20px 0;
                   }
                   QPushButton:hover {
                       background-color: #444;
                   }
               """)
            if btn_info["page"] != -1:
                btn.clicked.connect(lambda _, idx=btn_info["page"]: self.change_page(idx))
            self.left_nav_layout.addWidget(btn, alignment=Qt.AlignCenter)

        # 垂直 spacer
        self.left_nav_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

    def init_stacked_pages(self):
        # 首页（传用户名）
        self.home_page = HomePage(self.current_username)
        self.stacked_widget.addWidget(self.home_page)

        # 音乐页面（替换为图片显示）
        music_page = QWidget()
        music_layout = QVBoxLayout(music_page)
        music_layout.setContentsMargins(0, 0, 0, 0)
        self.music_label = QLabel()
        self.music_label.setPixmap(QPixmap("images/OPI-C.jpg"))  # 音乐界面图片
        self.music_label.setScaledContents(True)  # 图片自适应标签大小
        music_layout.addWidget(self.music_label)
        self.stacked_widget.addWidget(music_page)

        # 电话页面（替换为图片显示）
        phone_page = QWidget()
        phone_layout = QVBoxLayout(phone_page)
        phone_layout.setContentsMargins(0, 0, 0, 0)
        self.phone_label = QLabel()
        self.phone_label.setPixmap(QPixmap("images/R-C.png"))  # 电话界面图片
        self.phone_label.setScaledContents(True)  # 图片自适应标签大小
        phone_layout.addWidget(self.phone_label)
        self.stacked_widget.addWidget(phone_page)

        # 新增页面（对应左侧新增导航）
        self.map_page = MapPage()  # 使用地图页面类
        self.stacked_widget.addWidget(self.map_page)

    def change_page(self, index):
        # 设置当前页面
        self.stacked_widget.setCurrentIndex(index)

        # 清除所有按钮的高亮状态
        for i in range(len(self.nav_buttons)):
            btn = self.left_nav_layout.itemAt(i).widget()
            if isinstance(btn, QPushButton):
                btn.setStyleSheet("""
                       QPushButton {
                           background-color: transparent;
                           border: none;
                           padding: 20px 0;
                       }
                   """)

        # 查找目标页面索引对应的按钮位置
        target_btn_index = next((i for i, btn_info in enumerate(self.nav_buttons) if btn_info["page"] == index), None)

        # 高亮目标按钮
        if target_btn_index is not None:
            target_btn = self.left_nav_layout.itemAt(target_btn_index).widget()
            if target_btn and isinstance(target_btn, QPushButton):
                target_btn.setStyleSheet("""
                       QPushButton {
                           background-color: #444;
                           border: none;
                           padding: 20px 0;
                       }
                   """)

    def update_username(self, new_username):
        """更新用户名（登录后调用）"""
        self.current_username = new_username
        self.home_page.update_user_info(new_username)

    def set_login_window(self, login_window):
        """保存登录窗口引用，用于退出登录时返回"""
        self.login_window = login_window



class MapPage(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        # 页面布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 创建图形场景（用于放置地图图片）
        self.scene = QGraphicsScene(self)
        # 创建图形视图（用于显示场景，支持缩放和拖动）
        self.view = QGraphicsView(self.scene)
        # 配置视图属性
        self.view.setRenderHint(QPainter.Antialiasing)  # 抗锯齿
        self.view.setRenderHint(QPainter.SmoothPixmapTransform)  # 图片平滑缩放
        self.view.setMouseTracking(True)  # 跟踪鼠标
        self.view.setDragMode(QGraphicsView.ScrollHandDrag)  # 拖动模式（按住鼠标拖动地图）
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # 隐藏水平滚动条
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # 隐藏垂直滚动条

        #绘制地图
        self.map_pixmap = QPixmap("images/direct.png")  # 假设地图图片路径为 images/map.png
        if not self.map_pixmap.isNull():
            self.map_item = self.scene.addPixmap(self.map_pixmap)
            self.scene.setSceneRect(QRectF(self.map_pixmap.rect()))  # 设置场景大小为图片大小

        layout.addWidget(self.view)
        self.setLayout(layout)# 添加到布局

    def wheelEvent(self, event):
        """鼠标滚轮事件：实现缩放功能"""
        # 获取当前鼠标位置（场景坐标）
        mouse_pos = self.view.mapToScene(event.pos())

        # 缩放因子（滚轮向前放大，向后缩小）
        scale_factor = 1.1 if event.angleDelta().y() > 0 else 0.9

        # 缩放前先将鼠标位置设为锚点（确保缩放中心为鼠标指向的位置）
        self.view.centerOn(mouse_pos)
        self.view.scale(scale_factor, scale_factor)

        # 缩放后重新将鼠标位置设为中心（保持视角）
        self.view.centerOn(mouse_pos)
        event.accept()