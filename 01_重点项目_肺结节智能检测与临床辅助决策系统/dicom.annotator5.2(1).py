import sys
import os
import pydicom
import numpy as np
import pandas as pd
import re  # 导入re模块用于文件名清理

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSlider, QFileDialog, QGroupBox,
    QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPen, QColor

# --- 全局常量 ---
APP_VERSION = "2.3.0 (2025-11-05)"  # 更新版本号和日期
FIXED_WW = 1500
FIXED_WL = -600

# CSV值 -> 颜色
LABEL_COLORS = {
    0: QColor(0, 255, 0, 180),  # 非肿瘤性: 绿色
    1: QColor(255, 255, 0, 180),  # 癌前病变: 黄色
    2: QColor(255, 0, 0, 180),  # 肿瘤性病变: 红色
    -100: QColor(0, 0, 255, 180)  # 无法确定: 蓝色
}
# CSV值 -> 中文名称 (用于UI显示)
CHINESE_LABEL_MAP = {
    0: "非肿瘤性",
    1: "癌前病变（不典型腺瘤样增生，原位腺癌）",
    2: "肿瘤性病变",
    -100: "无法确定"
}
# CSV值 -> 英文名称 (用于CSV文件)
ENGLISH_LABEL_MAP = {
    0: "Non-neoplastic",
    1: "Premalignant lesion",
    2: "Neoplastic lesion",
    -100: "Undecided"
}


