"""
主窗口界面
使用PySide6实现专业的桌面GUI
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QPushButton, QTextEdit,
    QLineEdit, QCheckBox, QRadioButton, QButtonGroup,
    QProgressBar, QFileDialog, QMessageBox, QSplitter,
    QFrame, QScrollArea
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QTextCursor
from typing import List, Optional
from pathlib import Path
import time
import random

from browser_manager import BrowserManager
from question_parser import parse_questions
from exporter import Exporter
from models import Question


class CrawlWorker(QThread):
    """
    整理任务工作线程
    
    避免阻塞GUI主线程
    """
    
    # 信号定义
    log_signal = Signal(str)  # 日志信号
    progress_signal = Signal(int, int)  # 进度信号(当前,总数)
    finished_signal = Signal(bool, str, int)  # 完成信号(成功,输出路径,题目数量)
    error_signal = Signal(str)  # 错误信号
    
    def __init__(self, urls: List[str], 
                 auth_file: str,
                 excel_path: str,
                 word_path: str,
                 export_excel: bool,
                 export_word: bool,
                 interval: int,
                 auto_scroll: bool,
                 include_raw_text: bool):
        super().__init__()
        
        self.urls = urls
        self.auth_file = auth_file
        self.excel_path = excel_path
        self.word_path = word_path
        self.export_excel = export_excel
        self.export_word = export_word
        self.interval = interval
        self.auto_scroll = auto_scroll
        self.include_raw_text = include_raw_text
        
        self.is_running = True
        self.browser_manager: Optional[BrowserManager] = None
    
    def run(self):
        """执行整理任务"""
        try:
            self.log_signal.emit("正在启动浏览器...")
            
            # 启动浏览器(使用登录状态)
            self.browser_manager = BrowserManager(self.auth_file)
            if not self.browser_manager.start_with_auth(headless=False):
                self.error_signal.emit("无法启动浏览器,请检查登录状态")
                return
            
            all_questions: List[Question] = []
            
            # 处理每个URL
            for idx, url in enumerate(self.urls, start=1):
                if not self.is_running:
                    self.log_signal.emit("任务已停止")
                    break
                
                self.log_signal.emit(f"\n[{idx}/{len(self.urls)}] 正在处理: {url}")
                self.progress_signal.emit(idx, len(self.urls))
                
                try:
                    # 访问页面
                    html = self.browser_manager.visit_page(url, self.auto_scroll)
                    
                    if not html:
                        self.log_signal.emit(f"  ❌ 无法访问页面")
                        continue
                    
                    # 保存HTML用于调试
                    debug_file = Path("output") / f"debug_page_{idx}.html"
                    debug_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(html)
                    self.log_signal.emit(f"  已保存HTML到: {debug_file}")
                    
                    # 解析题目
                    self.log_signal.emit("  正在解析题目...")
                    questions = parse_questions(html, url)
                    
                    self.log_signal.emit(f"  ✓ 提取到 {len(questions)} 条题目")
                    all_questions.extend(questions)
                    
                except Exception as e:
                    self.log_signal.emit(f"  ❌ 处理失败: {e}")
                    continue
                
                # 页面间延迟
                if idx < len(self.urls) and self.is_running:
                    delay = random.uniform(self.interval - 1, self.interval + 1)
                    self.log_signal.emit(f"  等待 {delay:.1f} 秒...")
                    time.sleep(delay)
            
            # 关闭浏览器
            if self.browser_manager:
                self.browser_manager.close()
            
            if not self.is_running or len(all_questions) == 0:
                if len(all_questions) == 0:
                    self.finished_signal.emit(False, "", 0)
                return
            
            # 导出文件
            success = False
            output_path = ""
            
            if self.export_excel and self.excel_path:
                self.log_signal.emit(f"\n正在导出Excel: {self.excel_path}")
                if Exporter.export_to_excel(all_questions, self.excel_path, self.include_raw_text):
                    self.log_signal.emit(f"✓ Excel导出成功")
                    success = True
                    output_path = self.excel_path
                else:
                    self.log_signal.emit(f"❌ Excel导出失败")
            
            if self.export_word and self.word_path:
                self.log_signal.emit(f"\n正在导出Word: {self.word_path}")
                if Exporter.export_to_word(all_questions, self.word_path):
                    self.log_signal.emit(f"✓ Word导出成功")
                    success = True
                    output_path = self.word_path
                else:
                    self.log_signal.emit(f"❌ Word导出失败")
            
            # 完成
            total_count = len(all_questions)
            self.log_signal.emit(f"\n✓ 整理完成! 共提取到 {total_count} 条题目")
            self.finished_signal.emit(success, output_path, total_count)
            
        except Exception as e:
            self.error_signal.emit(f"整理过程出错: {e}")
            if self.browser_manager:
                self.browser_manager.close()
    
    def stop(self):
        """停止任务"""
        self.is_running = False


class MainWindow(QMainWindow):
    """
    主窗口
    
    布局:
    - 左侧: 操作步骤区域
    - 右侧: 配置和日志区域
    """
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("课堂派题目整理工具")
        self.setMinimumSize(1000, 700)
        
        # 浏览器管理器
        self.browser_manager: Optional[BrowserManager] = None
        
        # 工作线程
        self.worker: Optional[CrawlWorker] = None
        
        # 创建界面
        self._create_ui()
        
        # 检查登录状态
        self._check_auth_status()
    
    def _create_ui(self):
        """创建界面"""
        # 主部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局(水平分割器)
        main_layout = QHBoxLayout(central_widget)
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧面板
        left_panel = self._create_left_panel()
        splitter.addWidget(left_panel)
        
        # 右侧面板
        right_panel = self._create_right_panel()
        splitter.addWidget(right_panel)
        
        # 设置分割器比例
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        main_layout.addWidget(splitter)
    
    def _create_left_panel(self) -> QWidget:
        """创建左侧面板(操作步骤)"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 标题
        title = QLabel("操作步骤")
        title.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 步骤1: 登录
        login_group = QGroupBox("步骤1: 登录")
        login_layout = QVBoxLayout(login_group)
        
        self.btn_open_browser = QPushButton("打开课堂派并登录")
        self.btn_open_browser.setMinimumHeight(40)
        self.btn_open_browser.clicked.connect(self._on_open_browser)
        login_layout.addWidget(self.btn_open_browser)
        
        self.btn_save_auth = QPushButton("保存当前登录状态")
        self.btn_save_auth.setMinimumHeight(40)
        self.btn_save_auth.setEnabled(False)
        self.btn_save_auth.clicked.connect(self._on_save_auth)
        login_layout.addWidget(self.btn_save_auth)
        
        self.lbl_auth_status = QLabel("状态: 未登录")
        self.lbl_auth_status.setStyleSheet("color: #666;")
        login_layout.addWidget(self.lbl_auth_status)
        
        tip1 = QLabel("提示: 在浏览器中手动登录后\n点击保存登录状态")
        tip1.setStyleSheet("color: #999; font-size: 11px;")
        login_layout.addWidget(tip1)
        
        layout.addWidget(login_group)
        
        # 步骤2: 添加链接
        urls_group = QGroupBox("步骤2: 添加页面链接")
        urls_layout = QVBoxLayout(urls_group)
        
        self.txt_urls = QTextEdit()
        self.txt_urls.setPlaceholderText("每行一个页面URL...")
        urls_layout.addWidget(self.txt_urls)
        
        btn_layout = QHBoxLayout()
        self.btn_import_urls = QPushButton("从txt导入")
        self.btn_import_urls.clicked.connect(self._on_import_urls)
        btn_layout.addWidget(self.btn_import_urls)
        
        self.btn_save_urls = QPushButton("保存到txt")
        self.btn_save_urls.clicked.connect(self._on_save_urls)
        btn_layout.addWidget(self.btn_save_urls)
        
        self.btn_clear_urls = QPushButton("清空")
        self.btn_clear_urls.clicked.connect(self._on_clear_urls)
        btn_layout.addWidget(self.btn_clear_urls)
        
        urls_layout.addLayout(btn_layout)
        
        self.lbl_url_count = QLabel("当前链接数: 0")
        self.lbl_url_count.setStyleSheet("color: #666;")
        urls_layout.addWidget(self.lbl_url_count)
        
        layout.addWidget(urls_group)
        
        # 步骤3: 开始整理
        action_group = QGroupBox("步骤3: 开始整理")
        action_layout = QVBoxLayout(action_group)
        
        self.btn_start = QPushButton("开始整理")
        self.btn_start.setMinimumHeight(50)
        self.btn_start.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.btn_start.clicked.connect(self._on_start)
        action_layout.addWidget(self.btn_start)
        
        self.btn_stop = QPushButton("停止")
        self.btn_stop.setMinimumHeight(40)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._on_stop)
        action_layout.addWidget(self.btn_stop)
        
        layout.addWidget(action_group)
        
        layout.addStretch()
        
        return panel
    
    def _create_right_panel(self) -> QWidget:
        """创建右侧面板(配置和日志)"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 配置区域
        config_group = QGroupBox("导出设置")
        config_layout = QVBoxLayout(config_group)
        
        # 导出格式
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("导出格式:"))
        
        self.chk_excel = QCheckBox("Excel")
        self.chk_excel.setChecked(True)
        format_layout.addWidget(self.chk_excel)
        
        self.chk_word = QCheckBox("Word")
        self.chk_word.setChecked(False)
        format_layout.addWidget(self.chk_word)
        
        format_layout.addStretch()
        config_layout.addLayout(format_layout)
        
        # 提示
        tip_label = QLabel("提示: 点击\"开始整理\"后会弹出文件保存对话框")
        tip_label.setStyleSheet("color: #666; font-size: 11px;")
        config_layout.addWidget(tip_label)
        
        # 其他设置
        settings_layout = QHBoxLayout()
        settings_layout.addWidget(QLabel("页面间隔(秒):"))
        
        self.txt_interval = QLineEdit("3")
        self.txt_interval.setMaximumWidth(50)
        settings_layout.addWidget(self.txt_interval)
        
        settings_layout.addStretch()
        config_layout.addLayout(settings_layout)
        
        # 勾选项
        self.chk_auto_scroll = QCheckBox("自动滚动页面加载全部内容")
        self.chk_auto_scroll.setChecked(True)
        config_layout.addWidget(self.chk_auto_scroll)
        
        self.chk_include_raw = QCheckBox("导出raw_text方便校对")
        self.chk_include_raw.setChecked(True)
        config_layout.addWidget(self.chk_include_raw)
        
        layout.addWidget(config_group)
        
        # 进度条
        progress_group = QGroupBox("进度")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        self.lbl_progress = QLabel("就绪")
        progress_layout.addWidget(self.lbl_progress)
        
        layout.addWidget(progress_group)
        
        # 日志区域
        log_group = QGroupBox("日志输出")
        log_layout = QVBoxLayout(log_group)
        
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setStyleSheet("font-family: Consolas, 'Courier New', monospace;")
        log_layout.addWidget(self.txt_log)
        
        btn_clear_log = QPushButton("清空日志")
        btn_clear_log.clicked.connect(lambda: self.txt_log.clear())
        log_layout.addWidget(btn_clear_log)
        
        layout.addWidget(log_group)
        
        return panel
    
    def _check_auth_status(self):
        """检查登录状态"""
        auth_file = Path("data/auth.json")
        if auth_file.exists():
            self.lbl_auth_status.setText("状态: 已检测到登录状态文件")
            self.lbl_auth_status.setStyleSheet("color: green;")
        else:
            self.lbl_auth_status.setText("状态: 未登录")
            self.lbl_auth_status.setStyleSheet("color: #666;")
    
    def _on_open_browser(self):
        """打开浏览器"""
        try:
            self._add_log("正在打开浏览器...")
            
            self.browser_manager = BrowserManager()
            if self.browser_manager.start_browser(headless=False):
                if self.browser_manager.open_ketangpai():
                    self._add_log("✓ 浏览器已打开,请在浏览器中手动登录")
                    self.btn_save_auth.setEnabled(True)
                    self.btn_open_browser.setEnabled(False)
                else:
                    self._add_log("❌ 无法打开课堂派")
            else:
                self._add_log("❌ 无法启动浏览器")
                
        except Exception as e:
            self._add_log(f"❌ 错误: {e}")
    
    def _on_save_auth(self):
        """保存登录状态"""
        if not self.browser_manager:
            return
        
        try:
            self._add_log("正在保存登录状态...")
            
            if self.browser_manager.save_auth_state():
                self._add_log("✓ 登录状态已保存到 data/auth.json")
                self.lbl_auth_status.setText("状态: 已保存登录状态")
                self.lbl_auth_status.setStyleSheet("color: green; font-weight: bold;")
                self.btn_save_auth.setEnabled(False)
                
                # 关闭浏览器
                self.browser_manager.close()
                self.browser_manager = None
                self.btn_open_browser.setEnabled(True)
            else:
                self._add_log("❌ 保存登录状态失败")
                
        except Exception as e:
            self._add_log(f"❌ 错误: {e}")
    
    def _on_import_urls(self):
        """从txt导入链接"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择文件", "", "文本文件 (*.txt)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.txt_urls.setPlainText(content)
                self._update_url_count()
                self._add_log(f"✓ 已导入链接: {file_path}")
            except Exception as e:
                self._add_log(f"❌ 导入失败: {e}")
    
    def _on_save_urls(self):
        """保存链接到txt"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存文件", "", "文本文件 (*.txt)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.txt_urls.toPlainText())
                self._add_log(f"✓ 已保存链接: {file_path}")
            except Exception as e:
                self._add_log(f"❌ 保存失败: {e}")
    
    def _on_clear_urls(self):
        """清空链接"""
        self.txt_urls.clear()
        self._update_url_count()
    
    def _update_url_count(self):
        """更新链接数量"""
        urls = self._get_urls()
        self.lbl_url_count.setText(f"当前链接数: {len(urls)}")
    
    def _get_urls(self) -> List[str]:
        """获取URL列表"""
        content = self.txt_urls.toPlainText()
        urls = []
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                urls.append(line)
        return urls
    
    def _on_start(self):
        """开始整理"""
        # 检查条件
        auth_file = Path("data/auth.json")
        if not auth_file.exists():
            QMessageBox.warning(self, "警告", "未找到登录状态文件,请先登录")
            return
        
        urls = self._get_urls()
        if len(urls) == 0:
            QMessageBox.warning(self, "警告", "请至少添加一个页面链接")
            return
        
        if not self.chk_excel.isChecked() and not self.chk_word.isChecked():
            QMessageBox.warning(self, "警告", "请选择至少一种导出格式")
            return
        
        # 让用户选择保存路径
        export_excel = self.chk_excel.isChecked()
        export_word = self.chk_word.isChecked()
        
        excel_path = ""
        word_path = ""
        
        # 选择Excel保存路径
        if export_excel:
            excel_path, _ = QFileDialog.getSaveFileName(
                self, 
                "保存Excel文件", 
                str(Path.cwd() / "output" / "questions.xlsx"),
                "Excel文件 (*.xlsx)"
            )
            if not excel_path:
                return  # 用户取消
            if not excel_path.endswith('.xlsx'):
                excel_path += '.xlsx'
        
        # 选择Word保存路径
        if export_word:
            word_path, _ = QFileDialog.getSaveFileName(
                self, 
                "保存Word文件", 
                str(Path.cwd() / "output" / "questions.docx"),
                "Word文件 (*.docx)"
            )
            if not word_path:
                return  # 用户取消
            if not word_path.endswith('.docx'):
                word_path += '.docx'
        
        # 获取设置
        try:
            interval = int(self.txt_interval.text())
        except ValueError:
            interval = 3
        
        auto_scroll = self.chk_auto_scroll.isChecked()
        include_raw = self.chk_include_raw.isChecked()
        
        # 创建工作线程
        self.worker = CrawlWorker(
            urls=urls,
            auth_file="data/auth.json",
            excel_path=excel_path,
            word_path=word_path,
            export_excel=export_excel,
            export_word=export_word,
            interval=interval,
            auto_scroll=auto_scroll,
            include_raw_text=include_raw
        )
        
        # 连接信号
        self.worker.log_signal.connect(self._add_log)
        self.worker.progress_signal.connect(self._update_progress)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.error_signal.connect(self._on_error)
        
        # 更新UI状态
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.progress_bar.setValue(0)
        
        # 启动线程
        self.worker.start()
        self._add_log("✓ 开始整理任务...")
    
    def _on_stop(self):
        """停止整理"""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self._add_log("正在停止任务...")
    
    def _update_progress(self, current: int, total: int):
        """更新进度"""
        progress = int((current / total) * 100)
        self.progress_bar.setValue(progress)
        self.lbl_progress.setText(f"处理中: {current}/{total}")
    
    def _on_finished(self, success: bool, output_path: str, count: int):
        """任务完成"""
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        
        if success:
            self.progress_bar.setValue(100)
            self.lbl_progress.setText("完成")
            
            # 弹窗提示
            msg = f"整理完成!\n\n共提取到 {count} 条题目\n保存位置: {output_path}"
            QMessageBox.information(self, "完成", msg)
        else:
            self.lbl_progress.setText("失败")
    
    def _on_error(self, error_msg: str):
        """错误处理"""
        self._add_log(f"❌ {error_msg}")
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        QMessageBox.critical(self, "错误", error_msg)
    
    def _add_log(self, message: str):
        """添加日志"""
        timestamp = time.strftime("%H:%M:%S")
        self.txt_log.append(f"[{timestamp}] {message}")
        
        # 滚动到底部
        cursor = self.txt_log.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.txt_log.setTextCursor(cursor)
    
    def closeEvent(self, event):
        """关闭窗口事件"""
        # 停止工作线程
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        
        # 关闭浏览器
        if self.browser_manager:
            self.browser_manager.close()
        
        event.accept()
