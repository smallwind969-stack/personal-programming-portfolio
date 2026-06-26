# -*- coding: utf-8
# @Time  : 2025/5/6 19:54
# @Author: 小宇
# @File  : hat.Py

#https://support.huaweicloud.com/usermanual-standard-modelarts/inference-modelarts-0024.html#section3
import json

import cv2
import requests
import os
from apig_sdk import signer

def hat_check(imgPath):
    # Config url, ak, sk and file path.
    #老师的预测模型
    url = "https://c1c1a6d2954549e6bee688ed43b2df5b.apig.cn-north-4.huaweicloudapis.com/v1/infers/61807db4-80ff-4273-81e7-2cff9ef78970"
    ak = '7MDT7Q1LQCABCBJQYNHG'
    sk = 'a6xraLfGvr18MAozn3o4f2PQSRPmsHpskEMx3zFJ'
    #安全帽图片路径
    file_path = imgPath

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

    #{"detection_classes": ["yellow"], "detection_boxes": [[18.0, 126.0, 361.0, 459.0]], "detection_scores": [0.4445415437221527]}
    #json 格式 {“键1”：“值1”，“键2”：“值2”，“键3”：“值3”.....}
    #使用json对数据进行解析
    data_dict = json.loads(resp.text)
    print(data_dict)
    return data_dict
    #1.解析数据
    #2.获取方框所在的位置坐标
    #3.在原图上绘制方框
    #4.显示绘制后的图片

    #获取数据
    # label_list = data_dict['detection_classes']
    # boxs_list = data_dict['detection_boxes']
    # scores_list = data_dict['detection_scores']
    # print(label_list, boxs_list, scores_list)
    #
    # #opencv 读取图片
    # img = cv2.imread(file_path)
    # #解析box
    # for box in boxs_list:
    #     y1, x1, y2, x2 = box[0], box[1], box[2], box[3]
    #     y1 = int(float(y1))
    #     x1 = int(float(x1))
    #     y2 = int(float(y2))
    #     x2 = int(float(x2))
    #     cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0),2)
    #
    # cv2.imshow('img',img)
    # cv2.waitKey(0)  #保持图片一直显示


# hat_check('../images/hat.jpg')



