import random
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from tools import get_input_validator
from code import Code
from registration import RegisterWidget
from gameWidget import GameWidget


class LoginWidget(QWidget):
    # 添加登录成功信号和传递用户名的信号
    login_success = pyqtSignal()
    user_logged_in = pyqtSignal(str)  # 传递登录成功的用户名

    def __init__(self, w=1000, h=800):
        super().__init__()
        self.w = w
        self.h = h
        self.resize(self.w, self.h)
        self.setWindowTitle('登录界面')
        # 处理图片路径可能的异常
        try:
            self.setWindowIcon(QIcon(QPixmap('./images/icon.png')))
        except:
            self.setWindowIcon(QIcon())  # 使用默认图标

        # 设置背景并处理可能的图片加载失败
        palette = QPalette()
        try:
            palette.setBrush(self.backgroundRole(),
                             QBrush(
                                 QPixmap('./images/bg.jpg').scaled(self.w, self.h)))
            self.setPalette(palette)
        except Exception:
            print("背景图片文件未找到，请检查路径。")

        self.current_captcha = None
        self.captcha_label = Code(self)
        self.captcha_label.setFixedSize(120, 40)
        self.captcha_label.code_updated.connect(self.print_current_captcha)

        self.init_window_items()
        self.print_current_captcha()

        # 初始化相关窗口
        self.register_widget = RegisterWidget()
        self.game_widget = GameWidget("")

        # 连接信号与槽
        self.register_widget.back_to_login_signal.connect(self.show_login)
        self.game_widget.show_signal.connect(self.hide_login)
        self.loginBtn.clicked.connect(self.login)
        self.regBtn.clicked.connect(self.show_register)
        self.quiBtn.clicked.connect(self.quit)
        self.captcha_label.setToolTip("点击刷新验证码")

    def init_window_items(self):
        self.totalLayout = QVBoxLayout()
        self.setLayout(self.totalLayout)

        # 用户名行
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

        # 密码行
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

        # 验证码行
        self.line3 = QHBoxLayout()
        self.totalLayout.addLayout(self.line3)
        self.wdLabel = QLabel(' 验证码:', self)
        self.wdLabel.setStyleSheet('color:purple')
        self.wdEdit = QLineEdit(self)
        self.wdEdit.setPlaceholderText(' 请输入验证码 ')
        self.wdEdit.setStyleSheet('color:red')
        self.wdEdit.setValidator(self.validator)
        self.line3.addWidget(self.wdLabel)
        self.line3.addWidget(self.wdEdit)
        self.line3.addWidget(self.captcha_label)
        self.line3.setContentsMargins(10, 0, 100, 0)

        # 按钮行
        self.buttonLayout = QHBoxLayout()
        self.totalLayout.addLayout(self.buttonLayout)
        self.loginBtn = QPushButton('登录', self)
        self.loginBtn.setFixedWidth(100)
        self.regBtn = QPushButton('注册', self)
        self.regBtn.setFixedWidth(100)
        self.quiBtn = QPushButton('退出', self)
        self.quiBtn.setFixedWidth(100)
        self.buttonLayout.addWidget(self.loginBtn)
        self.buttonLayout.addWidget(self.regBtn)
        self.buttonLayout.addWidget(self.quiBtn)

        self.totalLayout.setSpacing(50)

    def login(self):
        """登录验证逻辑"""
        self.username = self.accEdit.text().strip()
        self.password = self.pwdEdit.text().strip()
        self.captcha = self.wdEdit.text().strip().lower()

        # 验证输入完整性
        if not all([self.username, self.password, self.captcha]):
            QMessageBox.warning(self, "登录失败", "用户名、密码和验证码不能为空，请重新输入。")
            return

        # 验证验证码
        self.current_captcha = self.captcha_label.text.lower() if self.captcha_label.text else ""
        if self.captcha != self.current_captcha:
            QMessageBox.warning(self, "登录失败", "验证码错误，请重新输入。")
            self.wdEdit.clear()
            return

        # 验证账号密码
        try:
            with open('users.txt', 'r') as f:
                users = [line.strip().split(':') for line in f.readlines() if line.strip()]

            for stored_username, stored_password in users:
                if self.username == stored_username and self.password == stored_password:
                    QMessageBox.information(self, "登录成功", f"欢迎回来，{self.username}！")
                    # 发送登录成功信号和用户名
                    self.login_success.emit()
                    self.user_logged_in.emit(self.username)
                    self.clear_inputs()
                    self.hide()
                    return

            QMessageBox.warning(self, "登录失败", "用户名或密码错误，请重新输入。")

        except FileNotFoundError:
            QMessageBox.warning(self, "错误", "用户数据文件不存在，请先注册账号。")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"登录过程出错：{str(e)}")

    def clear_inputs(self):
        """清空输入框"""
        self.accEdit.clear()
        self.pwdEdit.clear()
        self.wdEdit.clear()

    def show_register(self):
        """显示注册界面"""
        self.clear_inputs()
        self.register_widget.show()
        self.hide()

    def show_login(self):
        """显示登录界面"""
        self.show()
        self.register_widget.hide()

    def hide_login(self):
        """隐藏登录界面"""
        self.hide()

    def generate(self):
        """生成新的验证码"""
        self.captcha_label.ui_init()
        self.current_captcha = self.captcha_label.text

    def print_current_captcha(self):
        """打印当前验证码（调试用）"""
        current_captcha = self.captcha_label.text
        print(f"当前验证码是: {current_captcha}")

    def quit(self):
        """退出程序"""
        reply = QMessageBox.question(
            self, "确认退出", "确定要退出游戏吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.close()