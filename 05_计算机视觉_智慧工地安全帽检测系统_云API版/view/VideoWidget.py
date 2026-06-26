# -*- coding: utf-8 -*-
# @Time    : 2025/5/10 1:13
# @Author  : 小宇
# @File    : 1.py
#-*- coding: utf-8 -*-
# @Time    : 2025/5/6 18:55
# @Author  : 小宇
# @File    : VideoWidget.py
import os
import tempfile
import time
import cv2
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from apig_sdk import signer
import requests
import json


class VideoWidget(QWidget):
    def __init__(self, w=670, h=460):
        super().__init__()
        self.w = w
        self.h = h
        self.resize(self.w, self.h)
        self.video_path = './videos/'
        self.video_check_path = './check_videos/'
        self.file_path = ''
        self.cap = None
        self.out = None
        self.out2 = None
        self.frameCount = 0
        self.current_frame_pos = 0  # 新增：记录当前视频帧位置
        self.init_video()
        self.init_control()

    def init_control(self):
        button_layout = QHBoxLayout()

        self.startBtn = QPushButton('播放', self)
        self.startBtn.setStyleSheet('font:20px')
        self.stopBtn = QPushButton('停止', self)
        self.stopBtn.setStyleSheet('font:20px')
        self.openCamBtn = QPushButton('打开摄像头', self)
        self.openCamBtn.setStyleSheet('font:20px')
        self.checkBtn = QPushButton('云检测', self)
        self.checkBtn.setStyleSheet('font:20px')

        button_layout.addWidget(self.startBtn)
        button_layout.addWidget(self.stopBtn)
        button_layout.addWidget(self.openCamBtn)
        button_layout.addWidget(self.checkBtn)

        main_layout = QVBoxLayout(self)
        main_layout.addLayout(button_layout)

        self.startBtn.clicked.connect(self.video_start)
        self.stopBtn.clicked.connect(self.video_stop)
        self.openCamBtn.clicked.connect(self.cam_open)
        self.checkBtn.clicked.connect(self.video_check)

    def init_video(self):
        # 视频预先初始化
        self.cap = cv2.VideoCapture(self.file_path)
        self.f = self.cap.get(5) if self.cap.isOpened() else 30
        self.t = int(1000 / self.f) if self.cap.isOpened() else 33

        # 定时器 - 按一定时间间隔不断地执行某个内容
        self.time1 = QTimer()  # 读取视频帧的定时器
        self.time1.timeout.connect(self.time_read)

        self.time2 = QTimer()  # 保存视频的定时器
        self.time2.timeout.connect(self.save_frame)

        self.time3 = QTimer()  # 检测视频的定时器
        self.time3.timeout.connect(self.check_frame)

    def video_start(self):
        if self.cap is None or not self.cap.isOpened():
            if self.file_path:
                self.cap = cv2.VideoCapture(self.file_path)
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame_pos)  # 设置到停止时的帧位置
                if self.cap.isOpened():
                    self.f = self.cap.get(5)  # 获取帧率
                    self.t = int(1000 / self.f)  # 计算每帧之间的毫秒数
                    self.time1.start(self.t)
                    print(f"开始播放视频: {self.file_path}")
        else:
            if not self.time1.isActive():
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame_pos)  # 设置到停止时的帧位置
                self.f = self.cap.get(5)
                self.t = int(1000 / self.f)
                self.time1.start(self.t)
                print(f"继续播放视频: {self.file_path}")

    def video_stop(self):
        # 停止播放视频，释放资源
        if self.cap and self.cap.isOpened():
            self.current_frame_pos = self.cap.get(cv2.CAP_PROP_POS_FRAMES)  # 记录当前帧位置
            self.time1.stop()
            print("视频播放已停止")
            if self.out:
                self.out.release()
                self.out = None

    def cam_open(self):
        print('尝试打开摄像头...')
        self.video_stop()  # 先停止当前播放的视频

        self.cap = cv2.VideoCapture(0)  # 0表示默认摄像头
        if not self.cap.isOpened():
            print("无法打开摄像头")
            return

        # 获取摄像头参数
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(self.cap.get(cv2.CAP_PROP_FPS))

        print(f"摄像头已打开: {width}x{height}, {fps} FPS")

        # 开始读取摄像头帧
        self.time1.start(33)  # 约30FPS的间隔

        # 创建视频写入器，用于保存摄像头视频
        self.timeStr = time.strftime('%Y%m%d%H%M%S', time.localtime())
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # 使用MP4V编码
        self.out = cv2.VideoWriter(
            f'{self.video_path}{self.timeStr}.mp4',
            fourcc,
            fps,
            (width, height)
        )

        if not self.out.isOpened():
            print("无法创建视频文件进行保存")
            return

        # 开始保存视频帧
        self.time2.start(33)
        print("开始录制摄像头视频")

    def save_frame(self):
        # 保存视频帧，并添加时间水印
        if self.cap and self.cap.isOpened() and self.out:
            ret, frame = self.cap.read()
            if ret:
                # 添加时间水印
                timeStr = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
                cv2.putText(
                    frame,
                    timeStr,
                    (5, 80),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.75,
                    (110, 110, 110),
                    2
                )

                self.out.write(frame)  # 写入视频帧
                self.frameCount += 1
                print(f"已保存帧: {self.frameCount}")

                if self.frameCount == 200:  # 每200帧保存一次
                    if hasattr(self.parentWidget(),'save_video_signal'):
                        self.parentWidget().save_video_signal.emit()
                    self.frameCount = 0
            else:
                print("无法读取视频帧")

    def video_check(self):
        # 开始视频检测（安全帽、反光衣等）
        if self.cap and self.cap.isOpened():
            if not self.file_path:
                print("当前使用摄像头，无法进行完整视频检测")
                return

            # 创建输出视频文件
            filename = os.path.basename(self.file_path).split('.')[0]
            save_path = f'{self.video_check_path}{filename}_check.mp4'

            # 获取视频参数
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            # 创建视频写入器
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.out2 = cv2.VideoWriter(save_path, fourcc, fps, (width, height))

            if not self.out2.isOpened():
                print("无法创建检测结果视频文件")
                return

            # 开始检测
            self.time3.start()
            print(f"开始视频检测，结果将保存到: {save_path}")
        else:
            print("没有打开的视频，无法进行云检测")

    def check_frame(self):
        # 检测当前视频帧中的物体（安全帽、反光衣等）
        if self.cap and self.cap.isOpened() and self.out2:
            ret, frame = self.cap.read()
            if ret:
                # 保存当前帧为临时图像
                img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                with tempfile.NamedTemporaryFile(mode='w+b', delete=False, suffix='.jpg') as temp:
                    cv2.imwrite(temp.name, img)
                    temp_file_path = temp.name

                # 调用云检测API
                url = "https://infer-modelarts-cn-north-4.modelarts-infer.com/v1/infers/3c3d55f4-35a4-479f-afbd-a2b6c42862cf"
                ak = os.getenv("HUAWEI_CLOUD_AK", "")
                sk = os.getenv("HUAWEI_CLOUD_SK", "")
                if not ak or not sk:
                    print("缺少 HUAWEI_CLOUD_AK / HUAWEI_CLOUD_SK 环境变量，跳过云检测")
                    return

                # 签名认证
                method = 'POST'
                headers = {"x-sdk-content-sha256": "UNSIGNED-PAYLOAD"}
                request = signer.HttpRequest(method, url, headers)

                sig = signer.Signer()
                sig.Key = ak
                sig.Secret = sk
                sig.Sign(request)

                try:
                    # 发送请求
                    with open(temp_file_path, 'rb') as f:
                        files = {'images': f}
                        resp = requests.request(
                            request.method,
                            request.scheme + "://" + request.host + request.uri,
                            headers=request.headers,
                            files=files
                        )

                    # 处理响应
                    if resp.status_code == 200:
                        try:
                            data_dict = json.loads(resp.text)
                            label_list = data_dict.get('detection_classes', [])
                            boxs_list = data_dict.get('detection_boxes', [])
                            scores_list = data_dict.get('detection_scores', [])

                            # 在图像上绘制检测结果
                            h, w, _ = frame.shape
                            for i, (box, label, score) in enumerate(zip(boxs_list, label_list, scores_list)):
                                y1, x1, y2, x2 = box
                                y1 = int(float(y1))
                                x1 = int(float(x1))
                                y2 = int(float(y2))
                                x2 = int(float(x2))

                                # 检查边界
                                if x1 < 0 or x1 >= w or x2 < 0 or x2 >= w or y1 < 0 or y1 >= h or y2 < 0 or y2 >= h:
                                    print(f"检测框 {i} 坐标超出图像边界，跳过")
                                    continue

                                # 绘制边界框
                                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                                # 绘制标签和置信度
                                text = f'{label}({score * 100:.2f}%)'
                                cv2.putText(
                                    frame,
                                    text,
                                    (x1 + 5, y1 + 25),
                                    cv2.FONT_HERSHEY_SIMPLEX,
                                    0.8,
                                    (0, 255, 0),
                                    2
                                )

                            # 写入检测结果视频
                            self.out2.write(frame)

                            # 更新统计信息
                            if hasattr(self.parentWidget(), 'left_line1'):
                                helmet_count = label_list.count('安全帽')
                                vest_count = label_list.count('反光衣')
                                self.parentWidget().left_line1.setText(
                                    f"检测到安全帽数：{helmet_count}个\n检测到反光衣数：{vest_count}个"
                                )

                        except (json.JSONDecodeError, KeyError) as e:
                            print(f"解析检测结果失败: {str(e)}")
                            print(f"API响应: {resp.text}")
                    else:
                        print(f"云检测API返回错误状态码: {resp.status_code}")
                        print(f"响应内容: {resp.text}")

                except Exception as e:
                    print(f"发送检测请求时发生错误: {str(e)}")
                finally:
                    # 删除临时文件
                    try:
                        os.remove(temp_file_path)
                    except OSError as e:
                        print(f"删除临时文件失败: {str(e)}")
            else:
                print('视频检测完成')
                self.time3.stop()
                if self.out2:
                    self.out2.release()
                    print(f"检测结果已保存到: {self.out2.get(cv2.CAP_PROP_POS_MSEC)}")

                    # 更新检测后视频列表
                    if hasattr(self.parentWidget(), 'updata_chack_video'):
                        self.parentWidget().updata_chack_video()
        else:
            print("当前没有打开的视频或摄像头，无法进行云检测")

    def time_read(self):
        # 定时读取视频帧并显示
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                # 转换颜色空间以正确显示
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = frame.shape
                bytes_per_line = ch * w

                # 创建QImage并显示
                video_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
                if hasattr(self.parentWidget(), 'imgLab'):
                    self.parentWidget().imgLab.setPixmap(QPixmap.fromImage(video_img))
                    self.parentWidget().imgLab.setScaledContents(True)
            else:
                print("视频或摄像头读取结束")
                self.video_stop()
        else:
            print("没有打开的视频或摄像头，无法读取画面")

    def video_init_control(self, path):
        # 初始化视频文件
        self.file_path = path
        self.cap = cv2.VideoCapture(self.file_path)
        if not self.cap.isOpened():
            print(f"无法打开视频文件: {path}")
            return

        # 获取视频参数
        self.f = self.cap.get(cv2.CAP_PROP_FPS)  # 帧率
        self.n = self.cap.get(cv2.CAP_PROP_FRAME_COUNT)  # 总帧数
        self.t = int(1000 / self.f)  # 每帧之间的毫秒数

        print(f"视频已加载: {path}")
        print(f"帧率: {self.f} FPS, 总帧数: {self.n}")

    def get_fist_frame(self):
        # 获取视频的第一帧并显示
        if self.cap and self.cap.isOpened():
            # 重置视频到开始位置
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

            ret, frame = self.cap.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = frame.shape
                bytes_per_line = ch * w

                video_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
                if hasattr(self.parentWidget(), 'imgLab'):
                    self.parentWidget().imgLab.setPixmap(QPixmap.fromImage(video_img))
                    self.parentWidget().imgLab.setScaledContents(True)
            else:
                print("无法读取视频的第一帧")
        else:
            print("没有打开的视频，无法获取第一帧")
