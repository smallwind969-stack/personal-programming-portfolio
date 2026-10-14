"""
课堂派题目整理工具 - 主程序入口
合规的本地桌面软件,用于整理学生账号在课堂派中已授权访问的题目信息
"""
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont


def main():
    """
    主函数
    启动GUI应用程序
    """
    # 创建应用
    app = QApplication(sys.argv)
    
    # 设置应用信息
    app.setApplicationName("课堂派题目整理工具")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Ketangpai Question Tool")
    
    # 设置默认字体
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)
    
    # 设置样式
    app.setStyle("Fusion")
    
    # 创建必要目录
    Path("data").mkdir(exist_ok=True)
    Path("output").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)
    
    # 导入并创建主窗口
    from ui_main import MainWindow
    window = MainWindow()
    
    # 显示窗口
    window.show()
    
    # 运行应用
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
