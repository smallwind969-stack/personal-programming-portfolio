# -*- coding: utf-8 -*-
# @Time    : 2025/6/16
# @Author  : 小宇
# @File    : main(gongdi).py


# main.py
import sys
from PyQt5.QtWidgets import QApplication
from page.loginwidget import LoginWidget

def main():
    """主程序入口"""
    try:
        # 禁用硬件加速，解决Windows系统崩溃问题
        import os
        os.environ["QT_QUICK_BACKEND"] = "software"
        os.environ["QT_XCB_GL_INTEGRATION"] = "none"
        os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

        print("启动智能座舱系统...")
        app = QApplication(sys.argv)
        app.setStyle("Fusion")  # 使用Fusion样式避免系统样式问题

        # 数据库配置
        db_config = {
            'host': 'localhost',
            'user': 'root',
            'password': os.getenv('MYSQL_PASSWORD', ''),
            'database': 'ai250317',
            'port': 3306,
            'charset': 'utf8mb4'
        }

        # 创建登录窗口
        login_window = LoginWidget(db_config)
        login_window.show()

        sys.exit(app.exec_())

    except Exception as e:
        print(f"程序异常: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
