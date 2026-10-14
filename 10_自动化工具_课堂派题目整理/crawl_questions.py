"""
课堂派题目信息整理工具
功能:读取urls.txt中的页面链接,使用保存的登录状态访问页面,提取题目信息并保存为Excel
合规说明:
1. 只访问用户本人账号有权限查看的页面
2. 不绕过任何验证机制
3. 不高频请求,每个页面间有延迟
4. 不尝试获取隐藏或加密的答案
5. 不扫描未授权资源
"""
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from bs4 import BeautifulSoup, Tag
from typing import List, Dict, Optional, Tuple
import pandas as pd
import time
import random
import os
from datetime import datetime


# ============================================================================
# CSS选择器配置区域
# 说明: 如果课堂派页面结构变化,可以在浏览器中"检查元素"后修改这些选择器
# ============================================================================

# 候选题目容器选择器(按优先级排序)
QUESTION_CONTAINER_SELECTORS = [
    ".question-item",
    ".question",
    ".exam-question",
    ".topic-item",
    ".work-question",
    "[class*='question']",
    "[class*='Question']",
    "[class*='topic']",
    "[class*='Topic']",
    "[class*='problem']",
    "[class*='Problem']",
    ".item",
    ".list-item",
]

# 题干选择器
QUESTION_TEXT_SELECTORS = [
    ".question-text",
    ".question-title",
    ".question-content",
    ".stem",
    ".title",
    "[class*='stem']",
    "[class*='title']",
    "h3",
    "h4",
]

# 选项容器选择器
OPTIONS_CONTAINER_SELECTORS = [
    ".options",
    ".question-options",
    ".option-list",
    ".choices",
    "[class*='option']",
    "ul",
    "ol",
]

# 选项项选择器
OPTION_ITEM_SELECTORS = [
    ".option",
    ".option-item",
    "li",
    "[class*='choice']",
]

# 题型标记选择器
QUESTION_TYPE_SELECTORS = [
    ".question-type",
    ".type",
    "[class*='type']",
    "span.tag",
]

# 答案显示选择器(只提取页面正常显示的答案)
ANSWER_SELECTORS = [
    ".answer",
    ".correct-answer",
    ".question-answer",
    "[class*='answer']",
]


# ============================================================================
# 解析函数
# ============================================================================

def parse_questions(html: str, page_url: str) -> List[Dict[str, str]]:
    """
    解析HTML页面,提取题目信息
    
    参数:
        html: 页面HTML内容
        page_url: 页面URL,用于记录来源
        
    返回:
        题目列表,每个题目包含以下字段:
        - source_url: 来源页面
        - question_index: 题目序号
        - question_type: 题型
        - question_text: 题干
        - options: 选项(多行分隔)
        - visible_answer: 可见答案
        - raw_text: 原始文本
        
    说明:
        如果课堂派页面结构变化,可以:
        1. 在浏览器中打开页面
        2. 右键点击题目 -> 检查
        3. 查看题目的class名称
        4. 修改上方QUESTION_CONTAINER_SELECTORS等选择器列表
    """
    soup = BeautifulSoup(html, 'lxml')
    questions: List[Dict[str, str]] = []
    
    # 尝试多个题目容器选择器
    question_elements: List[Tag] = []
    selected_selector: Optional[str] = None
    
    for selector in QUESTION_CONTAINER_SELECTORS:
        try:
            elements = soup.select(selector)
            if len(elements) > 0:
                # 选择匹配数量较合理的选择器(通常一个页面不会超过100题,也不会只有1题)
                # 如果找到5个以上元素,说明可能选对了
                if len(elements) >= 3:
                    question_elements = elements
                    selected_selector = selector
                    print(f"  使用选择器 '{selector}' 找到 {len(elements)} 个题目块")
                    break
        except Exception as e:
            continue
    
    # 如果没有找到明确的题目块,启用fallback方案
    if len(question_elements) == 0:
        print("  未找到明确的题目块,启用fallback方案...")
        question_elements = fallback_extract(soup)
        selected_selector = "fallback"
    
    # 解析每个题目块
    for idx, elem in enumerate(question_elements, start=1):
        try:
            question_data = parse_single_question(elem, idx, page_url)
            if question_data and question_data.get('question_text'):
                questions.append(question_data)
        except Exception as e:
            # 单个题目解析失败不影响其他题目
            continue
    
    return questions


