# -*- coding: utf-8 -*-
# @Time    : 2025/6/16
# @Author  : 小宇
# @File    : database.py

import mysql.connector
from mysql.connector import Error
from PyQt5.QtCore import QObject, pyqtSignal


class DatabaseManager(QObject):
    """数据库管理类，使用单例模式管理数据库连接"""
    _instance = None  # 单例实例

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_config=None):
        super().__init__()
        self.db_config = db_config
        self.connection = None
        self._init_connection()

    def _init_connection(self):
        """初始化数据库连接"""
        if self.db_config and not self.connection:
            try:
                self.connection = mysql.connector.connect(**self.db_config)
                print("数据库连接成功")
            except Error as e:
                print(f"数据库连接失败: {e}")

    def is_connected(self):
        """检查连接状态"""
        return self.connection and self.connection.is_connected()

    def check_username_exists(self, username):
        """检查用户名是否存在"""
        if not self.is_connected():
            self._init_connection()

        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT username FROM users WHERE username = %s", (username,))
            result = cursor.fetchone()
            cursor.close()
            return result is not None
        except Error as e:
            print(f"查询用户失败: {e}")
            return False

    def add_user(self, username, password):
        """添加新用户（userstate=1，createtime自动生成）"""
        if not self.is_connected():
            self._init_connection()

        try:
            cursor = self.connection.cursor()
            cursor.execute(
                "INSERT INTO users (username, password, userstate) VALUES (%s, %s, 1)",
                (username, password)
            )
            self.connection.commit()
            cursor.close()
            return True
        except Error as e:
            print(f"添加用户失败: {e}")
            self.connection.rollback()
            return False

    def validate_user(self, username, password):
        """验证用户登录"""
        if not self.is_connected():
            self._init_connection()

        try:
            cursor = self.connection.cursor()
            cursor.execute(
                "SELECT userid, username, userstate FROM users WHERE username = %s AND password = %s",
                (username, password)
            )
            result = cursor.fetchone()
            cursor.close()
            return result if result else None
        except Error as e:
            print(f"验证用户失败: {e}")
            return None

    def close_connection(self):
        """关闭数据库连接"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            self.connection = None
            print("数据库连接已关闭")