# -*- coding: utf-8 -*-
import sys
from PyQt5.QtWidgets import QApplication, QMessageBox

from gameWidget import GameWidget


class MainApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.current_user = None  # 保存当前登录用户名

        # 延迟导入，避免循环依赖
        from loginWidget import LoginWidget
        from chooseWidget import ChooseWidget
        from gameWidget import GameWidget
        from profileWidget import ProfileWidget

        # 初始化界面
        self.login_widget = LoginWidget()  # 登录界面
        self.choose_widget = ChooseWidget()  # 关卡选择界面
        self.game_widget = None  # 游戏界面（动态创建）
        self.profile_widget = ProfileWidget()  # 个人中心界面

        # 连接信号与槽
        self.login_widget.login_success.connect(self.show_choose)  # 登录→关卡选择
        self.login_widget.user_logged_in.connect(self.set_current_user)  # 接收用户名
        self.choose_widget.level_chosen.connect(self.start_game)  # 选关卡→启动游戏
        self.profile_widget.back_signal.connect(self.return_to_game)  # 个人中心→游戏

        # 启动时显示登录界面
        self.login_widget.show()

    def set_current_user(self, username):
        """设置当前登录用户"""
        self.current_user = username
        print(f"当前登录用户: {self.current_user}")  # 调试信息

    def show_choose(self):
        """显示关卡选择界面（核心：确保界面可见）"""
        # 隐藏其他界面，显示关卡选择
        if self.login_widget.isVisible():
            self.login_widget.hide()
        if self.game_widget and self.game_widget.isVisible():
            self.game_widget.hide()
        if self.profile_widget.isVisible():
            self.profile_widget.hide()
        self.choose_widget.show()  # 关键：强制显示关卡选择界面
        self.choose_widget.raise_()  # 确保界面置顶，避免被遮挡

    def start_game(self, level):
        """根据选择的关卡启动游戏（补充返回信号绑定）"""
        try:
            # 隐藏关卡选择界面
            if self.choose_widget.isVisible():
                self.choose_widget.hide()

            # 验证登录状态
            if not self.current_user:
                QMessageBox.warning(None, "错误", "未检测到登录用户，请重新登录")
                self.show_choose()
                return

            # 销毁旧游戏窗口（避免资源残留）
            if self.game_widget:
                self.game_widget.close()
                self.game_widget = None

            # 创建新游戏窗口
            self.game_widget = GameWidget(self.current_user, level)
            # 关键修复：绑定游戏窗口的返回信号到 show_choose（显示关卡选择）
            self.game_widget.back_to_choose_signal.connect(self.show_choose)
            # 绑定个人中心信号
            self.game_widget.show_profile_signal.connect(self.show_profile)

            # 显示游戏窗口
            self.game_widget.show()
            self.game_widget.raise_()
            print(f"已启动关卡 {level} 游戏界面")

        except Exception as e:
            QMessageBox.warning(None, "启动失败", f"游戏启动失败: {str(e)}")
            print(f"游戏启动错误: {e}")
            self.show_choose()  # 启动失败时返回关卡选择

    def show_profile(self, username):
        """显示个人中心"""
        if self.game_widget and self.game_widget.isVisible():
            self.game_widget.hide()
        self.profile_widget.set_user(username)
        self.profile_widget.load_records()
        self.profile_widget.show()
        self.profile_widget.raise_()

    def return_to_game(self):
        """从个人中心返回游戏"""
        self.profile_widget.hide()
        if self.game_widget:
            self.game_widget.show()
            self.game_widget.raise_()


if __name__ == '__main__':
    app = MainApp(sys.argv)
    sys.exit(app.exec_())