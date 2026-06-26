# -*- coding: utf-8 -*-
# @Time    : 2025/4/6 22:01
# @Author  : 小宇
# @File    : tools.py
from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtCore import QRegExp


def get_input_validator():
    reg_exp = QRegExp("[a-zA-Z0-9]{1,8}")
    return QRegExpValidator(reg_exp)
