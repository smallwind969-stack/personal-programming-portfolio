# -*- coding: utf-8 -*-
# @Time    : 2025/6/19 18:57
# @Author  : 小宇
# @File    : DB_util.py


# 安装pymysql 1.1.1
import os
import pymysql

class DB_util(object):
    def __init__(self):
        self.host = os.getenv('MYSQL_HOST', 'localhost')
        self.user = os.getenv('MYSQL_USER', 'root')
        self.password = os.getenv('MYSQL_PASSWORD', '')
        self.database = os.getenv('MYSQL_DATABASE', 'ai250317')

    def db_user_login(self, acc, pwd):
        """
        登录业务
        :param acc: 账号
        :param pwd: 密码
        :return: int类型 1 和 0 ，1表示成功，0表示失败
        """
        try:
            #获取链接
            conn = pymysql.connect(host=self.host, port=3306, user=self.user, password=self.password, database=self.database, charset='utf8')
            #获取游标
            cursor = conn.cursor()
            #执行查询语句
            #定义语句
            sql = f"SELECT * FROM users where user_name = '{acc}' AND user_pwd = '{pwd}'"
            #执行
            cursor.execute(sql)
            # print(cursor.fetchall())
            res = list(cursor.fetchall())
            print(res)
            if len(res) > 0:
                #因为登录以后主页需要用到用户名，所以可以直接把res返回出去
                return res
            else:
                return 0
        except Exception as e:
            print(e)
            conn.rollback()#回滚  如果try 里面执行了插入，更新等等很多操作，只要一个出错，所有try 里面的操作都会还原
            return 0
        finally:
            cursor.close()
            conn.close()



    def db_user_res(self, acc, pwd, age):
        """
        注册业务
        :param acc: 账号
        :param pwd: 密码
        :param age: 年龄或/手机号/头像图片名字
        :return: int类型 1 和 0 ，1表示成功，0表示失败
        """
        try:
            # 获取连接
            conn = pymysql.connect(host=self.host, port=3306, user=self.user, password=self.password,
                                   database=self.database, charset='utf8')
            # 获取游标
            cursor = conn.cursor()
            # 执行查询语句
            # 定义语句
            sql = f"INSERT INTO  users(user_name,create_time,user_age,user_pwd ) VALUES('{acc}',NOW(),{age},md5('{pwd}'));"
            # 执行
            i = cursor.execute(sql)  # i 就是受影响的行数
            # 增删改一定要commit，否则无法保存数据
            conn.commit()
            if i > 0:
                # 因为登录以后主页需要用的用户名，所以呢，可以直接把res返回出去
                return 1
            else:
                return 0
        except Exception as e:
            print(e)
            conn.rollback()  # 回滚  如果try 里面执行了插入，更新等等很多操作，只要一个出错，所有try 里面的操作都会还原
            return 0
        finally:
            cursor.close()
            conn.close()

    def db_upate_pwd(self, acc, id, new_pwd):
        """
        修改密码
        :param acc: 账号，如果账号是唯一的，可以使用这个条件
        :param id: 如果其他条件不唯一，那就是用登录时候提供的id 来做条件
        :param new_pwd: 新密码
        :return: 1，0
        """
        try:
            conn = pymysql.connect(host=self.host, port=3306, user=self.user, password=self.password,
                                   database=self.database, charset='utf8')
            cursor = conn.cursor()
            sql = f"UPDATE users SET user_pwd='{new_pwd}' WHERE user_id = {id}"
            i = cursor.execute(sql)  # i 就是受影响的行数
            conn.commit()
            if i > 0:
                return 1
            else:
                return 0
        except Exception as e:
            print(e)
            conn.rollback()  # 回滚  如果try 里面执行了插入，更新等等很多操作，只要一个出错，所有try 里面的操作都会还原
            return 0
        finally:
            cursor.close()
            conn.close()

    def db_seach_img(self, image_name):
        """
        搜索图片
        :param image_name: 需要搜索的图片名字
        :return: 图片的数据 地址，创建时间等等信息
        """
        try:
            conn = pymysql.connect(host=self.host, port=3306, user=self.user, password=self.password,
                                   database=self.database, charset='utf8')
            cursor = conn.cursor()
            sql = f"SELECT * FROM images WHERE image_name LIKE '%{image_name}%'"
            cursor.execute(sql)
            # print(cursor.fetchall())
            res = list(cursor.fetchall())
            print(res)
            if len(res) > 0:
                # 因为登录以后主页需要用的用户名，所以呢，可以直接把res返回出去
                return res
            else:
                return 0
        # 注意：原代码缺少 except 和 finally 块，实际使用可能因异常未处理导致问题，可补充如下（示例）：
        except Exception as e:
            print(f"查询异常: {e}")
            return 0
        finally:
            cursor.close()
            conn.close()





    def get_connect(self):
        conn = pymysql.connect(host=self.host, port=3306, user=self.user, password=self.password, database=self.database, charset = 'utf8')
        print(conn)

if __name__ == '__main__':
    db = DB_util()
    #db.get_connect()
    # print(db)
    res = db.db_user_login('lisi', '123456')
    if res != 0:
        pass


