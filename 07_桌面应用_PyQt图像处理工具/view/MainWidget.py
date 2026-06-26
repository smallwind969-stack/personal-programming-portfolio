# -*- coding: utf-8 -*-
# @Time    : 2025/5/14 15:32
# @Author  : 小宇
# @File    : MainWidget.py

import os
import cv2
import numpy as np
from PIL import Image, ImageFont, ImageDraw
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import QWidget

from view.lightWin import lightWin


class MainWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.pathOp = None
        self.tempFile = None  # 新增：保存临时处理文件
        self.resize(1300, 700)
        self.setWindowTitle('美图工具')
        self.setStyleSheet('background-color:rgba(20,100,140,25%);font:24px;color:white')
        self.init_control()

    def init_control(self):
        # 总布局
        self.totalLayout = QHBoxLayout()  # 水平布局
        self.setLayout(self.totalLayout)  # 放置布局

        # 子布局
        # 第一列垂直布局
        self.line1 = QVBoxLayout(self)
        self.totalLayout.addLayout(self.line1)
        self.B1 = QPushButton('打开图片', self)
        self.B3 = QPushButton('添加背景', self)
        self.B2 = QPushButton('个人照换背景', self)
        self.B4 = QPushButton('人物素描', self)
        self.B6 = QPushButton('添加水印', self)
        self.B7 = QPushButton('调整亮度', self)
        self.B5 = QPushButton('保存图片', self)

        # 按钮加入到垂直布局
        self.line1.addWidget(self.B1)
        self.line1.addWidget(self.B2)
        self.line1.addWidget(self.B3)
        self.line1.addWidget(self.B4)
        self.line1.addWidget(self.B5)
        self.line1.addWidget(self.B6)
        self.line1.addWidget(self.B7)

        # 第二列
        self.line2 = QVBoxLayout()  # 垂直布局
        self.totalLayout.addLayout(self.line2)  # 把第一列加入水平布局中
        # 头部文字
        self.L1 = QLabel('图片列表', self)
        self.L1.setStyleSheet('color:white; font:28px')
        self.L1.setAlignment(Qt.AlignCenter)  # 居中
        self.line2.addWidget(self.L1)
        # 图片列表
        self.V1 = QListWidget(self)  # 图片列表
        # 读取储存图片的文件夹，得到一个文件的集合
        self.files = os.listdir('./image/')
        print(self.files)
        # 遍历这个集合，把图片添加到QListWidget
        for file in self.files:
            # 每个的图片对象
            self.item = QListWidgetItem(QIcon(os.path.join('./image/', file)), '')
            # 设置图片的统一大小
            self.V1.setIconSize(QSize(150, 150))
            # 图片加入界面组件
            self.V1.addItem(self.item)

        self.line2.addWidget(self.V1)
        # 列表中图片的点击事件绑定
        self.V1.itemClicked.connect(self.clicked)

        # 第三列
        self.line3 = QHBoxLayout()  # 水平布局
        self.totalLayout.addLayout(self.line3)  # 把第一列加入水平布局中
        # 原图
        # 预览图
        self.L2 = QLabel('原图', self)
        self.L3 = QLabel('效果图', self)  # 修改：更合适的标签名
        self.L2.setAlignment(Qt.AlignCenter)  # 居中
        self.L3.setAlignment(Qt.AlignCenter)  # 居中
        # 把这两个文字加入第三列
        self.line3.addWidget(self.L2)
        self.line3.addWidget(self.L3)

        # 三列权重占比  line1:line2:line3  1:1:5
        self.totalLayout.setStretchFactor(self.line1, 1)
        self.totalLayout.setStretchFactor(self.line2, 1)
        self.totalLayout.setStretchFactor(self.line3, 5)

        # 设置外边距
        self.line1.setContentsMargins(10, 10, 10, 10)  # 这外框的外边距  左边顺时针

        # 事件绑定
        self.B1.clicked.connect(self.openFile)
        self.B4.clicked.connect(self.sumiao)
        self.B6.clicked.connect(self.addwater)
        self.B5.clicked.connect(self.saveImg)
        self.B7.clicked.connect(self.changeLight)
        self.B3.clicked.connect(self.addBackground)
        self.B2.clicked.connect(self.changeBackground)

    def clicked(self):
        """
        列表图片点击，预览在预览区
        :return:
        """
        try:
            index = self.V1.currentIndex().row()  # 被点的图片
            file = self.files[index]
            file = './image/' + file
            self.L3.setPixmap(QPixmap(file).scaledToWidth(300))
            self.pathBg = file  # 记录背景图片路径
        except Exception as e:
            print(f"图片点击事件出错: {e}")

    def openFile(self):
        '''
        打开本地图片,并将其添加到图片列表中
        :return:
        '''
        try:
            file, _ = QFileDialog.getOpenFileName(self, '打开图片', '',
                                                  'Images(*.jpg *.png *.jpeg *.bmp)')
            if not file:  # 如果用户取消选择，直接返回
                return

            # 保存临时图片
            path = './temp_image/local_up.' + file.split('.')[-1]
            img = Image.open(file)
            img.save(path)
            self.L2.setPixmap(QPixmap(path).scaledToWidth(300))
            self.pathOp = path  # 保存当前操作图片路径

            # 将图片保存到./image/路径
            os.makedirs('./image/', exist_ok=True)
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            target_name = f"img_{timestamp}.{file.split('.')[-1]}"
            target_path = os.path.join('./image/', target_name)
            import shutil
            shutil.copy2(path, target_path)
            print(f"图片已保存到: {target_path}")

            # 更新图片列表
            self.update_image_list()
        except Exception as e:
            print(f"打开图片时出错: {e}")

    def sumiao(self):
        '''
        素描效果
        :return:
        '''
        try:
            if not self.pathOp or not os.path.exists(self.pathOp):
                QMessageBox.warning(self, "错误", "请先打开一张图片")
                return

            img = cv2.imread(self.pathOp, 0)
            if img is None:
                raise ValueError(f"无法读取图像: {self.pathOp}")

            # 图像预处理
            img_blur = cv2.GaussianBlur(img, (13, 13), 0)
            # 二值化
            new_img = cv2.adaptiveThreshold(img_blur, 255,
                                            adaptiveMethod=cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                            thresholdType=cv2.THRESH_BINARY,
                                            blockSize=13, C=2)

            # 保存临时文件
            temp_dir = './temp_image/'
            os.makedirs(temp_dir, exist_ok=True)
            self.tempFile = os.path.join(temp_dir, f"sumiao.{self.pathOp.split('.')[-1]}")
            cv2.imwrite(self.tempFile, new_img)

            # 显示结果
            self.L3.setPixmap(QPixmap(self.tempFile).scaledToWidth(300))
        except Exception as e:
            print(f"生成素描效果时出错: {e}")

    def addwater(self):
        '''
        添加水印
        :return:
        '''
        try:
            if not self.pathOp or not os.path.exists(self.pathOp):
                QMessageBox.warning(self, "错误", "请先打开一张图片")
                return

            img = Image.open(self.pathOp)
            width, height = img.size
            font = ImageFont.truetype("FZSTK.TTF", 35)  # 确保字体文件存在
            text = "传一智能"

            # 创建水印图像
            watermark = Image.new('RGBA', img.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(watermark)

            # 计算水印间距
            spacing_x = 250
            spacing_y = 250
            for y in range(0, height, spacing_y):
                for x in range(0, width, spacing_x):
                    # 绘制倾斜45°的水印
                    rotated_text = Image.new('RGBA', draw.textsize(text, font), (0, 0, 0, 0))
                    rdraw = ImageDraw.Draw(rotated_text)
                    rdraw.text((0, 0), text, font=font, fill=(255, 255, 255, 200))  # 半透明白色
                    rotated_text = rotated_text.rotate(45, expand=True)
                    watermark.paste(rotated_text, (x, y), rotated_text)

            # 合并水印
            result = Image.alpha_composite(img.convert('RGBA'), watermark)

            # 保存临时文件
            temp_dir = './temp_image/'
            os.makedirs(temp_dir, exist_ok=True)
            self.tempFile = os.path.join(temp_dir, f"watermark.{self.pathOp.split('.')[-1]}")
            result.convert('RGB').save(self.tempFile)

            # 显示结果
            self.L3.setPixmap(QPixmap(self.tempFile).scaledToWidth(300))
        except Exception as e:
            print(f"添加水印时出错: {e}")


    def saveImg(self):
        '''
        保存处理后的图片
        :return:
        '''
        try:
            if not hasattr(self, 'tempFile') or self.tempFile is None:
                QMessageBox.warning(self, "错误", "没有可保存的处理结果")
                return

            file, _ = QFileDialog.getSaveFileName(self, '保存图片', './', 'Images(*.jpg *.png)')
            if file:
                img = Image.open(self.tempFile)
                img.save(file)
                QMessageBox.information(self, "成功", f"图片已保存至: {file}")
        except Exception as e:
            print(f"保存图片时出错: {e}")

    def changeLight(self):
        '''
        打开亮度调整窗口
        :return:
        '''
        if not self.pathOp or not os.path.exists(self.pathOp):
            QMessageBox.warning(self, "错误", "请先打开一张图片")
            return

        self.light_window = lightWin()
        self.light_window.pathLight = self.pathOp
        self.light_window.main_window = self  # 传递主窗口引用
        self.hide()  # 隐藏主窗口
        self.light_window.show()

    def addBackground(self):
        '''
        添加背景图片到图片列表
        :return:
        '''
        try:
            file, _ = QFileDialog.getOpenFileName(self, '打开图片', '',
                                                  'Images(*.jpg *.png *.jpeg *.bmp)')
            if not file:
                return

            # 添加到图片列表
            new_item = QListWidgetItem(QIcon(file), '')
            self.V1.addItem(new_item)

            # 保存到本地
            img_name = file.split('/')[-1]
            path = f'./image/{img_name}'
            img = Image.open(file)
            img.save(path)

            # 更新文件列表
            self.files.append(img_name)
        except Exception as e:
            print(f"添加背景图片时出错: {e}")

    def changeBackground(self):
        '''
        个人照换背景
        :return:
        '''
        try:
            if not self.pathOp or not os.path.exists(self.pathOp):
                QMessageBox.warning(self, "错误", "请先打开一张图片")
                return
            if not hasattr(self, 'pathBg') or not os.path.exists(self.pathBg):
                QMessageBox.warning(self, "错误", "请先选择背景图片")
                return

            # 读取前景图
            image = cv2.imdecode(np.fromfile(self.pathOp, dtype=np.uint8), cv2.IMREAD_COLOR)
            img_hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

            # 创建蒙版：提取非蓝色区域（假设背景是蓝色）
            mask_hsv = cv2.inRange(img_hsv,
                                   lowerb=np.array([100, 100, 100]),
                                   upperb=np.array([124, 255, 255]))
            new_mask = cv2.bitwise_not(mask_hsv)

            # 保留前景（人物），背景变为黑色
            new_hsv = cv2.bitwise_and(img_hsv, img_hsv, mask=new_mask)
            new_hsv = cv2.cvtColor(new_hsv, cv2.COLOR_HSV2BGR)

            # 读取背景图并调整大小
            h, w = image.shape[:2]
            bg_img = cv2.imread(self.pathBg)
            bg_img_new = cv2.resize(bg_img, (w, h))

            # 像素级替换背景
            for i in range(h):
                for j in range(w):
                    if new_hsv[i, j, 0] == 0 and new_hsv[i, j, 1] == 0 and new_hsv[i, j, 2] == 0:
                        new_hsv[i, j] = bg_img_new[i, j]

            # 保存结果
            self.tempFile = './temp_image/tempBg.jpg'
            cv2.imwrite(self.tempFile, new_hsv)

            if os.path.exists(self.tempFile):
                self.L3.setPixmap(QPixmap(self.tempFile).scaledToWidth(300))
            else:
                print("保存图片失败")

        except Exception as e:
            print(f"背景替换出错: {e}")
            QMessageBox.warning(self, "处理错误", f"背景替换过程中出错: {str(e)}")

    def update_image_list(self):
        """更新图片列表"""
        self.V1.clear()
        self.files = os.listdir('./image/')
        for file in self.files:
            self.item = QListWidgetItem(QIcon(os.path.join('./image/', file)), '')
            self.V1.setIconSize(QSize(150, 150))
            self.V1.addItem(self.item)

    def back_from_light(self):
        """从亮度窗口返回时调用"""
        self.show()
        if hasattr(self, 'tempFile') and os.path.exists(self.tempFile):
            self.L3.setPixmap(QPixmap(self.tempFile).scaledToWidth(300))