def fallback_extract(soup: BeautifulSoup) -> List[Tag]:
    """
    Fallback方案:当找不到明确题目块时,尝试提取较长的文本块
    
    说明:
        过滤导航栏、按钮、页脚等明显无关内容
        保存较大块的文本,方便后续人工调整选择器
    """
    fallback_elements: List[Tag] = []
    
    # 尝试提取div、li、section等块级元素
    for tag_name in ['div', 'li', 'section', 'article']:
        elements = soup.find_all(tag_name)
        for elem in elements:
            # 获取文本内容
            text = elem.get_text(strip=True)
            text_length = len(text)
            
            # 过滤条件:
            # 1. 文本长度在20-2000字符之间(太短可能不是题目,太长可能是整个页面)
            # 2. 不包含导航、页脚、按钮等关键词
            # 3. 包含问号或句号(可能是题目)
            if 50 < text_length < 2000:
                class_attr = ' '.join(elem.get('class', []))
                id_attr = elem.get('id', '')
                
                # 排除导航、页脚、按钮等
                exclude_keywords = ['nav', 'footer', 'header', 'menu', 'btn', 'button', 
                                    'sidebar', 'comment', 'ads', 'advertisement']
                if not any(kw in class_attr.lower() or kw in id_attr.lower() for kw in exclude_keywords):
                    # 检查是否包含题目特征
                    if '？' in text or '?' in text or '。' in text:
                        fallback_elements.append(elem)
    
    print(f"  Fallback方案找到 {len(fallback_elements)} 个候选文本块")
    return fallback_elements[:50]  # 限制数量,避免过多


def parse_single_question(elem: Tag, index: int, page_url: str) -> Optional[Dict[str, str]]:
    """
    解析单个题目块
    
    参数:
        elem: 题目HTML元素
        index: 题目序号
        page_url: 页面URL
        
    返回:
        题目信息字典,如果解析失败返回None
    """
    result: Dict[str, str] = {
        'source_url': page_url,
        'question_index': str(index),
        'question_type': '',
        'question_text': '',
        'options': '',
        'visible_answer': '',
        'raw_text': ''
    }
    
    # 提取原始文本
    raw_text = elem.get_text(separator='\n', strip=True)
    result['raw_text'] = raw_text[:500]  # 限制长度
    
    # 提取题型
    for selector in QUESTION_TYPE_SELECTORS:
        type_elem = elem.select_one(selector)
        if type_elem:
            type_text = type_elem.get_text(strip=True)
            if type_text:
                result['question_type'] = type_text
                break
    
    # 如果没找到题型,尝试从文本中识别
    if not result['question_type']:
        result['question_type'] = detect_question_type(raw_text)
    
    # 提取题干
    question_text = ''
    for selector in QUESTION_TEXT_SELECTORS:
        text_elem = elem.select_one(selector)
        if text_elem:
            question_text = text_elem.get_text(strip=True)
            if question_text:
                break
    
    # 如果没找到题干,尝试提取第一段文本
    if not question_text:
        # 获取所有文本行,取第一行较长的文本作为题干
        lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
        for line in lines:
            if len(line) > 10:  # 题干通常较长
                question_text = line
                break
    
    result['question_text'] = question_text[:300]  # 限制长度
    
    # 提取选项
    options: List[str] = []
    for container_selector in OPTIONS_CONTAINER_SELECTORS:
        options_container = elem.select_one(container_selector)
        if options_container:
            for item_selector in OPTION_ITEM_SELECTORS:
                option_items = options_container.select(item_selector)
                if len(option_items) > 0:
                    for item in option_items:
                        opt_text = item.get_text(strip=True)
                        if opt_text and len(opt_text) > 1:
                            options.append(opt_text)
                    if len(options) > 0:
                        break
            if len(options) > 0:
                break
    
    result['options'] = '\n'.join(options)
    
    # 提取可见答案(只提取页面正常显示的答案,不尝试破解)
    for selector in ANSWER_SELECTORS:
        answer_elem = elem.select_one(selector)
        if answer_elem:
            answer_text = answer_elem.get_text(strip=True)
            if answer_text:
                result['visible_answer'] = answer_text
                break
    
    return result


def detect_question_type(text: str) -> str:
    """
    从文本中识别题型
    
    参数:
        text: 题目文本
        
    返回:
        题型字符串
    """
    text_lower = text.lower()
    
    if '单选' in text or '单项选择' in text:
        return '单选题'
    elif '多选' in text or '多项选择' in text:
        return '多选题'
    elif '判断' in text:
        return '判断题'
    elif '填空' in text:
        return '填空题'
    elif '简答' in text or '问答' in text:
        return '简答题'
    elif '计算' in text:
        return '计算题'
    elif '论述' in text:
        return '论述题'
    
    return ''


# ============================================================================
# 浏览器操作函数
# ============================================================================

