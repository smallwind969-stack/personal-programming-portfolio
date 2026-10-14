"""
交互式页面选择工具
功能:打开浏览器让你手动浏览课堂派,选择要整理的测试/考试页面,保存到urls.txt
"""
from playwright.sync_api import sync_playwright
import os
import time


def select_pages_interactive() -> None:
    """
    交互式选择页面
    
    流程:
    1. 打开浏览器(使用已保存的登录状态)
    2. 用户在浏览器中浏览,找到想要的测试/考试页面
    3. 在终端输入当前页面URL来保存
    4. 可以添加多个页面
    5. 完成后保存到urls.txt
    """
    print("=" * 60)
    print("课堂派页面选择工具")
    print("=" * 60)
    
    # 检查登录状态
    if not os.path.exists("auth.json"):
        print("\n❌ 错误: 未找到 auth.json 文件")
        print("请先运行 python save_login.py 保存登录状态")
        return
    
    print("\n使用说明:")
    print("1. 浏览器窗口即将打开(已登录状态)")
    print("2. 在浏览器中浏览到您想整理的测试/考试/作业页面")
    print("3. 等待浏览器地址栏URL变化完成")
    print("4. 回到终端,按 Enter 键获取当前URL")
    print("5. 输入 'add' 添加当前页面到列表")
    print("6. 输入 'list' 查看已添加的页面")
    print("7. 输入 'remove [序号]' 移除指定页面")
    print("8. 输入 'done' 完成选择并保存到 urls.txt")
    print("9. 输入 'quit' 退出不保存\n")
    
    selected_urls: list = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state="auth.json")
        page = context.new_page()
        
        # 打开课堂派首页
        print("正在打开课堂派...")
        page.goto("https://www.ketangpai.com/", wait_until="networkidle")
        
        print("\n✓ 浏览器已打开,请在浏览器中浏览到想要整理的页面")
        print("✓ 然后回到终端输入命令\n")
        
        while True:
            try:
                # 显示提示
                print("-" * 60)
                print("提示: 请先在浏览器中导航到目标页面,等待URL变化后,再回到这里输入命令")
                
                # 等待用户确认已导航到目标页面
                input("\n按 Enter 键获取当前浏览器URL...")
                
                # 获取当前页面URL(等待一下确保SPA路由更新)
                time.sleep(0.5)  # 等待URL更新
                current_url = page.url
                
                print(f"\n当前浏览器URL: {current_url}")
                command = input("\n请输入命令 (add/list/remove/done/quit): ").strip().lower()
                
                if command == 'add':
                    # 添加当前页面
                    if current_url not in selected_urls:
                        selected_urls.append(current_url)
                        print(f"✓ 已添加: {current_url}")
                        print(f"✓ 当前已选择 {len(selected_urls)} 个页面")
                    else:
                        print("⚠ 该页面已在列表中")
                
                elif command == 'list':
                    # 显示已添加的页面
                    print("\n已选择的页面:")
                    if len(selected_urls) == 0:
                        print("  (无)")
                    else:
                        for idx, url in enumerate(selected_urls, start=1):
                            print(f"  [{idx}] {url}")
                
                elif command.startswith('remove'):
                    # 移除指定页面
                    parts = command.split()
                    if len(parts) < 2:
                        print("⚠ 用法: remove [序号]")
                        print("   示例: remove 1")
                    else:
                        try:
                            idx = int(parts[1])
                            if 1 <= idx <= len(selected_urls):
                                removed_url = selected_urls.pop(idx - 1)
                                print(f"✓ 已移除: {removed_url}")
                            else:
                                print(f"⚠ 序号无效,请输入 1-{len(selected_urls)} 之间的数字")
                        except ValueError:
                            print("⚠ 请输入有效的数字序号")
                
                elif command == 'done':
                    # 完成选择
                    if len(selected_urls) == 0:
                        print("⚠ 未选择任何页面,请先添加页面")
                        continue
                    
                    # 保存到urls.txt
                    print("\n正在保存到 urls.txt...")
                    with open("urls.txt", "w", encoding="utf-8") as f:
                        f.write("# 课堂派页面链接配置文件\n")
                        f.write("# 由交互式选择工具自动生成\n")
                        f.write("#\n")
                        for url in selected_urls:
                            f.write(f"{url}\n")
                    
                    print(f"✓ 已保存 {len(selected_urls)} 个页面到 urls.txt")
                    print("✓ 可以运行 python crawl_questions.py 开始整理题目")
                    break
                
                elif command == 'quit':
                    # 退出不保存
                    print("已退出,未保存更改")
                    break
                
                else:
                    print("⚠ 未知命令,可用命令: add, list, remove [序号], done, quit")
            
            except KeyboardInterrupt:
                print("\n\n已中断,未保存更改")
                break
            except Exception as e:
                print(f"错误: {e}")
        
        browser.close()
    
    print("\n程序结束")


if __name__ == "__main__":
    select_pages_interactive()
