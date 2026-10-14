"""
浏览器管理模块
负责Playwright浏览器的启动、登录状态管理、页面访问
"""
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, Playwright
from typing import Optional
from pathlib import Path
import time


class BrowserManager:
    """
    浏览器管理器
    
    功能:
    1. 启动浏览器(非无头模式,方便用户手动登录)
    2. 保存登录状态到auth.json
    3. 加载登录状态
    4. 访问页面并获取HTML内容
    5. 自动滚动页面加载懒加载内容
    """
    
    def __init__(self, auth_file: str = "data/auth.json"):
        """
        初始化浏览器管理器
        
        参数:
            auth_file: 登录状态文件路径
        """
        self.auth_file = Path(auth_file)
        self.auth_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
    
    def start_browser(self, headless: bool = False) -> bool:
        """
        启动浏览器
        
        参数:
            headless: 是否使用无头模式
            
        返回:
            是否成功启动
        """
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=headless)
            self.context = self.browser.new_context()
            self.page = self.context.new_page()
            return True
        except Exception as e:
            import traceback
            error_msg = str(e)
            error_detail = traceback.format_exc()
            
            print(f"启动浏览器失败: {e}")
            print(f"详细错误:\n{error_detail}")
            
            # 检查是否是浏览器未安装
            if "Executable doesn't exist" in error_msg or "browser" in error_msg.lower():
                print("\n" + "="*60)
                print("错误: 未找到Playwright浏览器!")
                print("="*60)
                print("解决方法:")
                print("1. 打开命令提示符(CMD)")
                print("2. 运行以下命令安装浏览器:")
                print("   pip install playwright")
                print("   playwright install chromium")
                print("3. 安装完成后重新运行本程序")
                print("="*60)
            else:
                print("\n" + "="*60)
                print("启动浏览器时发生错误")
                print("="*60)
                print(f"错误类型: {type(e).__name__}")
                print(f"错误信息: {error_msg}")
                print("="*60)
            
            return False
    
    def open_ketangpai(self) -> bool:
        """
        打开课堂派首页
        
        返回:
            是否成功打开
        """
        if not self.page:
            return False
        
        try:
            self.page.goto("https://www.ketangpai.com/", wait_until="networkidle")
            return True
        except Exception as e:
            print(f"打开课堂派失败: {e}")
            return False
    
    def save_auth_state(self) -> bool:
        """
        保存登录状态到auth.json
        
        返回:
            是否成功保存
        """
        if not self.context:
            return False
        
        try:
            self.context.storage_state(path=str(self.auth_file))
            return True
        except Exception as e:
            print(f"保存登录状态失败: {e}")
            return False
    
    def has_auth_file(self) -> bool:
        """
        检查是否存在登录状态文件
        
        返回:
            是否存在
        """
        return self.auth_file.exists()
    
    def start_with_auth(self, headless: bool = False) -> bool:
        """
        使用保存的登录状态启动浏览器
        
        参数:
            headless: 是否使用无头模式
            
        返回:
            是否成功启动
        """
        if not self.has_auth_file():
            print("未找到登录状态文件")
            return False
        
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=headless)
            self.context = self.browser.new_context(storage_state=str(self.auth_file))
            self.page = self.context.new_page()
            return True
        except Exception as e:
            error_msg = str(e)
            print(f"使用登录状态启动浏览器失败: {e}")
            
            # 检查是否是浏览器未安装
            if "Executable doesn't exist" in error_msg or "browser" in error_msg.lower():
                print("\n" + "="*60)
                print("错误: 未找到Playwright浏览器!")
                print("="*60)
                print("解决方法:")
                print("1. 打开命令提示符(CMD)")
                print("2. 运行以下命令安装浏览器:")
                print("   pip install playwright")
                print("   playwright install chromium")
                print("3. 安装完成后重新运行本程序")
                print("="*60)
            
            return False
    
    def visit_page(self, url: str, auto_scroll: bool = True) -> Optional[str]:
        """
        访问页面并获取HTML内容
        
        参数:
            url: 页面URL
            auto_scroll: 是否自动滚动加载全部内容
            
        返回:
            HTML内容,失败返回None
        """
        if not self.page:
            return None
        
        try:
            # 访问页面
            self.page.goto(url, wait_until="networkidle", timeout=60000)
            
            # 等待页面加载
            time.sleep(2)
            
            # 自动滚动
            if auto_scroll:
                self._scroll_to_bottom()
            
            # 获取HTML
            html = self.page.content()
            return html
            
        except Exception as e:
            print(f"访问页面失败 {url}: {e}")
            return None
    
    def _scroll_to_bottom(self) -> None:
        """
        滚动页面到底部,加载懒加载内容
        """
        if not self.page:
            return
        
        try:
            # 获取页面高度
            page_height = self.page.evaluate("document.body.scrollHeight")
            viewport_height = self.page.evaluate("window.innerHeight")
            
            # 分段滚动
            current_position = 0
            scroll_step = viewport_height // 2
            
            while current_position < page_height:
                self.page.evaluate(f"window.scrollTo(0, {current_position})")
                time.sleep(0.3)
                current_position += scroll_step
                
                # 更新页面高度
                page_height = self.page.evaluate("document.body.scrollHeight")
            
            # 滚动到最底部
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)
            
        except Exception as e:
            print(f"滚动页面时出错: {e}")
    
    def close(self) -> None:
        """关闭浏览器"""
        try:
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        except Exception as e:
            print(f"关闭浏览器时出错: {e}")
        finally:
            self.page = None
            self.context = None
            self.browser = None
            self.playwright = None
