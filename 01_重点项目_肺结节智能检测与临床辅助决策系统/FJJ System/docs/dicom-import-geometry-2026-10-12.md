# DICOM 序列读入与空间几何修正

2026-10-12。旧 `engine.py` 与预测导出脚本对 `GetGDCMSeriesFileNames` 返回的列表强制 `[::-1]`。根据 [SimpleITK 官方 DICOM Series Reader 文档](https://simpleitk.readthedocs.io/en/latest/link_DicomSeriesReader_docs.html)，该接口提供沿扫描方向排序的文件名；再次反转会使读入体积方向与后续物理坐标转换存在风险。

现在由 `dicom_io.load_ct_image` 统一读取 MHD 或 DICOM。DICOM 使用 GDCM 返回的顺序，不再反转；目录有多套 series 时直接报错，要求明确选择，以免误把不同重建或不同时间点混在一起。`engine.load_itk` 与 `experiments/export_luna_predictions.py` 已共享该入口。

验证：合成 3 层 CT，文件名字母顺序故意与物理 z 顺序相反；读取结果切片值为 10、20、30，对应 z=0、2、4 mm，层距 2 mm。另覆盖多序列与空目录异常。项目测试套件 100 项通过。合成测试只证明基本层序与间距；真实医院 DICOM 仍需检查增强序列、多帧对象、不规则间距、混合序列和烧录信息，并由影像科医生核对解剖方向。已上传旧病例的缓存预览应重建后再使用，不能把旧坐标原样迁移。
