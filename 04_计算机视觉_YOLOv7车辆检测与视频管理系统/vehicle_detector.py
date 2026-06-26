# -*- coding: utf-8 -*-
# @Time    : 2025/7/9 1:17
# @Author  : 小宇
# @File    : vehicle_detector.py.py
import cv2
import torch
import numpy as np
from pathlib import Path
import time
from numpy import random
from models.experimental import attempt_load
from utils.general import check_img_size, non_max_suppression, scale_coords, set_logging
from utils.torch_utils import select_device, time_synchronized, TracedModel


class VehicleDetector:
    """基于YOLOv7的车辆检测器，适配原始YOLOv7检测逻辑"""

    # 定义车辆相关类别（COCO数据集）
    VEHICLE_CLASSES = [2, 3, 5, 7]  # 2:汽车, 3:摩托车, 5:公交车, 7:卡车

    def __init__(self, weights='yolov7.pt', device='', img_size=640,
                 conf_thres=0.25, iou_thres=0.45, trace=True, box_correction=True):
        """
        初始化车辆检测器
        :param weights: 模型权重路径
        :param device: 运行设备 (cpu或cuda设备编号)
        :param img_size: 推理图像尺寸
        :param conf_thres: 置信度阈值
        :param iou_thres: NMS的IOU阈值
        :param trace: 是否使用模型追踪加速
        :param box_correction: 是否启用边界框校准
        """
        self.weights = weights
        self.img_size = img_size
        self.conf_thres = conf_thres
        self.iou_thres = iou_thres
        self.trace = trace
        self.box_correction = box_correction  # 新增：边界框校准选项

        # 初始化日志
        set_logging()

        # 选择设备
        self.device = select_device(device)
        self.half = self.device.type != 'cpu'  # 仅在CUDA上使用FP16

        # 加载模型
        self.model = self._load_model()

        # 获取类别名称和颜色
        self.names = self.model.module.names if hasattr(self.model, 'module') else self.model.names
        self.colors = [[random.randint(0, 255) for _ in range(3)] for _ in self.names]

        # 模型预热
        self._warmup_model()

    def _load_model(self):
        """加载YOLOv7模型，完全遵循原始检测代码逻辑"""
        # 检查权重文件
        if not Path(self.weights).exists():
            raise FileNotFoundError(f"模型权重文件不存在: {self.weights}")

        # 加载FP32模型
        model = attempt_load(self.weights, map_location=self.device)
        self.stride = int(model.stride.max())  # 模型步长

        # 检查图像尺寸
        self.img_size = check_img_size(self.img_size, s=self.stride)

        # 模型追踪
        if self.trace:
            model = TracedModel(model, self.device, self.img_size)

        # 转换为FP16
        if self.half:
            model.half()

        return model

    def _warmup_model(self):
        """模型预热，确保首次推理速度正常"""
        if self.device.type != 'cpu':
            # 生成随机输入进行预热
            img = torch.zeros(1, 3, self.img_size, self.img_size).to(self.device)
            img = img.half() if self.half else img.float()
            # 多次前向传播进行预热
            for _ in range(3):
                self.model(img, augment=False)[0]

    def preprocess(self, frame):
        """
        预处理图像，适配YOLOv7输入要求（保持比例缩放并填充黑边）
        :param frame: 原始BGR图像 (cv2读取)
        :return: 处理后的张量, 缩放比例, 填充尺寸
        """
        # 记录原始图像尺寸
        h, w = frame.shape[:2]

        # 计算缩放比例（保持宽高比）
        scale = min(self.img_size / h, self.img_size / w)
        new_h, new_w = int(h * scale), int(w * scale)

        # 缩放图像
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        # 计算填充量
        pad_h = self.img_size - new_h
        pad_w = self.img_size - new_w
        top, bottom = pad_h // 2, pad_h - (pad_h // 2)
        left, right = pad_w // 2, pad_w - (pad_w // 2)

        # 填充黑边
        img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=[0, 0, 0])

        # 转换为张量
        img = img.transpose(2, 0, 1)  # (3, img_size, img_size)
        img = torch.from_numpy(img).to(self.device)
        img = img.half() if self.half else img.float()
        img /= 255.0

        if img.ndimension() == 3:
            img = img.unsqueeze(0)  # (1, 3, img_size, img_size)

        # 返回预处理后的图像、缩放比例和填充尺寸
        return img, scale, (top, left)

    def detect(self, frame):
        """
        检测图像中的车辆
        :param frame: 原始BGR图像 (cv2读取)
        :return: 检测结果 (标签列表和边界框列表)
                 标签格式: [类别名称+置信度, ...]
                 边界框格式: [(x1, y1, x2, y2), ...] (坐标为原始图像中的像素位置)
        """
        # 图像预处理（获取缩放比例和填充信息）
        img, scale, (pad_top, pad_left) = self.preprocess(frame)
        im0 = frame.copy()  # 原始图像备份

        # 推理
        with torch.no_grad():
            pred = self.model(img, augment=False)[0]

        # 应用NMS，只保留车辆类别
        pred = non_max_suppression(
            pred,
            self.conf_thres,
            self.iou_thres,
            classes=self.VEHICLE_CLASSES,
            agnostic=False
        )

        # 处理检测结果
        labels = []
        boxes = []

        for det in pred:  # 遍历每个图像的检测结果
            if len(det):
                # 将边界框从img_size缩放回原始图像尺寸
                for *xyxy, conf, cls in reversed(det):
                    # 转换为原始图像坐标（考虑填充和缩放）
                    x1 = int((xyxy[0].item() - pad_left) / scale)
                    y1 = int((xyxy[1].item() - pad_top) / scale)
                    x2 = int((xyxy[2].item() - pad_left) / scale)
                    y2 = int((xyxy[3].item() - pad_top) / scale)

                    # 边界检查
                    x1 = max(0, x1)
                    y1 = max(0, y1)
                    x2 = min(im0.shape[1] - 1, x2)
                    y2 = min(im0.shape[0] - 1, y2)

                    # 边界框校准（微调）
                    if self.box_correction:
                        x1, y1, x2, y2 = self._correct_box((x1, y1, x2, y2), cls.item())

                    boxes.append((x1, y1, x2, y2))
                    labels.append(f'{self.names[int(cls)]} {conf:.2f}')

        return labels, boxes

    def _correct_box(self, box, cls_id):
        """
        边界框校准函数（根据不同类别微调边界框位置）
        :param box: 原始边界框 (x1, y1, x2, y2)
        :param cls_id: 类别ID
        :return: 校准后的边界框
        """
        x1, y1, x2, y2 = box

        # 根据不同类别设置不同的校准参数（示例值，需根据实际情况调整）
        if cls_id == 2:  # 汽车
            y1 = max(0, y1 - 5)  # 上移5像素
            y2 = min(y2 + 5, 10000)  # 下移5像素
        elif cls_id == 5:  # 公交车
            y1 = max(0, y1 - 10)  # 上移10像素
            y2 = min(y2 + 5, 10000)  # 下移5像素

        return x1, y1, x2, y2

    def draw_detections(self, frame, labels, boxes):
        """
        在图像上绘制检测结果
        :param frame: 原始BGR图像
        :param labels: 标签列表
        :param boxes: 边界框列表
        :return: 绘制后的图像
        """
        im0 = frame.copy()
        for label, (x1, y1, x2, y2) in zip(labels, boxes):
            # 提取类别ID
            cls_name = label.split()[0]
            cls_id = self.names.index(cls_name)

            # 绘制边界框
            color = self.colors[cls_id]
            cv2.rectangle(im0, (x1, y1), (x2, y2), color, 2)

            # 绘制标签背景和文字
            label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
            label_w, label_h = label_size
            cv2.rectangle(im0, (x1, y1 - label_h - 10), (x1 + label_w, y1), color, -1)
            cv2.putText(im0, label, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        return im0