def scroll_to_bottom(page: Page) -> None:
    """
    滚动页面到底部,加载懒加载内容
    
    参数:
        page: Playwright页面对象
    """
    try:
        # 获取页面高度
        page_height = page.evaluate("document.body.scrollHeight")
        viewport_height = page.evaluate("window.innerHeight")
        
        # 分段滚动
        current_position = 0
        scroll_step = viewport_height // 2
        
        while current_position < page_height:
            page.evaluate(f"window.scrollTo(0, {current_position})")
            time.sleep(0.5)  # 等待加载
            current_position += scroll_step
            
            # 更新页面高度(可能因为加载了新内容而改变)
            page_height = page.evaluate("document.body.scrollHeight")
        
        # 滚动到最底部
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)
        
    except Exception as e:
        print(f"  滚动页面时出错: {e}")


# ============================================================================
# 主函数
# ============================================================================

def main() -> None:
    """
    主函数:读取urls.txt,访问页面,提取题目,保存Excel
    """
    print("=" * 60)
    print("课堂派题目信息整理工具")
    print("=" * 60)
    
    # 检查必要文件
    if not os.path.exists("auth.json"):
        print("\n❌ 错误: 未找到 auth.json 文件")
        print("请先运行 python save_login.py 保存登录状态")
        return
    
    if not os.path.exists("urls.txt"):
        print("\n❌ 错误: 未找到 urls.txt 文件")
        print("请在 urls.txt 中填写要访问的页面链接,每行一个URL")
        return
    
    # 读取URL列表,过滤注释行(以#开头)和空行
    with open("urls.txt", "r", encoding="utf-8") as f:
        urls = []
        for line in f:
            line = line.strip()
            # 过滤空行和注释行
            if line and not line.startswith('#'):
                urls.append(line)
    
    if len(urls) == 0:
        print("\n❌ 错误: urls.txt 文件为空或只有注释")
        print("请在 urls.txt 中填写有效的页面链接(以#开头的行将被忽略)")
        return
    
    print(f"\n✓ 读取到 {len(urls)} 个URL")
    print(f"✓ 登录状态: auth.json")
    
    # 创建输出目录
    os.makedirs("output", exist_ok=True)
    
    # 错误日志
    error_log_path = "output/errors.log"
    error_messages: List[str] = []
    
    # 所有题目
    all_questions: List[Dict[str, str]] = []
    
    # 开始处理
    print("\n开始处理页面...")
    print("-" * 60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        
        # 使用保存的登录状态
        context = browser.new_context(storage_state="auth.json")
        page = context.new_page()
        
        for idx, url in enumerate(urls, start=1):
            print(f"\n[{idx}/{len(urls)}] 正在处理: {url}")
            
            try:
                # 访问页面
                page.goto(url, wait_until="networkidle", timeout=60000)
                
                # 等待页面加载
                time.sleep(2)
                
                # 滚动到底部,加载懒加载内容
                print("  正在滚动页面加载内容...")
                scroll_to_bottom(page)
                
                # 获取HTML
                html = page.content()
                
                # 解析题目
                print("  正在解析题目...")
                questions = parse_questions(html, url)
                
                print(f"  ✓ 提取到 {len(questions)} 条题目")
                all_questions.extend(questions)
                
            except Exception as e:
                error_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] URL: {url}\n错误: {str(e)}\n"
                error_messages.append(error_msg)
                print(f"  ❌ 处理失败: {e}")
                
                # 页面失败不终止,继续下一个
                continue
            
            # 页面间延迟(2-5秒)
            if idx < len(urls):
                delay = random.uniform(2, 5)
                print(f"  等待 {delay:.1f} 秒后处理下一个页面...")
                time.sleep(delay)
        
        browser.close()
    
    print("\n" + "=" * 60)
    print(f"处理完成! 共提取到 {len(all_questions)} 条题目")
    
    # 去重
    if len(all_questions) > 0:
        print("正在进行去重...")
        df = pd.DataFrame(all_questions)
        
        # 根据题干和选项去重
        df_deduplicated = df.drop_duplicates(subset=['question_text', 'options'], keep='first')
        
        removed_count = len(df) - len(df_deduplicated)
        print(f"✓ 去重完成,移除 {removed_count} 条重复题目")
        
        # 保存Excel
        output_path = "output/questions.xlsx"
        df_deduplicated.to_excel(output_path, index=False, engine='openpyxl')
        print(f"✓ 结果已保存到: {output_path}")
        print(f"✓ 最终题目数量: {len(df_deduplicated)} 条")
    else:
        print("⚠ 未提取到任何题目")
    
    # 保存错误日志
    if len(error_messages) > 0:
        with open(error_log_path, "w", encoding="utf-8") as f:
            f.writelines(error_messages)
        print(f"⚠ 有 {len(error_messages)} 个页面处理失败,详见: {error_log_path}")
    
    print("\n程序结束")


if __name__ == "__main__":
    main()
