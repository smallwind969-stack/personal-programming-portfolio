"""
题目解析模块 - 专门针对课堂派HTML结构
"""
from bs4 import BeautifulSoup, Tag
from typing import List
from models import Question


def parse_questions(html: str, page_url: str) -> List[Question]:
    """解析HTML页面,提取题目信息"""
    soup = BeautifulSoup(html, 'lxml')
    questions: List[Question] = []
    
    # 查找所有题型的题目容器
    # 1. 单选题
    single_choice = soup.select('.plugins-testType-SingleChoice')
    
    # 2. 多选题
    multiple_choice = soup.select('.plugins-testType-MultipleChoice')
    
    # 3. 判断题
    judgment = soup.select('.plugins-testType-Judge')
    
    # 4. 填空题
    fill_blank = soup.select('.plugins-testType-FillBlank')
    
    # 5. 简答题
    short_answer = soup.select('.plugins-testType-ShortAnswer')
    
    total = len(single_choice) + len(multiple_choice) + len(judgment) + len(fill_blank) + len(short_answer)
    print(f"  找到 {len(single_choice)} 道单选题, {len(multiple_choice)} 道多选题, {len(judgment)} 道判断题, {len(fill_blank)} 道填空题, {len(short_answer)} 道简答题")
    print(f"  共计 {total} 道题")
    
    # 解析单选题
    for container in single_choice:
        try:
            question = _parse_single_choice(container, len(questions) + 1, page_url)
            if question and question.is_valid():
                questions.append(question)
        except Exception as e:
            print(f"  解析单选题失败: {e}")
            continue
    
    # 解析多选题
    for container in multiple_choice:
        try:
            question = _parse_multiple_choice(container, len(questions) + 1, page_url)
            if question and question.is_valid():
                questions.append(question)
        except Exception as e:
            print(f"  解析多选题失败: {e}")
            continue
    
    # 解析判断题
    for container in judgment:
        try:
            question = _parse_judgment(container, len(questions) + 1, page_url)
            if question and question.is_valid():
                questions.append(question)
        except Exception as e:
            print(f"  解析判断题失败: {e}")
            continue
    
    # 解析填空题
    for container in fill_blank:
        try:
            question = _parse_fill_blank(container, len(questions) + 1, page_url)
            if question and question.is_valid():
                questions.append(question)
        except Exception as e:
            print(f"  解析填空题失败: {e}")
            continue
    
    # 解析简答题
    for container in short_answer:
        try:
            question = _parse_short_answer(container, len(questions) + 1, page_url)
            if question and question.is_valid():
                questions.append(question)
        except Exception as e:
            print(f"  解析简答题失败: {e}")
            continue
    
    return questions


def _parse_single_choice(container: Tag, index: int, page_url: str) -> Question:
    """解析单选题"""
    question = Question(
        source_url=page_url,
        question_index=index,
        question_type='单选题'
    )
    
    # 提取题干
    content_box = container.select_one('.content-box')
    if content_box:
        question.question_text = content_box.get_text(strip=True)
    
    # 提取选项
    options = []
    choice_elems = container.select('.el-radio__label')
    for choice_elem in choice_elems:
        choice_text_elem = choice_elem.select_one('.choice')
        if choice_text_elem:
            choice_text = choice_text_elem.get_text(strip=True)
            inner_div = choice_text_elem.select_one('.v-latex-rendered')
            if inner_div:
                option_content = inner_div.get_text(strip=True)
                option_letter = choice_text.split('.')[0] if '.' in choice_text else choice_text[0]
                full_option = f"{option_letter}. {option_content}"
                options.append(full_option)
    
    question.options = '\n'.join(options)
    
    # 提取答案
    answer_elem = container.select_one('.answer-correct-type i')
    if answer_elem:
        question.visible_answer = answer_elem.get_text(strip=True)
    
    # 提取解析
    analysis_elem = container.select_one('.analysisDesc .margb-20px')
    if analysis_elem:
        question.analysis = analysis_elem.get_text(strip=True)
    
    # 保存原始文本
    raw_text = container.get_text(separator='\n', strip=True)
    question.raw_text = raw_text[:500]
    
    return question


