"""
课堂派登录状态保存工具
功能:打开浏览器,让用户手动登录,登录成功后保存登录状态到 auth.json
合规说明:不保存用户名和密码,只保存浏览器登录状态(cookies等)
"""
from playwright.sync_api import sync_playwright
import json
import os


def save_login_state() -> None:
    """
    打开课堂派网站,等待用户手动登录,保存登录状态
    
    步骤:
    1. 启动浏览器(非无头模式)
    2. 打开课堂派首页
    3. 等待用户在终端按Enter键(表示登录完成)
    4. 保存storage_state到auth.json
    """
    print("=" * 60)
    print("课堂派登录状态保存工具")
    print("=" * 60)
    print("\n使用说明:")
    print("1. 浏览器窗口即将打开")
    print("2. 请在浏览器中完成登录操作")
    print("3. 登录成功后,回到此终端按 Enter 键")
    print("4. 程序将保存登录状态到 auth.json 文件")
    print("\n注意: 不要保存用户名和密码到代码中!\n")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        print("正在打开课堂派网站...")
        page.goto("https://www.ketangpai.com/", wait_until="networkidle")
        
        print("\n✓ 浏览器已打开,请在浏览器中完成登录操作")
        print("✓ 登录成功后,回到此终端按 Enter 键继续...")
        
        input("\n按 Enter 键继续: ")
        
        auth_file = "auth.json"
        context.storage_state(path=auth_file)
        
        print(f"\n✓ 登录状态已保存到: {auth_file}")
        print("✓ 下次运行爬取脚本时将使用此登录状态,无需重新登录")
        
        browser.close()
    
    print("\n程序结束,可以运行 python crawl_questions.py 开始整理题目")


if __name__ == "__main__":
    save_login_state()
