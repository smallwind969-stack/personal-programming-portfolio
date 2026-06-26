"""
@BelongsProject: AgentProject
@BelongsPackage: 
@Author: 蔡张君逸
@CreateTime: 2026-05-14 15:19
@Description: TODO
@Version: 1.
"""
import pydicom
import matplotlib.pyplot as plt
from pydicom.pixels import apply_modality_lut, apply_voi_lut
from PIL import Image
import numpy as np
file_name="DJ001"
ds = pydicom.dcmread("data/曾xx/"+file_name+".dcm")

# print(ds)                 # 打印 DICOM 元数据
# print(ds.PatientID)       # 患者 ID，如果有
# print(ds.Modality)        # CT / MR / CR / DX 等
# print(ds.Rows, ds.Columns)

img = ds.pixel_array      # numpy array
# print(img.shape, img.dtype)

# print(img.min(), img.max())
# plt.imshow(img, cmap="gray")
# plt.axis("off")
# plt.show()
# print(img)

# （-3000，-1000）映射到0,255.unit-8是8位整数类型，取值范围仅0-255
def normalize_to_uint8(arr):
    img=arr
    arr = arr.astype(np.float32)
    arr -= arr.min()
    if arr.max() > 0:
        arr /= arr.max()
    # return (arr * 255).astype(np.uint8)
    a=255*arr
    print(a)
    FIXED_WW = 1500
    ww=FIXED_WW
    FIXED_WL = -600
    wl = FIXED_WL
    min_val, max_val = wl - ww / 2, wl + ww / 2
    windowed_slice = np.clip(img, min_val, max_val)
    windowed_slice = 255 * (windowed_slice - min_val) / (max_val - min_val)
    print(windowed_slice)
    print(a==windowed_slice)
    return windowed_slice.astype(np.uint8)
img8 = normalize_to_uint8(img)


Image.fromarray(img8).save("transformed/曾xx/"+file_name+".png")
plt.imshow(img8)