# ==============================================================================
#  交互式图像标签类 (已修改 paintEvent 方法)
# ==============================================================================
class InteractiveLabel(QLabel):
    """一个可以响应鼠标事件以绘制矩形的自定义QLabel"""
    new_rect_drawn = pyqtSignal(QRect)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.drawing = False
        self.start_point = QPoint()
        self.end_point = QPoint()
        self.annotations_on_slice = []
        self.image_size = QSize(0, 0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)  # 允许图像标签扩展
        # 移除或确保不使用 self.setScaledContents(True)，因为我们将手动处理缩放和绘图

    def set_annotations(self, annotations, image_size):
        self.annotations_on_slice = annotations
        self.image_size = QSize(image_size[1], image_size[0]) # 注意：PIL/numpy是(height, width)，QImage是(width, height)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = True
            self.start_point = event.pos()
            self.end_point = event.pos()

    def mouseMoveEvent(self, event):
        if self.drawing:
            self.end_point = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.drawing:
            self.drawing = False
            widget_rect = QRect(self.start_point, self.end_point).normalized()
            # 过滤掉过小的矩形，避免误触
            if widget_rect.width() < 5 or widget_rect.height() < 5:
                self.update()
                return

            image_rect = self.map_widget_to_image(widget_rect)
            if image_rect.width() > 2 and image_rect.height() > 2:  # 再次过滤，确保映射后的实际尺寸也足够
                self.new_rect_drawn.emit(image_rect)
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing) # 可选：让绘制的线条更平滑

        current_pixmap = self.pixmap() # 获取 QLabel 中存储的原始 QPixmap

        if current_pixmap and not current_pixmap.isNull():
            # 1. 将原始 pixmap 缩放到 QLabel 的当前大小，并保持长宽比
            scaled_pixmap = current_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

            # 2. 计算缩放后图片在 QLabel 中的居中位置
            x = (self.width() - scaled_pixmap.width()) / 2
            y = (self.height() - scaled_pixmap.height()) / 2

            # 3. 绘制缩放后的图片
            painter.drawPixmap(int(x), int(y), scaled_pixmap)

            # 4. 绘制所有已有的标注框
            for annotation in self.annotations_on_slice:
                rect_coords = annotation['rect']
                label_id = annotation['label']
                image_rect = QRect(*rect_coords)
                widget_rect = self.map_image_to_widget(image_rect)
                pen_color = LABEL_COLORS.get(label_id, QColor(255, 255, 255, 180))  # 默认为白色
                pen = QPen(pen_color, 2)
                painter.setPen(pen)
                painter.drawRect(widget_rect)

            # 5. 如果正在绘制新矩形，绘制临时虚线框
            if self.drawing:
                pen = QPen(QColor(255, 255, 255, 200), 1, Qt.PenStyle.DashLine)
                painter.setPen(pen)
                painter.drawRect(QRect(self.start_point, self.end_point))
        else:
            # 如果没有图片，则调用父类的 paintEvent 来绘制 QLabel 的文本（例如“请打开DICOM文件夹开始标注”）
            super().paintEvent(event)

    def map_widget_to_image(self, widget_rect: QRect) -> QRect:
        if self.pixmap() is None or self.image_size.isEmpty():
            return QRect()

        current_pixmap = self.pixmap()
        # 获取当前实际显示的图片大小和位置
        # 注意：QLabel.pixmap() 返回的是原始大小的pixmap，需要再次 scaled 才能得到显示的实际大小
        scaled_pixmap = current_pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                              Qt.TransformationMode.SmoothTransformation)

        scaled_width = scaled_pixmap.width()
        scaled_height = scaled_pixmap.height()

        # 计算图片在QLabel中的偏移量 (居中)
        offset_x = (self.width() - scaled_width) / 2
        offset_y = (self.height() - scaled_height) / 2

        # 计算从widget坐标到实际图片像素的缩放比例
        if scaled_width == 0 or scaled_height == 0 or self.image_size.width() == 0 or self.image_size.height() == 0:
            return QRect()

        scale_x = self.image_size.width() / scaled_width
        scale_y = self.image_size.height() / scaled_height

        img_x = int((widget_rect.x() - offset_x) * scale_x)
        img_y = int((widget_rect.y() - offset_y) * scale_y)
        img_w = int(widget_rect.width() * scale_x)
        img_h = int(widget_rect.height() * scale_y)

        # 裁剪到图像边界内
        img_x = max(0, min(img_x, self.image_size.width() - 1))
        img_y = max(0, min(img_y, self.image_size.height() - 1))
        img_w = max(1, min(img_w, self.image_size.width() - img_x))  # 确保宽度至少为1
        img_h = max(1, min(img_h, self.image_size.height() - img_y))  # 确保高度至少为1

        return QRect(img_x, img_y, img_w, img_h)

    def map_image_to_widget(self, image_rect: QRect) -> QRect:
        if self.pixmap() is None or self.image_size.isEmpty():
            return QRect()

        current_pixmap = self.pixmap()
        scaled_pixmap = current_pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                              Qt.TransformationMode.SmoothTransformation)

        scaled_width = scaled_pixmap.width()
        scaled_height = scaled_pixmap.height()

        # 计算图片在QLabel中的偏移量 (居中)
        offset_x = (self.width() - scaled_width) / 2
        offset_y = (self.height() - scaled_height) / 2

        if self.image_size.width() == 0 or self.image_size.height() == 0:
            return QRect()

        scale_x = scaled_width / self.image_size.width()
        scale_y = scaled_height / self.image_size.height()

        widget_x = int(image_rect.x() * scale_x + offset_x)
        widget_y = int(image_rect.y() * scale_y + offset_y)
        widget_w = int(image_rect.width() * scale_x)
        widget_h = int(image_rect.height() * scale_y)

        # 裁剪到QLabel显示区域内
        widget_x = max(0, widget_x)
        widget_y = max(0, widget_y)
        widget_w = min(self.width() - widget_x, widget_w)
        widget_h = min(self.height() - widget_y, widget_h)

        return QRect(widget_x, widget_y, widget_w, widget_h)