def _parse_multiple_choice(container: Tag, index: int, page_url: str) -> Question:
    """解析多选题"""
    question = Question(
        source_url=page_url,
        question_index=index,
        question_type='多选题'
    )
    
    # 提取题干
    content_box = container.select_one('.content-box')
    if content_box:
        question.question_text = content_box.get_text(strip=True)
    
    # 提取选项（多选题使用checkbox）
    options = []
    choice_elems = container.select('.el-checkbox__label')
    for choice_elem in choice_elems:
        choice_text_elem = choice_elem.select_one('.choice')
        if choice_text_elem:
            choice_text = choice_text_elem.get_text(strip=True)
            inner_div = choice_text_elem.select_one('.v-latex-rendered')
            if inner_div:
                option_content = inner_div.get_text(strip=True)
                option_letter = choice_text.split('.')[0] if '.' in choice_text else choice_text[0]
                full_option = f"{option_letter}. {option_content}"
                options.append(full_option)
    
    question.options = '\n'.join(options)
    
    # 提取答案
    answer_elem = container.select_one('.answer-correct-type i')
    if answer_elem:
        question.visible_answer = answer_elem.get_text(strip=True)
    
    # 提取解析
    analysis_elem = container.select_one('.analysisDesc .margb-20px')
    if analysis_elem:
        question.analysis = analysis_elem.get_text(strip=True)
    
    # 保存原始文本
    raw_text = container.get_text(separator='\n', strip=True)
    question.raw_text = raw_text[:500]
    
    return question


def _parse_judgment(container: Tag, index: int, page_url: str) -> Question:
    """解析判断题"""
    question = Question(
        source_url=page_url,
        question_index=index,
        question_type='判断题'
    )
    
    # 提取题干
    content_box = container.select_one('.content-box')
    if content_box:
        question.question_text = content_box.get_text(strip=True)
    
    # 提取选项（对/错）
    options = []
    judgment_options = container.select('.Judge-radio .el-radio__label')
    for opt_elem in judgment_options:
        opt_text = opt_elem.get_text(strip=True)
        if opt_text in ['对', '错']:
            options.append(opt_text)
    
    # 如果上面没找到，尝试其他选择器
    if len(options) == 0:
        judgment_options = container.select('.el-radio__label')
        for opt_elem in judgment_options:
            opt_text = opt_elem.get_text(strip=True)
            if opt_text in ['对', '错']:
                options.append(opt_text)
    
    question.options = '\n'.join(options)
    
    # 提取答案
    answer_elem = container.select_one('.answer-correct-type i')
    if answer_elem:
        question.visible_answer = answer_elem.get_text(strip=True)
    
    # 提取解析
    analysis_elem = container.select_one('.analysisDesc .margb-20px')
    if analysis_elem:
        question.analysis = analysis_elem.get_text(strip=True)
    
    # 保存原始文本
    raw_text = container.get_text(separator='\n', strip=True)
    question.raw_text = raw_text[:500]
    
    return question


def _parse_fill_blank(container: Tag, index: int, page_url: str) -> Question:
    """解析填空题"""
    question = Question(
        source_url=page_url,
        question_index=index,
        question_type='填空题'
    )
    
    # 提取题干
    content_box = container.select_one('.content-box')
    if content_box:
        question.question_text = content_box.get_text(strip=True)
    
    # 提取答案
    answer_elem = container.select_one('.answer-correct-type')
    if answer_elem:
        question.visible_answer = answer_elem.get_text(strip=True)
    
    # 提取解析
    analysis_elem = container.select_one('.analysisDesc .margb-20px')
    if analysis_elem:
        question.analysis = analysis_elem.get_text(strip=True)
    
    # 保存原始文本
    raw_text = container.get_text(separator='\n', strip=True)
    question.raw_text = raw_text[:500]
    
    return question


def _parse_short_answer(container: Tag, index: int, page_url: str) -> Question:
    """解析简答题"""
    question = Question(
        source_url=page_url,
        question_index=index,
        question_type='简答题'
    )
    
    # 提取题干
    content_box = container.select_one('.content-box')
    if content_box:
        question.question_text = content_box.get_text(strip=True)
    
    # 提取答案
    answer_elem = container.select_one('.answer-correct-type')
    if answer_elem:
        question.visible_answer = answer_elem.get_text(strip=True)
    
    # 提取解析
    analysis_elem = container.select_one('.analysisDesc .margb-20px')
    if analysis_elem:
        question.analysis = analysis_elem.get_text(strip=True)
    
    # 保存原始文本
    raw_text = container.get_text(separator='\n', strip=True)
    question.raw_text = raw_text[:500]
    
    return question
