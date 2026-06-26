import cv2

from apig_sdk import signer
import requests
import  json
import os
if __name__ == '__main__':
    # Config url, ak, sk and file path.
    url = "https://infer-modelarts-cn-north-4.modelarts-infer.com/v1/infers/3c3d55f4-35a4-479f-afbd-a2b6c42862cf"
    # 认证用的ak和sk硬编码到代码中或者明文存储都有很大的安全风险,建议在配置文件或者环境变量中密文存放,使用时解密,确保安全;
    # 本示例以ak和sk保存在环境变量中来实现身份验证为例,运行本示例前请先在本地环境中设置环境变量HUAWEICLOUD_SDK_AK和HUAWEICLOUD_SDK_SK。
    ak = 'HPUAPUJSGRL1CYGS80K7'
    sk = 'AmVPucyjjNLFXyPg1kx8IkLFUvua87wFmjnY2lPX'
    file_path = "./images/hat.jpg"

    # Create request, set method, url, headers and body.
    method = 'POST'
    headers = {"x-sdk-content-sha256": "UNSIGNED-PAYLOAD"}
    request = signer.HttpRequest(method, url, headers)

    # Create sign, set the AK/SK to sign and authenticate the request.
    sig = signer.Signer()
    sig.Key = ak
    sig.Secret = sk
    sig.Sign(request)

    # Send request
    files = {'images': open(file_path, 'rb')}
    resp = requests.request(request.method, request.scheme + "://" + request.host + request.uri, headers=request.headers, files=files)

    # Print result
    print(resp.status_code)
    print(resp.text)

    # {"detection_classes": ["yellow"], "detection_boxes": [[18.0, 126.0, 361.0, 459.0]], "detection_scores": [0.4445415437221527]}
    # json 格式 {"键1": "值1", "键2": "值2", "键3": "值3"......}
    # 使用json对数据进行解析
    data_dict = json.loads(resp.text)
    print(data_dict)
    # 1.解析数据
    # 2.获取方框所在的位置坐标
    # 3.在原图上绘制方框
    # 4.显示绘制后的图片

    # 获取数据
    label_list = data_dict['detection_classes']
    boxs_list = data_dict['detection_boxes']
    scores_list = data_dict['detection_scores']
    print(label_list, boxs_list, scores_list)

    # opencv 读取图片
    img = cv2.imread(file_path)
    # 解析box
    for box in boxs_list:
        y1, x1, y2, x2 = box[0], box[1], box[2], box[3]
        y1 = int(float(y1))
        x1 = int(float(x1))
        y2 = int(float(y2))
        x2 = int(float(x2))
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0))

    cv2.imshow('img', img)
    cv2.waitKey(0)  # 保持图片一直显示