# ==============================================================================
#  主窗口类
# ==============================================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.dicom_files = []  # 存储加载的DICOM文件完整路径
        self.dicom_basenames = []  # 存储DICOM文件的basename (不含.dcm后缀)
        self.dicom_stack = None
        self.annotations = []
        self.series_uid = ""
        self.display_id = ""
        self.current_slice_index = 0
        self.ww = FIXED_WW
        self.wl = FIXED_WL
        self.chinese_label_map = CHINESE_LABEL_MAP
        self.english_label_map = ENGLISH_LABEL_MAP
        self.current_drawing_label = 0
        self.current_dicom_folder_path = ""  # 用于保存CSV的默认路径

        self.setWindowTitle(f"DICOM 肺结节标注工具 - v{APP_VERSION}")
        self.setGeometry(100, 100, 1200, 800)
        self.initUI()
        self.update_controls_state(enabled=False)

    def initUI(self):
        main_layout = QHBoxLayout()
        left_panel = QVBoxLayout()
        right_panel = QVBoxLayout()

        # --- 右侧控制面板 ---
        # 文件操作
        file_group = QGroupBox("文件操作")
        file_layout = QHBoxLayout()
        self.open_button = QPushButton("打开DICOM文件夹")
        self.open_button.clicked.connect(self.open_folder)
        self.save_button = QPushButton("保存标注 (CSV)")
        self.save_button.clicked.connect(self.save_annotations)
        file_layout.addWidget(self.open_button)
        file_layout.addWidget(self.save_button)
        file_group.setLayout(file_layout)

        # 序列信息 & 窗宽窗位
        series_info_group = QGroupBox("序列信息与窗宽窗位")
        series_info_layout = QVBoxLayout()  # 使用垂直布局

        # 窗宽窗位信息
        self.wwl_info_label = QLabel(f"固定肺窗: WW {self.ww} / WL {self.wl}")
        self.wwl_info_label.setStyleSheet("font-weight: bold;")
        series_info_layout.addWidget(self.wwl_info_label)

        # 层面信息
        self.slice_info_label = QLabel("层面: - / -")
        self.slice_info_label.setStyleSheet("font-weight: bold;")
        series_info_layout.addWidget(self.slice_info_label)

        # 当前层面标注数量
        self.slice_annotation_info = QLabel("当前层面标注: -")
        series_info_layout.addWidget(self.slice_annotation_info)
        series_info_group.setLayout(series_info_layout)

        annotation_group = QGroupBox("标注操作")
        annotation_layout = QVBoxLayout()
        self.drawing_label_status = QLabel()

        self.btn_set_type0 = QPushButton("设为: 非肿瘤性 (绿色)")
        self.btn_set_type1 = QPushButton("设为: 癌前病变 (黄色)")
        self.btn_set_type2 = QPushButton("设为: 肿瘤性病变 (红色)")
        self.btn_set_type_unknown = QPushButton("设为: 无法确定 (蓝色)")
        self.btn_clear_slice = QPushButton("清除当前层面所有标注")

        self.btn_set_type0.clicked.connect(lambda: self.set_drawing_label(0))
        self.btn_set_type1.clicked.connect(lambda: self.set_drawing_label(1))
        self.btn_set_type2.clicked.connect(lambda: self.set_drawing_label(2))
        self.btn_set_type_unknown.clicked.connect(lambda: self.set_drawing_label(-100))
        self.btn_clear_slice.clicked.connect(self.clear_slice_annotations)

        annotation_layout.addWidget(self.drawing_label_status)
        annotation_layout.addWidget(self.btn_set_type0)
        annotation_layout.addWidget(self.btn_set_type1)
        annotation_layout.addWidget(self.btn_set_type2)
        annotation_layout.addWidget(self.btn_set_type_unknown)
        annotation_layout.addSpacing(10)
        annotation_layout.addWidget(self.btn_clear_slice)
        annotation_group.setLayout(annotation_layout)

        right_panel.addWidget(file_group)
        right_panel.addWidget(series_info_group)  # 添加新的序列信息组
        right_panel.addWidget(annotation_group)
        right_panel.addStretch()

        # --- 左侧图像显示面板 ---
        self.image_label = InteractiveLabel("请打开DICOM文件夹开始标注")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(600, 600)
        self.image_label.setStyleSheet("background-color: black; color: white;")
        self.image_label.new_rect_drawn.connect(self.add_new_annotation)
        # 图像标签应尽可能占据可用空间
        # !!! 关键修改: 给 image_label 一个拉伸因子，让它占据大部分垂直空间 !!!
        left_panel.addWidget(self.image_label, 1) # 这里是修改点

        # 层面滑动条和导航按钮
        slice_nav_layout = QHBoxLayout()
        self.prev_slice_button = QPushButton("上一张")
        self.next_slice_button = QPushButton("下一张")
        self.prev_slice_button.clicked.connect(self.prev_slice)
        self.next_slice_button.clicked.connect(self.next_slice)

        self.slice_slider = QSlider(Qt.Orientation.Horizontal)
        self.slice_slider.valueChanged.connect(self.change_slice)
        self.slice_slider.setMinimumWidth(300)  # 给滑动条一个最小宽度

        slice_nav_layout.addWidget(self.prev_slice_button)
        slice_nav_layout.addWidget(self.slice_slider)
        slice_nav_layout.addWidget(self.next_slice_button)
        left_panel.addLayout(slice_nav_layout)

        # 移除原有的 left_panel.addStretch(1)，因为它会导致 image_label 上方有空余空间
        # 现在 image_label 自身的拉伸因子会处理空间分配

        main_layout.addLayout(left_panel, 3)  # 左侧占比3
        main_layout.addLayout(right_panel, 1)  # 右侧占比1

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        self.set_drawing_label(0)

    def open_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "选择DICOM文件夹")
        if not folder_path: return

        self.current_dicom_folder_path = folder_path  # 保存当前选定的DICOM文件夹路径

        try:
            self.load_dicom_series(folder_path)
            self.update_controls_state(enabled=True)
            self.current_slice_index = 0
            self.slice_slider.setRange(0, len(self.dicom_files) - 1)
            self.slice_slider.setValue(self.current_slice_index)
            self.update_image()
        except Exception as e:
            QMessageBox.critical(self, "加载错误", f"无法加载DICOM序列:\n{str(e)}")
            self.update_controls_state(enabled=False)
            # 清空状态
            self.dicom_files = []
            self.dicom_basenames = []
            self.dicom_stack = None
            self.annotations = []
            self.series_uid = ""
            self.display_id = ""
            self.slice_info_label.setText("层面: - / -")
            self.slice_annotation_info.setText("当前层面标注: -")

    def _get_cleaned_dcm_files(self, folder_path):
        """
        扫描文件夹中的.dcm文件，并过滤掉类似 `file(1).dcm` 的重复文件。
        优先保留没有 `(N)` 后缀的文件。
        """
        all_files_raw = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.lower().endswith('.dcm')]

        if not all_files_raw:
            return []

        # 使用字典来存储每个“基名”对应的最佳文件路径
        # key: 剔除 "(N)" 后缀的文件名（不含扩展名）
        # value: 完整的最佳文件路径
        unique_files_map = {}

        for f_path in all_files_raw:
            basename = os.path.basename(f_path)
            name_stem, ext = os.path.splitext(
                basename)  # 例如: '95189551_20211108_201_531' 或 '95189551_20211108_201_531(1)'

            # 提取不包含 "(N)" 的规范文件名，用于比较
            canonical_stem = re.sub(r'\(\d+\)$', '', name_stem)

            if canonical_stem not in unique_files_map:
                # 第一次遇到这个规范文件名，直接添加
                unique_files_map[canonical_stem] = f_path
            else:
                # 已经有一个文件对应这个规范文件名了，需要判断哪个更好
                existing_f_path = unique_files_map[canonical_stem]
                existing_basename = os.path.basename(existing_f_path)
                existing_name_stem = os.path.splitext(existing_basename)[0]

                # 如果现有文件带有 "(N)" 后缀，而新文件没有，则优先使用新文件
                if re.search(r'\(\d+\)$', existing_name_stem) and not re.search(r'\(\d+\)$', name_stem):
                    unique_files_map[canonical_stem] = f_path
                # 如果两个都带(N)或都不带(N)，则保留先遇到的那个（即unique_files_map中已有的）
                # 否则，如果新文件带(N)而现有文件不带(N)，则保持现有文件不变

        return list(unique_files_map.values())

    def load_dicom_series(self, folder_path):
        filtered_files = self._get_cleaned_dcm_files(folder_path)
        if not filtered_files:
            raise ValueError("文件夹中未找到有效DICOM文件")

        # 尝试读取DCM文件，并过滤掉无法解析为DCM的非DCM文件
        dicom_objects_raw = []
        for f in filtered_files:
            try:
                # 先尝试读取元数据以检查InstanceNumber，然后读取完整DCM
                ds_meta = pydicom.dcmread(f, stop_before_pixels=True)
                if hasattr(ds_meta, 'InstanceNumber'):  # 确保有InstanceNumber才能排序
                    dicom_objects_raw.append(pydicom.dcmread(f))  # 再次读取完整DCM，包含像素数据
                else:
                    print(f"警告: 文件 {os.path.basename(f)} 缺少InstanceNumber，已跳过。")
            except Exception as e:
                print(f"警告: 无法读取或解析文件 {os.path.basename(f)} 为DICOM文件，已跳过。错误: {e}")

        if not dicom_objects_raw:
            raise ValueError("在选定文件夹中未找到可用于加载和排序的DICOM图像文件。")

        # 按照InstanceNumber排序
        dicom_objects_raw.sort(key=lambda x: int(x.InstanceNumber))

        self.dicom_files = [d.filename for d in dicom_objects_raw]
        self.dicom_basenames = [os.path.splitext(os.path.basename(f))[0] for f in self.dicom_files]  # 存储不带后缀的文件名

        self.display_id = os.path.basename(folder_path)
        self.series_uid = dicom_objects_raw[0].SeriesInstanceUID if hasattr(dicom_objects_raw[0],
                                                                            'SeriesInstanceUID') else self.display_id

        stack = []
        for dcm in dicom_objects_raw:
            pixels = dcm.pixel_array.astype(np.float32)
            if hasattr(dcm, 'RescaleSlope') and hasattr(dcm, 'RescaleIntercept'):
                slope = float(dcm.RescaleSlope)
                intercept = float(dcm.RescaleIntercept)
                pixels = pixels * slope + intercept
            stack.append(pixels)

        self.dicom_stack = np.stack(stack, axis=0)
        self.annotations = [[] for _ in range(len(self.dicom_files))]
        print(f"成功加载 {len(self.dicom_files)} 个层面。Series UID: {self.series_uid}")

    def apply_windowing(self, image_slice, ww, wl):
        min_val, max_val = wl - ww / 2, wl + ww / 2
        windowed_slice = np.clip(image_slice, min_val, max_val)
        windowed_slice = 255 * (windowed_slice - min_val) / (max_val - min_val)
        return windowed_slice.astype(np.uint8)

    def update_image(self):
        if self.dicom_stack is None or len(self.dicom_files) == 0:
            self.image_label.clear()
            self.image_label.setText("请打开DICOM文件夹开始标注")
            self.slice_info_label.setText("层面: - / -")
            self.slice_annotation_info.setText("当前层面标注: -")
            return

        current_slice_data = self.dicom_stack[self.current_slice_index]
        img_8bit = self.apply_windowing(current_slice_data, self.ww, self.wl)

        height, width = img_8bit.shape
        # QImage 默认使用 ByteOrder.Native 格式，对于 Grayscale8， width 即 bytesPerLine
        q_image = QImage(img_8bit.data, width, height, width, QImage.Format.Format_Grayscale8)
        pixmap = QPixmap.fromImage(q_image)
        self.image_label.setPixmap(pixmap)

        current_annotations = self.annotations[self.current_slice_index]
        self.image_label.set_annotations(current_annotations, current_slice_data.shape)

        self.slice_info_label.setText(f"层面: {self.current_slice_index + 1} / {len(self.dicom_files)}")
        self.slice_annotation_info.setText(f"当前层面标注: {len(current_annotations)}个")

    def change_slice(self, value):
        if self.dicom_stack is None or len(self.dicom_files) == 0:
            return
        self.current_slice_index = value
        self.update_image()

    def prev_slice(self):
        if self.dicom_stack is not None and self.current_slice_index > 0:
            self.slice_slider.setValue(self.current_slice_index - 1)

    def next_slice(self):
        if self.dicom_stack is not None and self.current_slice_index < len(self.dicom_files) - 1:
            self.slice_slider.setValue(self.current_slice_index + 1)

    def wheelEvent(self, event):
        # 只有当鼠标在image_label上且dicom_stack已加载时才响应滚轮事件
        if self.image_label.underMouse() and self.dicom_stack is not None:
            delta = event.angleDelta().y()
            if delta > 0:
                self.prev_slice()
            elif delta < 0:
                self.next_slice()
        else:
            # 如果鼠标不在image_label上，将事件传递给父类处理，允许滚动其他可滚动的组件
            super().wheelEvent(event)

    def set_drawing_label(self, label_value):
        """设置即将绘制的标注框的类型，并更新状态标签"""
        self.current_drawing_label = label_value
        label_name = self.chinese_label_map.get(label_value, "未知")

        self.drawing_label_status.setText(f"绘图类型: {label_name}")
        self.drawing_label_status.setStyleSheet("font-weight: bold; color: black;")  # 固定文字颜色为黑色，只加粗

    def add_new_annotation(self, image_rect: QRect):
        if self.dicom_stack is None: return
        new_annotation = {
            'rect': (image_rect.x(), image_rect.y(), image_rect.width(), image_rect.height()),
            'label': self.current_drawing_label
        }
        self.annotations[self.current_slice_index].append(new_annotation)
        print(f"层面 {self.current_slice_index + 1}: 新增标注 {new_annotation}")
        self.update_image()

    def clear_slice_annotations(self):
        if self.dicom_stack is None or not self.annotations[self.current_slice_index]:
            QMessageBox.information(self, "无标注", "当前层面没有标注可清除。")
            return

        reply = QMessageBox.question(self, '确认清除', '您确定要清除当前层面的所有标注吗？',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.annotations[self.current_slice_index] = []
            print(f"层面 {self.current_slice_index + 1} 的所有标注已清除。")
            self.update_image()

    def _sanitize_filename_component(self, name):
        """清理字符串，使其适合作为文件名的一部分，替换非法字符为下划线"""
        # 只保留字母、数字、下划线和连字符，其他替换为下划线
        sanitized = re.sub(r'[^\w-]', '_', name)
        return sanitized

    def save_annotations(self):
        if not self.dicom_files:
            QMessageBox.warning(self, "无法保存", "没有加载DICOM数据，无法保存标注。")
            return

        # 1. 获取 ID（使用文件夹名称），并清理用于文件名
        identifier_for_filename = self.display_id if self.display_id else self.series_uid
        sanitized_id = self._sanitize_filename_component(identifier_for_filename)

        # 2. 获取切片总数
        total_slices = len(self.dicom_files)

        # 3. 计算被标记的切片数量
        labeled_slices_count = 0
        if self.annotations:
            for slice_annotations in self.annotations:
                if slice_annotations:
                    labeled_slices_count += 1

        # 4. 构建默认文件名
        default_filename = f"ID{sanitized_id}-SlicesAll{total_slices}-Labeled{labeled_slices_count}.csv"

        # 5. 设置默认保存路径为DICOM文件夹的父目录
        save_directory = os.path.dirname(
            self.current_dicom_folder_path) if self.current_dicom_folder_path else os.getcwd()
        full_default_path = os.path.join(save_directory, default_filename)

        file_path, _ = QFileDialog.getSaveFileName(self, "保存标注文件", full_default_path, "CSV Files (*.csv)")
        if not file_path: return

        try:
            data_to_save = []
            for slice_idx, slice_annotations in enumerate(self.annotations):
                if slice_annotations:
                    for annot in slice_annotations:
                        rect = annot['rect']
                        data_to_save.append({
                            "SeriesUID": self.series_uid,
                            "SliceIndex": slice_idx + 1,  # SliceIndex 从 1 开始
                            "DicomFilename": self.dicom_basenames[slice_idx],  # 新增文件名列
                            "Label": annot['label'],
                            "LabelName": self.english_label_map[annot['label']],  # 使用英文标注名称
                            "x": rect[0],
                            "y": rect[1],
                            "width": rect[2],
                            "height": rect[3]
                        })

            if not data_to_save:
                QMessageBox.information(self, "无标注", "没有需要保存的标注信息。")
                return

            df = pd.DataFrame(data_to_save)
            df.to_csv(file_path, index=False, encoding='utf-8-sig')  # 显式指定编码以支持中文
            QMessageBox.information(self, "保存成功", f"标注已成功保存到:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存文件时发生错误:\n{str(e)}")

    def update_controls_state(self, enabled: bool):
        self.save_button.setEnabled(enabled)
        self.slice_slider.setEnabled(enabled)
        self.prev_slice_button.setEnabled(enabled)
        self.next_slice_button.setEnabled(enabled)

        self.btn_set_type0.setEnabled(enabled)
        self.btn_set_type1.setEnabled(enabled)
        self.btn_set_type2.setEnabled(enabled)
        self.btn_set_type_unknown.setEnabled(enabled)
        self.btn_clear_slice.setEnabled(enabled)

    def resizeEvent(self, event):
        # 窗口大小改变时，重新绘制图像以适应新的 QLabel 大小
        if self.dicom_stack is not None:
            self.update_image() # 重新调用 update_image 会触发 image_label 的 update，从而调用 paintEvent
        super().resizeEvent(event)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())