import random
import numpy as np
import cvzone
import cv2
from cvzone.HandTrackingModule import HandDetector
import json
import os

# 创建摄像头对象
cap = cv2.VideoCapture(0)

# 积分榜类
class Scoreboard:
    def __init__(self, file_path="high_score.json"):
        self.file_path = file_path
        self.high_score = 0
        self.holder = "Anonymous"  # 默认保持者名称，可手动修改
        self.load_high_score()

    def load_high_score(self):
        """从文件加载最高分和保持者"""
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.high_score = data.get('high_score', 0)
                    self.holder = data.get('holder', "Anonymous")
        except Exception as e:
            print(f"加载最高分失败: {e}")

    def save_high_score(self):
        """保存最高分和保持者至文件"""
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump({'high_score': self.high_score, 'holder': self.holder}, f, ensure_ascii=False)
        except Exception as e:
            print(f"保存最高分失败: {e}")

    def update(self, current_score):
        """更新最高分，只有当超过当前最高分才更新"""
        if current_score > self.high_score:
            self.high_score = current_score
            self.save_high_score()
            return True
        return False

    def reset(self):
        """重置最高分和保持者"""
        self.high_score = 0
        # 注意：保持者名称不会被重置，需要手动修改
        self.save_high_score()

    def display(self, image):
        """在画面上显示最高分和保持者"""
        cv2.putText(image, f'HIGH SCORE: {self.high_score}', (10, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
        # 显示保持者姓名，确保中文正常显示
        cv2.putText(image, f'HOLDER: {self.holder}', (10, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(image, 'Press "o" to reset high score', (10, 460),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

# 创建蛇类
class Snake:
    def __init__(self):
        self.length = 5  # 蛇的初始长度
        self.head = (0, 0)  # 蛇头的位置
        self.points = [self.head]  # 蛇身的点，初始时只有蛇头
        self.last_move_time = None  # 记录最后移动的时间

    def move(self, point, image):
        # point: 蛇头点。 image：画线的图片
        x, y = self.head
        x1, y1 = point

        # 计算蛇头移动的距离
        distance = ((x1 - x) ** 2 + (y1 - y) ** 2) ** 0.5

        # 设置最大移动距离
        max_distance = 10  # 设置最大移动距离

        if distance >= max_distance:
            # 更新蛇头位置
            self.head = point
            self.points.insert(0, point)  # 在前面插入新的头部位置

            # 保持蛇身长度
            while len(self.points) > self.length:
                self.points.pop()  # 从数组的尾部消除元素

            # 更新最后移动的时间
            self.last_move_time = cv2.getTickCount()
        else:
            # 如果没有移动，保持原来的蛇身点不变
            if self.last_move_time is not None:
                # 可能在这里可以添加一些逻辑来处理不动的情况
                pass

        # 绘制蛇身
        for i in range(len(self.points) - 1):
            p = self.points[i]
            p1 = self.points[i + 1]
            cv2.line(image, p, p1, (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)), 3)

    def reset(self):
        self.points = []
        self.head = (0, 0)
        self.length = 5
        self.last_move_time = None  # 重置最后移动时间

# 创建食物的类
class Food:
    def __init__(self):
        # 尝试加载食物图片，失败则创建一个替代图形
        try:
            self.image = cv2.imread('food.png', cv2.IMREAD_UNCHANGED)
            if self.image is None:
                raise FileNotFoundError
            shape = self.image.shape
            self.size = (shape[1], shape[0])  # 宽度，高度
        except:
            # 创建一个替代的食物图形
            self.image = np.ones((30, 30, 4), dtype=np.uint8) * 255
            self.image[:, :, 0:3] = np.random.randint(0, 256, (30, 30, 3))
            self.size = (30, 30)
        self.create_position()  # 生成随机初始坐标

    def show(self, image):
        # 显示食物
        cvzone.overlayPNG(image, self.image, self.position)

    def create_position(self):
        # 随机生成食物的坐标，考虑边界
        x = random.randint(20, 600)
        y = random.randint(20, 420)
        self.position = (x, y)

class Game:
    def __init__(self):
        self.score = 0
        self.is_over = False

    # 食物碰撞检测
    def eat(self, snake_head, food):
        x, y = snake_head
        x1, y1 = food.position
        w, h = food.size

        if x1 <= x <= (x1 + w) and y1 <= y <= (y1 + h):
            self.score += 1
            return True
        return False

    # 蛇身碰撞检测
    def snake_collision(self, snake_points, point, image):
        if len(snake_points) < 3:
            return False

        distance = cv2.pointPolygonTest(np.array(snake_points[2:]), point, measureDist=True)
        if -1 <= distance <= 1:
            cv2.putText(image, f'you are ate', (200, 250), cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 200, 200), 3)
            self.is_over = True
        return self.is_over

    # 边界碰撞检测
    def snake_crush(self, x, y, image):
        # 考虑边界，避免蛇头超出画面
        if (x >= 630 or x <= 10) or (y <= 10 or y >= 470):
            self.is_over = True
            cv2.putText(image, f'you are crushed', (160, 250), cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 200, 0), 3)
        return self.is_over

    # 显示积分
    def show_score(self, image):
        cv2.putText(image, f'SCORE:{self.score}', (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

    # 游戏结束
    def over(self, image):
        cv2.putText(image, 'GAME OVER', (200, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
        cv2.putText(image, 'press "r" to restart', (380, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 1)
        cv2.putText(image, 'press "q" to esc', (400, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 1)
        cv2.putText(image, f'YOUR SCORE:{self.score}', (180, 300), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 4)

    # 重启游戏
    def restart(self):
        self.is_over = False
        self.score = 0

# 创建蛇、食物、游戏和积分榜对象
snake = Snake()
food = Food()
game = Game()
scoreboard = Scoreboard()

# 创建检测器对象
detector = HandDetector(maxHands=1, detectionCon=0.8)

# 主循环
while True:
    # 读取视频帧
    success, image = cap.read()
    if not success:
        print("无法获取视频帧")
        break

    # 水平翻转图像
    image = cv2.flip(image, 1)

    # 显示食物和分数
    food.show(image)
    game.show_score(image)
    scoreboard.display(image)  # 显示积分榜

    if game.is_over:
        game.over(image)
    else:
        # 检测手势
        hands, image = detector.findHands(image, flipType=False)

        if hands:  # 说明识别到手势了
            # 取出食指的顶点坐标
            point = hands[0]["lmList"][8][:-1]  # [x, y, confidence] -> [x, y]

            # 碰撞检测
            game.snake_collision(snake.points, tuple(point), image)
            game.snake_crush(int(point[0]), int(point[1]), image)

            # 移动蛇
            snake.move(tuple(point), image)

            # 检测食物碰撞
            result = game.eat(tuple(point), food)
            if result:
                food.create_position()
                snake.length += 1

        # 更新最高分（只有超过当前最高分才更新）
        scoreboard.update(game.score)

    # 显示图像
    cv2.imshow('Snake Game', image)

    # 按键处理
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    if key == ord('r'):
        game.restart()
        snake.reset()
        food.create_position()
    if key == ord('o'):  # 重置最高分
        scoreboard.reset()

# 释放资源
cap.release()
cv2.destroyAllWindows()