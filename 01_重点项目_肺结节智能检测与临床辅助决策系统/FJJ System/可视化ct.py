import SimpleITK as sitk
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path


def visualize_lung_ct_slice(input_path, slice_idx):
    """
    显示肺部CT切片（无标注框，无颜色条）

    Args:
        input_path: CT图像路径 (.mhd文件)
        slice_idx: 要显示的切片索引
    """
    # 读取CT数据
    input_image = sitk.ReadImage(input_path)
    input_array = sitk.GetArrayFromImage(input_image)  # 形状: [切片数, 高, 宽]
    spacing = np.array(input_image.GetSpacing())
    origin = np.array(input_image.GetOrigin())

    print(f"CT图像形状: {input_array.shape}")
    print(f"体素间距(x,y,z): {spacing.round(3)} mm/像素")
    print(f"原点坐标: {origin}")

    # 检查切片索引有效性
    max_slice = input_array.shape[0] - 1
    if slice_idx < 0 or slice_idx > max_slice:
        print(f"切片索引无效,有效范围：0~{max_slice}")
        return

    # 获取指定切片的原始数据
    ct_slice = input_array[slice_idx]

    # 应用肺部专用HU窗口调整
    lung_window_min = -1350
    lung_window_max = 150
    ct_windowed = np.clip(ct_slice, lung_window_min, lung_window_max)
    ct_normalized = (ct_windowed - lung_window_min) / (lung_window_max - lung_window_min)

    # 创建图像
    fig, ax = plt.subplots(1, 1, figsize=(10, 10))

    # 显示CT图像
    ax.imshow(ct_normalized, cmap='gray')
    ax.set_title(f'肺部CT切片 (索引: {slice_idx})', fontsize=14)
    ax.axis('off')

    plt.tight_layout()
    plt.show()

    return ct_slice


def visualize_lung_ct_slice_with_window(input_path, slice_idx, window_center=-600, window_width=1500):
    """
    显示肺部CT切片（可自定义窗宽窗位，无颜色条）

    Args:
        input_path: CT图像路径 (.mhd文件)
        slice_idx: 要显示的切片索引
        window_center: 窗位中心（默认-600，肺窗）
        window_width: 窗宽（默认1500，肺窗）
    """
    # 读取CT数据
    input_image = sitk.ReadImage(input_path)
    input_array = sitk.GetArrayFromImage(input_image)
    spacing = np.array(input_image.GetSpacing())

    print(f"CT图像形状: {input_array.shape}")
    print(f"体素间距(x,y,z): {spacing.round(3)} mm/像素")

    # 检查切片索引有效性
    max_slice = input_array.shape[0] - 1
    if slice_idx < 0 or slice_idx > max_slice:
        print(f"切片索引无效,有效范围：0~{max_slice}")
        return

    # 获取指定切片
    ct_slice = input_array[slice_idx]

    # 应用自定义窗宽窗位
    min_bound = window_center - window_width / 2
    max_bound = window_center + window_width / 2
    ct_windowed = np.clip(ct_slice, min_bound, max_bound)
    ct_normalized = (ct_windowed - min_bound) / (max_bound - min_bound)

    # 显示图像
    fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    ax.imshow(ct_normalized, cmap='gray')
    ax.set_title(f'肺部CT切片 (索引: {slice_idx}) | 窗宽: {window_width}, 窗位: {window_center}', fontsize=12)
    ax.axis('off')
    plt.tight_layout()
    plt.show()

    return ct_slice


def display_multiple_slices(input_path, slice_indices, cols=4):
    """
    显示多个CT切片（无颜色条）

    Args:
        input_path: CT图像路径
        slice_indices: 要显示的切片索引列表
        cols: 每行显示的图像数量
    """
    # 读取CT数据
    input_image = sitk.ReadImage(input_path)
    input_array = sitk.GetArrayFromImage(input_image)

    # 计算行数
    n_slices = len(slice_indices)
    rows = (n_slices + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(cols * 4, rows * 4))
    if rows == 1 and cols == 1:
        axes = np.array([axes])
    axes = axes.flatten()

    lung_window_min = -1350
    lung_window_max = 150

    for i, slice_idx in enumerate(slice_indices):
        if slice_idx < 0 or slice_idx >= input_array.shape[0]:
            continue

        ct_slice = input_array[slice_idx]
        ct_windowed = np.clip(ct_slice, lung_window_min, lung_window_max)
        ct_normalized = (ct_windowed - lung_window_min) / (lung_window_max - lung_window_min)

        axes[i].imshow(ct_normalized, cmap='gray')
        axes[i].set_title(f'切片 {slice_idx}', fontsize=10)
        axes[i].axis('off')

    # 隐藏多余的子图
    for i in range(n_slices, len(axes)):
        axes[i].axis('off')

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    # CT图像路径
    INPUT_PATH = "FJJ System\曾玉香"

    # 要显示的切片索引
    slice_idx = 1

    print(f"显示切片索引: {slice_idx}")

    # 显示单张切片
    visualize_lung_ct_slice(INPUT_PATH, slice_idx)


