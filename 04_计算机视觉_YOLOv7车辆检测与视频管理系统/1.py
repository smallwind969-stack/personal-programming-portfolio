# -*- coding: utf-8 -*-
# @Time    : 2025/7/7 11:01
# @Author  : 小宇
# @File    : 1.py
from PyQt5.QtWidgets import QStackedWidget, QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt


class HomePage(QWidget):
    # 定义信号，用于通知主窗口切换页面
    switch_to_page = pyqtSignal(str)

    def __init__(self, username, parent=None):
        super().__init__(parent)
        self.username = username
        self.video_list_page = None  # 视频列表页面实例

        # 初始化堆叠窗口
        self.stacked_widget = QStackedWidget()
        self.init_stacked_pages()  # 创建所有子页面

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 添加堆叠窗口和底部导航
        main_layout.addWidget(self.stacked_widget, stretch=1)
        self.init_bottom_nav(main_layout)  # 底部导航固定

        # 摄像头与检测相关初始化
        self.cap = None
        self.is_recording = False
        self.frame_count = 0
        self.save_interval = 20 * 10  # 20秒，假设帧率为10帧/秒
        self.video_writer = None
        self.current_video_path = ""

        # 疲劳驾驶检测模型
        self.detector = driving_detect()  # 初始化检测模型

        # 数据库配置
        self.db_config = {
            'host': 'localhost',
            'user': 'root',
            'password': '12345678',
            'database': 'ai250317',
            'port': 3306,
            'charset': 'utf8mb4'
        }

        # 创建视频保存目录
        self.video_dir = "recorded_videos"
        if not os.path.exists(self.video_dir):
            os.makedirs(self.video_dir)

    def init_stacked_pages(self):
        """初始化堆叠页面"""
        # 主页面（原中间功能区）
        self.main_page = QWidget()
        self.init_main_page()
        self.stacked_widget.addWidget(self.main_page)

        # 可添加其他页面
        self.info_page = QWidget()
        info_layout = QVBoxLayout(self.info_page)
        info_layout.addWidget(QLabel("车辆信息页面", alignment=Qt.AlignCenter))
        self.stacked_widget.addWidget(self.info_page)

        self.settings_page = QWidget()
        settings_layout = QVBoxLayout(self.settings_page)
        settings_layout.addWidget(QLabel("设置页面", alignment=Qt.AlignCenter))
        self.stacked_widget.addWidget(self.settings_page)

    def init_main_page(self):
        """初始化主页面内容（原中间功能区）"""
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
        current_time = datetime.now().strftime("%Y.%m.%d %H:%M:%S")
        if hasattr(self, 'time_label'):
            self.time_label.setText(f"{current_time}")

    def init_middle_controls(self, main_layout):
        # 中间功能布局（水平分栏）
        middle_layout = QHBoxLayout()
        middle_layout.setSpacing(80)

        # 左侧功能按钮
        left_layout = QVBoxLayout()
        left_layout.setAlignment(Qt.AlignTop)

        left_buttons = [
            {"text": "中心锁", "icon": "images/lock.png", "size": 32},
            {"text": "油箱", "icon": "images/oil.png", "size": 32},
            {"text": "主题", "icon": "images/clothes.png", "size": 32},
        ]

        for btn_info in left_buttons:
            btn = QPushButton()
            btn.setText(btn_info["text"])
            btn.setIcon(QIcon(QPixmap(btn_info["icon"])))
            btn.setIconSize(QSize(btn_info["size"], btn_info["size"]))
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
        self.time_label = QLabel("2024.02.26 16:17:03")
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

        # 右侧功能按钮（新增页面切换功能）
        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignTop)

        right_buttons = [
            {"text": "空调", "icon": "images/conditioner.png", "size": 32},
            {"text": "车辆信息", "icon": "images/car_info.png", "size": 32, "page": 1},
            {"text": "设置", "icon": "images/settings.png", "size": 32, "page": 2},
        ]

        for btn_info in right_buttons:
            btn = QPushButton()
            btn.setText(btn_info["text"])
            btn.setIcon(QIcon(QPixmap(btn_info["icon"])))
            btn.setIconSize(QSize(btn_info["size"], btn_info["size"]))
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
            # 如果按钮需要切换页面，绑定页面切换事件
            if "page" in btn_info:
                btn.clicked.connect(lambda checked, idx=btn_info["page"]: self.stacked_widget.setCurrentIndex(idx))
            right_layout.addWidget(btn)

        right_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        middle_layout.addLayout(right_layout, stretch=1)

        main_layout.addLayout(middle_layout)

    def init_bottom_nav(self, main_layout):
        """初始化底部导航栏，固定高度并绑定页面切换事件"""
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(20)
        bottom_layout.setAlignment(Qt.AlignCenter)

        # 设置底部导航栏固定高度
        bottom_widget = QWidget()
        bottom_widget.setFixedHeight(80)  # 固定高度
        bottom_widget.setLayout(bottom_layout)

        # 按钮与功能的映射：图标名 → 方法名/页面索引
        button_actions = [
            ("images/alarm.png", self.trigger_driving_detection),  # 疲劳驾驶检测
            ("images/road.png", self.stub_method),  # 导航
            ("images/photos.png", self.stub_method),  # 拍照
            ("images/home.png", lambda: self.stacked_widget.setCurrentIndex(0)),  # 主页
            ("images/video.png", self.open_video_list),  # 录像列表
            ("images/pictures.png", self.stub_method),  # 相册
            ("images/person.png", self.stub_method),  # 个人中心
        ]

        for icon_path, func in button_actions:
            btn = QPushButton()
            btn.setIcon(QIcon(QPixmap(icon_path)))
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

        main_layout.addWidget(bottom_widget)

    # 以下为原有功能代码（保持不变）
    def open_video_list(self):
        """打开视频列表页面"""
        if not self.video_list_page:
            self.video_list_page = VideoListPage(self.db_config, self.video_dir)
            self.video_list_page.switch_to_page.connect(self.switch_to_page)

        self.switch_to_page.emit("video_list")

    def update_user_info(self, new_username):
        """更新用户名显示"""
        self.username = new_username
        self.username_label.setText(f"你好，{new_username}")

    def trigger_driving_detection(self):
        """触发疲劳驾驶检测，开启摄像头、实时检测并保存视频"""
        if not self.is_recording:
            # 打开摄像头
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                QMessageBox.warning(self, "错误", "无法打开摄像头")
                return

            # 启动定时器，用于获取帧和处理检测逻辑
            self.frame_timer = QTimer(self)
            self.frame_timer.timeout.connect(self.process_frame)
            self.frame_timer.start(33)  # 约30fps（33ms/帧）
            self.is_recording = True

            # 初始化视频写入器
            self.start_new_video()
        else:
            # 停止检测
            self.stop_detection()

    def start_new_video(self):
        """开始一个新的20秒视频录制，初始化视频写入器"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        self.current_video_path = os.path.join(self.video_dir, f"video_{timestamp}.mp4")

        # 获取摄像头参数
        fps = self.cap.get(cv2.CAP_PROP_FPS) or 10  # 默认为10fps
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # 创建视频写入器
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.video_writer = cv2.VideoWriter(self.current_video_path, fourcc, fps, (width, height))
        self.frame_count = 0

    def process_frame(self):
        """处理摄像头帧：获取、检测、显示并保存"""
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

            # 检查是否达到20秒的帧数
            if self.frame_count >= self.save_interval:
                self.video_writer.release()
                # 保存视频信息到数据库
                self.save_video_to_db(self.current_video_path, datetime.now())
                # 开始新的20秒视频录制
                self.start_new_video()
        else:
            self.stop_detection()

    def save_video_to_db(self, video_path, create_time):
        """将视频信息保存到数据库videos表"""
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            sql = "INSERT INTO videos (video_path, video_state, create_time) VALUES (%s, %s, %s)"
            video_state = 1  # 1表示正常，0表示异常（可根据检测结果修改）
            create_time_str = create_time.strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(sql, (video_path, video_state, create_time_str))
            conn.commit()
            cursor.close()
            conn.close()
        except Error as e:
            print(f"保存视频到数据库失败: {e}")

    def stop_detection(self):
        """停止疲劳驾驶检测，释放资源"""
        if self.is_recording:
            self.frame_timer.stop()
            if self.video_writer:
                self.video_writer.release()
            if self.cap and self.cap.isOpened():
                self.cap.release()
            self.is_recording = False

    def stub_method(self):
        """暂不实现功能的空方法"""
        pass

    def closeEvent(self, event):
        """关闭窗口时释放资源"""
        self.stop_detection()
        if self.video_list_page:
            self.video_list_page.close()
        super().closeEvent(event)