"""
题目数据模型
定义题目的数据结构
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Question:
    """
    题目数据结构
    
    属性:
        source_url: 来源页面URL
        question_index: 题目序号
        question_type: 题型(单选题/多选题/判断题等)
        question_text: 题干文本
        options: 选项文本(多个选项用换行分隔)
        visible_answer: 页面正常显示的答案
        analysis: 页面正常显示的解析
        raw_text: 题目块的完整原始文本
    """
    source_url: str
    question_index: int
    question_type: str = ""
    question_text: str = ""
    options: str = ""
    visible_answer: str = ""
    analysis: str = ""
    raw_text: str = ""
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "source_url": self.source_url,
            "question_index": self.question_index,
            "question_type": self.question_type,
            "question_text": self.question_text,
            "options": self.options,
            "visible_answer": self.visible_answer,
            "analysis": self.analysis,
            "raw_text": self.raw_text
        }
    
    def is_valid(self) -> bool:
        """检查题目是否有效(至少有题干或原始文本)"""
        return bool(self.question_text or self.raw_text)
