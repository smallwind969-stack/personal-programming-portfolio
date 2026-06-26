# -*- coding: utf-8 -*-
# @Time    : 2025/5/14 16:00
# @Author  : 小宇
# @File    : main.py
import sys
from PyQt5.QtWidgets import QApplication
from view.MainWidget import MainWidget

if __name__ == '__main__':
    # 1.创建应用
    app = QApplication(sys.argv)
    # 2.创建页面
    mainwin = MainWidget()
    # 3.设置大小
    # widget.resize(500, 500)
    # 4.设置标题
    # widget.setWindowTitle('Hello PyQT')
    # 5.显示出来
    mainwin.show()
    # 6.持续显示界面，直到APP点关闭退出
    sys.exit(app.exec_())