"""
一键打包脚本
自动将程序打包成可执行文件
"""
import os
import sys
import subprocess
from pathlib import Path


def main():
    print("=" * 60)
    print("课堂派题目整理工具 - 自动打包")
    print("=" * 60)
    print()
    
    # 步骤1：检查并安装PyInstaller
    print("[1/3] 检查PyInstaller...")
    try:
        import PyInstaller
        print("✓ PyInstaller已安装")
    except ImportError:
        print("正在安装PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        print("✓ PyInstaller安装完成")
    
    print()
    
    # 步骤2：打包
    print("[2/3] 开始打包...")
    print("这可能需要几分钟，请耐心等待...")
    print()
    
    # PyInstaller命令
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",           # 打包成单个文件
        "--windowed",          # 窗口模式（无控制台）
        "--name", "课堂派题目整理工具",  # 可执行文件名
        "--clean",             # 清理临时文件
        "main.py"              # 入口文件
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print()
        print("✓ 打包成功！")
    except subprocess.CalledProcessError as e:
        print(f"❌ 打包失败: {e}")
        print("\n请尝试手动安装依赖后重新打包：")
        print("pip install pyinstaller")
        print("pyinstaller --onefile --windowed --name \"课堂派题目整理工具\" main.py")
        input("\n按回车键退出...")
        return
    
    print()
    
    # 步骤3：完成
    print("[3/3] 打包完成！")
    print()
    
    # 检查输出文件
    exe_path = Path("dist") / "课堂派题目整理工具.exe"
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"✓ 生成的文件: {exe_path.absolute()}")
        print(f"✓ 文件大小: {size_mb:.2f} MB")
        print()
        print("使用说明:")
        print("1. 将 '课堂派题目整理工具.exe' 复制到任意目录")
        print("2. 双击运行即可")
        print("3. 首次运行前需要安装Playwright浏览器:")
        print("   pip install playwright")
        print("   playwright install chromium")
    else:
        print(f"⚠ 未找到生成的EXE文件，请检查dist目录")
    
    print()
    input("按回车键退出...")


if __name__ == "__main__":
    main()
