#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2026 高教社杯 B题 · 问题3
严格按“七个固定监测点 + 期望信息增益 + 原地继续切频道硬控制 + 确定性清除”实现。

========================
一、严格执行的决策逻辑
========================

监测点 q_m 只允许取 7 个固定覆盖点：
    Q0=(0,0)
    Q1...Q6：半径1150m的正六边形顶点

对每个频道 c：
    - 维护状态 U/A/C/N
    - 维护联合可行域 Ω_c={(x,R)}
    - 假设在当前 Ω_c 内均匀分布
    - 计算候选“频道-监测点”的期望信息增益 I_c(q)
    - 同一点、同一频道最多检测一次

唯一模型超参数：
    LAMBDA_SECONDS_PER_BIT = λ

普通移动检测目标：
    J_measure(c,q)
      = ||q-q_now||/5 + 5 + 1[c != current_channel] - λ I_c(q)

清除动作（只有当 P_c 可被20m圆确定覆盖时才允许）：
    J_clear(c)
      = ||q_clear-q_now||/5 + 5

【原地继续切频道监测：硬控制，不增加第二个超参数】
若机器狗当前就在七个监测点之一，并且还存在：
    - 当前点对频道 c 尚未检测
    - I_c(q_now) > 0
    - 频道尚未完成
则本轮禁止离开当前点，必须继续在原地选择一个频道检测。
多个原地频道之间仍用同一个 J_measure 比较。

这等价于原模型中给“原地、未扫描、信息增益>0”的检测动作加入 -∞ 优先项，
所以不需要额外“原地奖励权重”。

只有当当前监测点已经没有任何“未测且有正信息增益”的频道后，
才在：
    1) 移动到其它七点检测
    2) 去已确定定位的目标清除
之间比较目标值。

near 是硬事件：立即原地 /clear。

========================
二、信息增益
========================

隐藏状态 Z_c：
    - 频道不存在；
    - 或频道存在，(X_c,R_c) 在 Ω_c 上均匀分布。

观测 Y：
    no_signal / near / direction角度箱

假设测向误差 ε ~ U[-1°,1°]。
信息增益直接取互信息：
    I_c(q)=I(Z_c;Y_q)=H(Y_q)-E[H(Y_q|Z_c)]
单位 bit。

这样不需要再设置面积权重、半径权重、状态权重。
模型中只有 λ 一个超参数。

========================
三、数值实现
========================

- Ω_c 用 5m 空间网格 + 每个网格单元对应可行 R 区间 [R_lo,R_hi] 外逼近。
- 真实观测更新使用完整细网格，保证几何更新可靠。
- “候选点信息增益”仅用确定性均匀抽样的粒子近似积分，避免运行过慢。
- 因为监测点永远只有7个，所有网格到七点的距离/方位角一次性预计算。
- 信息增益按 (频道版本, 监测点) 缓存；只有该频道收到新观测时缓存失效。

========================
四、运行
========================

依赖：
    Python >= 3.9
    numpy

运行前：
    1. 模拟器登录并启动问题3测试，等接口就绪。
    2. 设置 ROBOT_ID：
       PowerShell:
           $env:ROBOT_ID="参赛队号"
       Linux/macOS:
           export ROBOT_ID="参赛队号"
    3. python problem3_strict_expected_info.py
"""

from __future__ import annotations

import json
import math
import os
import random
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import numpy as np


# ============================================================
# 0. 唯一需要演练调节的模型超参数
# ============================================================

# 单位：秒 / bit
# 含义：多获得 1 bit 期望信息，最多值得付出多少秒额外时间。
# 原地继续扫频道由硬规则控制，不再需要第二个参数。
LAMBDA_SECONDS_PER_BIT = 30.0


# ============================================================
# 1. 接口与题目物理常数（不是超参数）
# ============================================================

BASE_URL = os.getenv("SIM_BASE_URL", "http://127.0.0.1:2026")
ROBOT_ID = os.getenv("ROBOT_ID", "202613002010")

ARENA_RADIUS = 1800.0
R_MIN = 1000.0
R_MAX = 1500.0

DOG_SPEED = 5.0
MEASURE_TIME = 5.0
SWITCH_TIME = 1.0
CLEAR_SUCCESS_TIME = 5.0

NEAR_RADIUS = 5.0
CLEAR_RADIUS = 20.0
DIRECTION_ERROR_DEG = 1.0

CHANNELS = tuple(range(1, 21))

# 若 N 在10..16上取均匀先验，则 E[N]=13
INITIAL_EXIST_PROB = 13.0 / 20.0

# 七点覆盖半径：
# sqrt(1800^2 + 1150^2 - 2*1800*1150*cos30°) ≈ 988.5 < 1000
MONITOR_RING_RADIUS = 1150.0


# ============================================================
# 2. 数值计算常数（仅控制精度/速度，不是模型权重）
# ============================================================

# 完整可行域网格。5m是为了最终20m清除判据具有足够分辨率。
GRID_STEP = 5.0
CELL_PAD = GRID_STEP * math.sqrt(2.0) / 2.0

# 计算期望信息增益时，从当前联合可行域均匀取的积分代表点数。
# 这是数值积分精度，不是模型超参数。
INFO_PARTICLES = 4096

# direction 分箱。误差区间总宽度为2°，取2°一箱。
ANGLE_BIN_DEG = 2.0
N_ANGLE_BINS = int(round(360.0 / ANGLE_BIN_DEG))

# 数值容差
SAME_POINT_EPS_M = 0.50
INFO_EPS_BITS = 1e-8
CLEAR_EPS_M = 0.20

# HTTP/工程保护
HTTP_TIMEOUT_S = 4.0
NETWORK_RETRIES = 3
REAL_TIME_SAFETY_S = 8.0
MAX_ACTIONS = 2000
LOCAL_LOG_FILE = "robot_local_log.jsonl"


Point = Tuple[float, float]


# ============================================================
# 3. 基础函数
# ============================================================

def euclid(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def entropy(prob: np.ndarray) -> float:
    p = prob[prob > 0.0]
    if p.size == 0:
        return 0.0
    return float(-np.sum(p * np.log2(p)))


def binary_entropy(p: np.ndarray) -> np.ndarray:
    ans = np.zeros_like(p, dtype=np.float64)
    m = (p > 0.0) & (p < 1.0)
    q = p[m]
    ans[m] = -q * np.log2(q) - (1.0 - q) * np.log2(1.0 - q)
    return ans


def circular_diff_deg(a: np.ndarray, b: float) -> np.ndarray:
    return np.abs((a - b + 180.0) % 360.0 - 180.0)


# ============================================================
# 4. 七个固定监测点
# ============================================================

def build_monitor_points() -> List[Point]:
    pts: List[Point] = [(0.0, 0.0)]
    for j in range(6):
        theta = j * math.pi / 3.0
        pts.append(
            (
                MONITOR_RING_RADIUS * math.cos(theta),
                MONITOR_RING_RADIUS * math.sin(theta),
            )
        )
    return pts


MONITOR_POINTS = build_monitor_points()
N_MONITOR = len(MONITOR_POINTS)


def monitor_index(q: Point) -> Optional[int]:
    for i, p in enumerate(MONITOR_POINTS):
        if euclid(q, p) <= SAME_POINT_EPS_M:
            return i
    return None


# ============================================================
# 5. 完整位置网格，并预计算七点几何关系
# ============================================================

def build_position_grid() -> Tuple[np.ndarray, np.ndarray]:
    vals = np.arange(
        -ARENA_RADIUS,
        ARENA_RADIUS + GRID_STEP * 0.5,
        GRID_STEP,
        dtype=np.float32,
    )
    xx, yy = np.meshgrid(vals, vals, indexing="xy")
    x = xx.ravel()
    y = yy.ravel()

    # 外逼近：凡单元可能与目标圆相交就保留
    keep = x.astype(np.float64) ** 2 + y.astype(np.float64) ** 2 <= (
        ARENA_RADIUS + CELL_PAD
    ) ** 2
    return x[keep], y[keep]


GRID_X, GRID_Y = build_position_grid()
N_GRID = GRID_X.size


def precompute_monitor_geometry() -> Tuple[np.ndarray, np.ndarray]:
    """
    DIST_TO_MONITOR[i,j] : 第j个网格中心到第i个固定监测点距离
    BEARING_TO_MONITOR[i,j] : 从第i监测点指向第j网格中心的方位角
    """
    D = np.empty((N_MONITOR, N_GRID), dtype=np.float32)
    B = np.empty((N_MONITOR, N_GRID), dtype=np.float32)

    gx = GRID_X.astype(np.float64)
    gy = GRID_Y.astype(np.float64)

    for i, q in enumerate(MONITOR_POINTS):
        dx = gx - q[0]
        dy = gy - q[1]
        D[i] = np.hypot(dx, dy).astype(np.float32)
        B[i] = ((np.degrees(np.arctan2(dy, dx)) + 360.0) % 360.0).astype(
            np.float32
        )
    return D, B


DIST_TO_MONITOR, BEARING_TO_MONITOR = precompute_monitor_geometry()


# ============================================================
# 6. 最小包围圆
# ============================================================

@dataclass
class Circle:
    x: float
    y: float
    r: float


def _is_in_circle(c: Circle, p: Point, eps: float = 1e-9) -> bool:
    return euclid((c.x, c.y), p) <= c.r + eps


def _circle_diameter(a: Point, b: Point) -> Circle:
    cx = (a[0] + b[0]) / 2.0
    cy = (a[1] + b[1]) / 2.0
    return Circle(cx, cy, euclid(a, b) / 2.0)


def _circle_three(a: Point, b: Point, c: Point) -> Optional[Circle]:
    ax, ay = a
    bx, by = b
    cx, cy = c

    d = 2.0 * (
        ax * (by - cy)
        + bx * (cy - ay)
        + cx * (ay - by)
    )
    if abs(d) < 1e-12:
        return None

    a2 = ax * ax + ay * ay
    b2 = bx * bx + by * by
    c2 = cx * cx + cy * cy

    ux = (
        a2 * (by - cy)
        + b2 * (cy - ay)
        + c2 * (ay - by)
    ) / d
    uy = (
        a2 * (cx - bx)
        + b2 * (ax - cx)
        + c2 * (bx - ax)
    ) / d

    return Circle(ux, uy, math.hypot(ux - ax, uy - ay))


def _left_cross(o: Point, a: Point, b: Point) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def convex_hull(points: Sequence[Point]) -> List[Point]:
    pts = sorted(set(points))
    if len(pts) <= 1:
        return pts

    lower: List[Point] = []
    for p in pts:
        while len(lower) >= 2 and _left_cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)

    upper: List[Point] = []
    for p in reversed(pts):
        while len(upper) >= 2 and _left_cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)

    return lower[:-1] + upper[:-1]


def smallest_enclosing_circle(points: Sequence[Point]) -> Circle:
    """
    确定性复现的 Welzl 风格最小包围圆。
    先固定随机种子打乱，避免病态顺序；结果几何上仍是同一个MEC。
    """
    pts = list(points)
    if not pts:
        return Circle(0.0, 0.0, float("inf"))

    rnd = random.Random(0)
    rnd.shuffle(pts)

    c: Optional[Circle] = None

    for i, p in enumerate(pts):
        if c is not None and _is_in_circle(c, p):
            continue

        c = Circle(p[0], p[1], 0.0)

        for j in range(i):
            q = pts[j]
            if _is_in_circle(c, q):
                continue

            c = _circle_diameter(p, q)

            for k in range(j):
                r = pts[k]
                if _is_in_circle(c, r):
                    continue

                c3 = _circle_three(p, q, r)
                if c3 is not None:
                    c = c3

    assert c is not None
    return c


# ============================================================
# 7. 每个频道的状态
# ============================================================

@dataclass
class ChannelBelief:
    channel: int

    # U: 未确定是否存在
    # A: 已确定存在但未清除
    # C: 已清除
    # N: 已确定不存在
    status: str = "U"

    p_exist: float = INITIAL_EXIST_PROB

    # Ω_c 的离散外逼近：
    # 每个位置网格单元保留一个可行接收半径区间 [r_lo, r_hi]
    r_lo: np.ndarray = field(
        default_factory=lambda: np.full(N_GRID, R_MIN, dtype=np.float32)
    )
    r_hi: np.ndarray = field(
        default_factory=lambda: np.full(N_GRID, R_MAX, dtype=np.float32)
    )

    # 七个监测点是否已经对该频道测过
    measured: np.ndarray = field(
        default_factory=lambda: np.zeros(N_MONITOR, dtype=bool)
    )

    # 七点中实际返回的结果；用于7点全部no_signal的确定性无源判据
    monitor_results: Dict[int, str] = field(default_factory=dict)

    # 状态版本，每次收到该频道新信息后+1
    version: int = 0

    # 信息增益 cache: monitor_idx -> bits
    info_cache: Dict[int, float] = field(default_factory=dict)

    # 均匀积分代表点 cache
    sample_idx_cache: Optional[np.ndarray] = None

    # 清除圆 cache
    clear_cache_version: int = -1
    clear_cache: Optional[Circle] = None

    def feasible_length(self) -> np.ndarray:
        return np.maximum(
            self.r_hi.astype(np.float64) - self.r_lo.astype(np.float64),
            0.0,
        )

    def volume(self) -> float:
        # 位置网格面积 GRID_STEP^2 是统一常数，概率比中消去
        return float(np.sum(self.feasible_length(), dtype=np.float64))

    def feasible_mask(self) -> np.ndarray:
        return self.r_hi > self.r_lo

    def invalidate(self) -> None:
        self.version += 1
        self.info_cache.clear()
        self.sample_idx_cache = None
        self.clear_cache_version = -1
        self.clear_cache = None


# ============================================================
# 8. 当前Ω内的“均匀”数值积分代表点
# ============================================================

def uniform_joint_position_samples(b: ChannelBelief) -> np.ndarray:
    """
    对联合可行域 Ω={(x,R)} 做确定性等质量抽样。

    因为每个位置网格单元在R维上的可行长度不同，
    位置被抽中的概率应正比于 (r_hi-r_lo)。

    用累积分布的等分位点取样，无随机性、可复现。
    """
    if b.sample_idx_cache is not None:
        return b.sample_idx_cache

    w = b.feasible_length()
    total = float(np.sum(w))
    if total <= 0.0:
        ans = np.empty(0, dtype=np.int64)
        b.sample_idx_cache = ans
        return ans

    cdf = np.cumsum(w)
    n = min(INFO_PARTICLES, max(1, int(np.count_nonzero(w))))

    # 中点分位： (0.5/n, 1.5/n, ...)
    targets = (np.arange(n, dtype=np.float64) + 0.5) * total / n
    idx = np.searchsorted(cdf, targets, side="left").astype(np.int64)

    b.sample_idx_cache = idx
    return idx


# ============================================================
# 9. 期望信息增益 I(Z;Y)
# ============================================================

def expected_information_gain_bits(
    b: ChannelBelief,
    monitor_idx: int,
) -> float:
    """
    I_c(q)=I(Z_c;Y_q)，单位 bit。

    Z_c：
      1) 频道不存在；
      2) 频道存在且 (x,R) 在当前Ω_c中均匀。

    Y_q：
      no_signal
      near
      direction角度箱

    ε ~ U[-1°,1°]。

    对“频道存在”时的联合Ω分布，使用等质量代表点近似积分。
    """
    if b.status in ("C", "N"):
        return 0.0

    if b.measured[monitor_idx]:
        # 同一点同一频道只能测一次；重复测量边际信息为0
        return 0.0

    if monitor_idx in b.info_cache:
        return b.info_cache[monitor_idx]

    idx = uniform_joint_position_samples(b)
    n = idx.size
    if n == 0:
        b.info_cache[monitor_idx] = 0.0
        return 0.0

    lo = b.r_lo[idx].astype(np.float64)
    hi = b.r_hi[idx].astype(np.float64)
    width = hi - lo

    valid = width > 0.0
    if not np.all(valid):
        idx = idx[valid]
        lo = lo[valid]
        hi = hi[valid]
        width = width[valid]
        n = idx.size
        if n == 0:
            b.info_cache[monitor_idx] = 0.0
            return 0.0

    d = DIST_TO_MONITOR[monitor_idx, idx].astype(np.float64)
    beta = BEARING_TO_MONITOR[monitor_idx, idx].astype(np.float64)

    # 这些样本在联合Ω里是等质量样本。
    # 对每个位置样本，再对其R区间做解析积分。
    near_mask = d <= NEAR_RADIUS

    no_fraction = np.zeros(n, dtype=np.float64)
    dir_fraction = np.zeros(n, dtype=np.float64)
    near_fraction = np.zeros(n, dtype=np.float64)

    near_fraction[near_mask] = 1.0

    m = ~near_mask
    if np.any(m):
        # no_signal iff R < d
        no_len = np.clip(
            np.minimum(hi[m], d[m]) - lo[m],
            0.0,
            width[m],
        )
        no_fraction[m] = no_len / width[m]
        dir_fraction[m] = 1.0 - no_fraction[m]

    pE = float(np.clip(b.p_exist, 0.0, 1.0))
    mass_per_sample = pE / n

    p_no = (1.0 - pE) + mass_per_sample * float(np.sum(no_fraction))
    p_near = mass_per_sample * float(np.sum(near_fraction))

    angle_prob = np.zeros(N_ANGLE_BINS, dtype=np.float64)

    # H(Y|Z)：
    # no/near在给定真实状态下是确定的；
    # direction只剩均匀±1°误差带来的角度箱随机性。
    conditional_entropy = 0.0

    md = dir_fraction > 0.0
    if np.any(md):
        bta = beta[md]
        dir_mass = mass_per_sample * dir_fraction[md]

        # 误差区间长度2°，恰好等于一个角度箱宽。
        lower = (bta - DIRECTION_ERROR_DEG) % 360.0
        base = np.floor(lower / ANGLE_BIN_DEG).astype(np.int32)
        offset = lower - base * ANGLE_BIN_DEG

        p1 = (ANGLE_BIN_DEG - offset) / ANGLE_BIN_DEG
        p2 = offset / ANGLE_BIN_DEG

        idx1 = base % N_ANGLE_BINS
        idx2 = (base + 1) % N_ANGLE_BINS

        angle_prob += np.bincount(
            idx1,
            weights=dir_mass * p1,
            minlength=N_ANGLE_BINS,
        )
        angle_prob += np.bincount(
            idx2,
            weights=dir_mass * p2,
            minlength=N_ANGLE_BINS,
        )

        conditional_entropy = float(
            np.sum(dir_mass * binary_entropy(p1))
        )

    prob = np.concatenate(
        (
            np.array([p_no, p_near], dtype=np.float64),
            angle_prob,
        )
    )

    # 数值归一化
    s = float(np.sum(prob))
    if s > 0.0:
        prob /= s

    I = max(0.0, entropy(prob) - conditional_entropy)
    b.info_cache[monitor_idx] = I
    return I


# ============================================================
# 10. 真实 /measure 返回后的联合可行域更新
# ============================================================

def update_after_measure(
    b: ChannelBelief,
    monitor_idx: int,
    result: str,
    svd_deg: Optional[float],
) -> None:
    if b.measured[monitor_idx]:
        raise RuntimeError(
            f"违反模型约束：频道{b.channel}在监测点{monitor_idx}重复检测"
        )

    d = DIST_TO_MONITOR[monitor_idx].astype(np.float64)
    beta = BEARING_TO_MONITOR[monitor_idx].astype(np.float64)

    lo_old = b.r_lo.astype(np.float64)
    hi_old = b.r_hi.astype(np.float64)
    width_old = np.maximum(hi_old - lo_old, 0.0)
    volume_old = float(np.sum(width_old))

    if result == "no_signal":
        # ---- Bayes存在概率更新 ----
        # 用网格中心模型计算 P(no_signal | 存在)
        no_len_center = np.clip(
            np.minimum(hi_old, d) - lo_old,
            0.0,
            width_old,
        )
        p_no_given_exist = (
            0.0
            if volume_old <= 0.0
            else float(np.sum(no_len_center) / volume_old)
        )

        p = b.p_exist
        denom = (1.0 - p) + p * p_no_given_exist
        if denom <= 1e-15:
            b.p_exist = 0.0
        else:
            b.p_exist = p * p_no_given_exist / denom

        # ---- Ω外逼近 ----
        # no_signal => R < d_true。
        # 单元内真实点最远可到 d_center + CELL_PAD，
        # 因此外逼近保留 R <= d_center + CELL_PAD。
        b.r_hi = np.minimum(
            hi_old,
            d + CELL_PAD,
        ).astype(np.float32)

    elif result == "near":
        # near => true distance <=5
        keep = d <= NEAR_RADIUS + CELL_PAD

        new_hi = hi_old.copy()
        new_hi[~keep] = lo_old[~keep]

        b.r_hi = new_hi.astype(np.float32)
        b.p_exist = 1.0
        b.status = "A"

    elif result == "direction":
        if svd_deg is None:
            raise RuntimeError("direction返回缺少svd_deg")

        # 单元角半径的保守上界
        safe_d = np.maximum(d, CELL_PAD)
        angular_pad = np.degrees(
            np.arcsin(np.minimum(1.0, CELL_PAD / safe_d))
        )

        angle_ok = circular_diff_deg(
            beta,
            float(svd_deg),
        ) <= (DIRECTION_ERROR_DEG + angular_pad)

        # direction => d_true > 5 且 R >= d_true
        # 外逼近下，R下界用 d_center-CELL_PAD
        new_lo = np.maximum(
            lo_old,
            np.maximum(R_MIN, d - CELL_PAD),
        )
        new_hi = hi_old.copy()

        keep = angle_ok & ((d + CELL_PAD) > NEAR_RADIUS)
        new_hi[~keep] = new_lo[~keep]

        b.r_lo = new_lo.astype(np.float32)
        b.r_hi = new_hi.astype(np.float32)
        b.p_exist = 1.0
        b.status = "A"

    else:
        raise RuntimeError(f"未知measure_result: {result}")

    # 清除非法区间
    bad = b.r_hi <= b.r_lo
    b.r_hi[bad] = b.r_lo[bad]

    b.measured[monitor_idx] = True
    b.monitor_results[monitor_idx] = result

    # 7个覆盖点全部 no_signal => 确定无源
    if b.status == "U" and np.all(b.measured):
        if all(
            b.monitor_results.get(i) == "no_signal"
            for i in range(N_MONITOR)
        ):
            b.status = "N"
            b.p_exist = 0.0
            b.r_hi[:] = b.r_lo

    # 数值上联合可行域为空，而且尚未出现正信号
    if b.status == "U" and b.volume() <= 1e-10:
        b.status = "N"
        b.p_exist = 0.0

    b.invalidate()


# ============================================================
# 11. 清除失败更新
# ============================================================

def update_after_clear_fail(b: ChannelBelief, q: Point) -> None:
    dx = GRID_X.astype(np.float64) - q[0]
    dy = GRID_Y.astype(np.float64) - q[1]
    d = np.hypot(dx, dy)

    # no_target_in_range => true position 不在 B(q,20)。
    # 只剔除“整个网格单元都必定位于20m圆内”的单元，保持外逼近。
    remove = d + CELL_PAD <= CLEAR_RADIUS
    b.r_hi[remove] = b.r_lo[remove]
    b.invalidate()


# ============================================================
# 12. 是否已经可以确定性清除
# ============================================================

def guaranteed_clear_circle(b: ChannelBelief) -> Optional[Circle]:
    if b.status != "A":
        return None

    if b.clear_cache_version == b.version:
        return b.clear_cache

    mask = b.feasible_mask()
    n = int(np.count_nonzero(mask))
    if n == 0:
        b.clear_cache_version = b.version
        b.clear_cache = None
        return None

    x = GRID_X[mask].astype(np.float64)
    y = GRID_Y[mask].astype(np.float64)

    # 网格中心的MEC半径必须 <= 20-CELL_PAD-CLEAR_EPS
    center_radius_limit = CLEAR_RADIUS - CELL_PAD - CLEAR_EPS_M
    if center_radius_limit <= 0:
        b.clear_cache_version = b.version
        b.clear_cache = None
        return None

    xmin, xmax = float(np.min(x)), float(np.max(x))
    ymin, ymax = float(np.min(y)), float(np.max(y))

    # MEC半径至少为bbox跨度的一半；快速排除
    if max(xmax - xmin, ymax - ymin) / 2.0 > center_radius_limit:
        b.clear_cache_version = b.version
        b.clear_cache = None
        return None

    pts = [(float(px), float(py)) for px, py in zip(x, y)]
    hull = convex_hull(pts)
    mec = smallest_enclosing_circle(hull)

    guaranteed_r = mec.r + CELL_PAD
    if guaranteed_r <= CLEAR_RADIUS - CLEAR_EPS_M:
        ans = Circle(mec.x, mec.y, guaranteed_r)
    else:
        ans = None

    b.clear_cache_version = b.version
    b.clear_cache = ans
    return ans


# ============================================================
# 13. 10<=N<=16 的确定性逻辑
# ============================================================

def apply_count_logic(beliefs: Dict[int, ChannelBelief]) -> None:
    confirmed = [
        c for c, b in beliefs.items()
        if b.status in ("A", "C")
    ]
    unknown = [
        c for c, b in beliefs.items()
        if b.status == "U"
    ]

    # 已确认达到最大16个，则其余必无源
    if len(confirmed) >= 16:
        for c in unknown:
            b = beliefs[c]
            b.status = "N"
            b.p_exist = 0.0
            b.r_hi[:] = b.r_lo
            b.invalidate()
        return

    # 已确认 + 未知 = 10，则所有未知必须存在
    if len(confirmed) + len(unknown) == 10:
        for c in unknown:
            b = beliefs[c]
            b.status = "A"
            b.p_exist = 1.0
            b.invalidate()


def task_complete(beliefs: Dict[int, ChannelBelief]) -> bool:
    n_cleared = sum(
        1 for b in beliefs.values()
        if b.status == "C"
    )
    if n_cleared >= 16:
        return True

    return all(
        b.status in ("C", "N")
        for b in beliefs.values()
    )


# ============================================================
# 14. 动作结构与目标函数
# ============================================================

@dataclass
class MeasureAction:
    channel: int
    monitor_idx: int
    info_bits: float
    time_s: float
    J: float
    forced_stay: bool = False

    @property
    def q(self) -> Point:
        return MONITOR_POINTS[self.monitor_idx]


@dataclass
class ClearAction:
    channel: int
    q: Point
    time_s: float
    J: float
    guaranteed_radius: float


def measure_time(
    current_pos: Point,
    current_channel: int,
    c: int,
    monitor_idx: int,
) -> float:
    q = MONITOR_POINTS[monitor_idx]
    move = euclid(current_pos, q) / DOG_SPEED
    switch = 0.0 if c == current_channel else SWITCH_TIME
    return move + MEASURE_TIME + switch


def build_measure_action(
    b: ChannelBelief,
    current_pos: Point,
    current_channel: int,
    monitor_idx: int,
    forced_stay: bool,
) -> Optional[MeasureAction]:
    if b.status in ("C", "N"):
        return None
    if b.measured[monitor_idx]:
        return None

    # 已经确定能清除的目标不再继续浪费检测
    if b.status == "A" and guaranteed_clear_circle(b) is not None:
        return None

    I = expected_information_gain_bits(b, monitor_idx)
    if I <= INFO_EPS_BITS:
        return None

    T = measure_time(
        current_pos,
        current_channel,
        b.channel,
        monitor_idx,
    )

    J = T - LAMBDA_SECONDS_PER_BIT * I

    return MeasureAction(
        channel=b.channel,
        monitor_idx=monitor_idx,
        info_bits=I,
        time_s=T,
        J=J,
        forced_stay=forced_stay,
    )


# ============================================================
# 15. 原地继续切频道：严格硬控制
# ============================================================

def choose_forced_stay_action(
    beliefs: Dict[int, ChannelBelief],
    current_pos: Point,
    current_channel: int,
) -> Optional[MeasureAction]:
    """
    如果当前就在七个监测点之一：

    只要存在“当前点未测过 + I>0”的合法频道，
    就强制继续留在原地扫描，不允许和远处移动/清除动作竞争。

    这就是模型中的原地继续切频道控制项（等价于 -∞ 优先）。
    不使用第二个超参数。
    """
    idx = monitor_index(current_pos)
    if idx is None:
        return None

    candidates: List[MeasureAction] = []

    for c in CHANNELS:
        a = build_measure_action(
            beliefs[c],
            current_pos,
            current_channel,
            idx,
            forced_stay=True,
        )
        if a is not None:
            candidates.append(a)

    if not candidates:
        return None

    # 原地候选间仍严格使用原目标：
    # 5 + switch - λI
    return min(
        candidates,
        key=lambda a: (a.J, -a.info_bits, a.channel),
    )


# ============================================================
# 16. 当前点榨干后，选择下一移动监测动作
# ============================================================

def choose_best_move_measure(
    beliefs: Dict[int, ChannelBelief],
    current_pos: Point,
    current_channel: int,
) -> Optional[MeasureAction]:

    current_monitor = monitor_index(current_pos)
    best: Optional[MeasureAction] = None

    for c in CHANNELS:
        b = beliefs[c]

        if b.status in ("C", "N"):
            continue

        if b.status == "A" and guaranteed_clear_circle(b) is not None:
            continue

        for i in range(N_MONITOR):
            if i == current_monitor:
                # 当前点若有正信息动作，forced-stay阶段早已处理
                continue

            if b.measured[i]:
                continue

            a = build_measure_action(
                b,
                current_pos,
                current_channel,
                i,
                forced_stay=False,
            )
            if a is None:
                continue

            if best is None or (
                a.J,
                a.time_s,
                -a.info_bits,
                a.channel,
                a.monitor_idx,
            ) < (
                best.J,
                best.time_s,
                -best.info_bits,
                best.channel,
                best.monitor_idx,
            ):
                best = a

    return best


# ============================================================
# 17. 可清除动作
# ============================================================

def choose_best_clear(
    beliefs: Dict[int, ChannelBelief],
    current_pos: Point,
) -> Optional[ClearAction]:

    best: Optional[ClearAction] = None

    for c in CHANNELS:
        b = beliefs[c]
        circle = guaranteed_clear_circle(b)
        if circle is None:
            continue

        q = (circle.x, circle.y)
        T = euclid(current_pos, q) / DOG_SPEED + CLEAR_SUCCESS_TIME

        # 原手稿结构中清除项是时间成本，
        # 信息增益项只作用于检测动作，因此清除J=T。
        a = ClearAction(
            channel=c,
            q=q,
            time_s=T,
            J=T,
            guaranteed_radius=circle.r,
        )

        if best is None or (
            a.J,
            a.channel,
        ) < (
            best.J,
            best.channel,
        ):
            best = a

    return best


# ============================================================
# 18. HTTP客户端（严格幂等）
# ============================================================

class SimulatorClient:
    def __init__(
        self,
        base_url: str,
        robot_id: str,
        log_path: str,
    ):
        self.base_url = base_url.rstrip("/")
        self.robot_id = robot_id
        self.seq = 0
        self.log_path = Path(log_path)

    def new_id(self, prefix: str) -> str:
        self.seq += 1
        return f"{prefix}-{self.seq}-{uuid.uuid4().hex[:8]}"

    def base(self, request_id: str) -> dict:
        return {
            "arena_id": "default",
            "robot_id": self.robot_id,
            "request_id": request_id,
        }

    def log(self, item: dict) -> None:
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    item,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                + "\n"
            )

    def post(self, path: str, payload: dict) -> dict:
        """
        网络超时/连接断开时：
        必须用完全相同的 payload 和 request_id 重试。

        HTTP业务错误：
        不擅自生成新request_id重复动作。
        """
        body = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")

        last_error: Optional[Exception] = None

        for attempt in range(1, NETWORK_RETRIES + 1):
            req = Request(
                self.base_url + path,
                data=body,
                headers={
                    "Content-Type": "application/json; charset=utf-8"
                },
                method="POST",
            )

            try:
                with urlopen(
                    req,
                    timeout=HTTP_TIMEOUT_S,
                ) as response:
                    http_status = int(response.status)
                    raw = response.read().decode("utf-8")
                    data = json.loads(raw)

                self.log(
                    {
                        "wall_time": time.time(),
                        "path": path,
                        "payload": payload,
                        "http_status": http_status,
                        "response": data,
                    }
                )

                if http_status != 200:
                    raise RuntimeError(
                        f"HTTP {http_status}: {data}"
                    )

                if data.get("accepted") is not True:
                    raise RuntimeError(
                        f"accepted=false: {data}"
                    )

                return data

            except HTTPError as e:
                raw = ""
                try:
                    raw = e.read().decode("utf-8")
                except Exception:
                    pass

                self.log(
                    {
                        "wall_time": time.time(),
                        "path": path,
                        "payload": payload,
                        "http_status": getattr(e, "code", None),
                        "error": raw or repr(e),
                    }
                )
                raise

            except (
                URLError,
                TimeoutError,
                ConnectionError,
                OSError,
            ) as e:
                last_error = e

                self.log(
                    {
                        "wall_time": time.time(),
                        "path": path,
                        "payload": payload,
                        "attempt": attempt,
                        "network_error": repr(e),
                    }
                )

                if attempt < NETWORK_RETRIES:
                    time.sleep(0.20)

        raise RuntimeError(
            f"网络失败；已严格复用同一request_id重试：{last_error}"
        )

    def enter(self) -> dict:
        rid = self.new_id("enter")
        return self.post(
            "/enter",
            self.base(rid),
        )

    def measure(
        self,
        q: Point,
        channel: int,
    ) -> dict:
        rid = self.new_id("measure")
        payload = self.base(rid)
        payload["position"] = {
            "x": float(q[0]),
            "y": float(q[1]),
        }
        payload["channel"] = int(channel)

        return self.post(
            "/measure",
            payload,
        )

    def clear(
        self,
        q: Point,
        channel: int,
    ) -> dict:
        rid = self.new_id("clear")
        payload = self.base(rid)
        payload["position"] = {
            "x": float(q[0]),
            "y": float(q[1]),
        }
        payload["channel"] = int(channel)

        return self.post(
            "/clear",
            payload,
        )

    def exit(self) -> dict:
        rid = self.new_id("exit")
        return self.post(
            "/exit",
            self.base(rid),
        )


# ============================================================
# 19. 输出状态
# ============================================================

def state_summary(
    beliefs: Dict[int, ChannelBelief],
) -> str:
    groups = {
        "U": [],
        "A": [],
        "C": [],
        "N": [],
    }

    for c in CHANNELS:
        groups[beliefs[c].status].append(c)

    return (
        f"U={groups['U']} | "
        f"A={groups['A']} | "
        f"C={groups['C']} | "
        f"N={groups['N']}"
    )


# ============================================================
# 20. 主策略
# ============================================================

def run() -> None:
    if (
        ROBOT_ID == "<参赛队号>"
        or not ROBOT_ID.strip()
    ):
        raise SystemExit(
            "请先设置 ROBOT_ID 为当前模拟器登录参赛队号。"
        )

    print("=" * 70)
    print("问题3：七点 + 期望信息增益 + 原地硬控制")
    print(f"位置网格数 = {N_GRID}")
    print(
        f"唯一模型超参数 λ = "
        f"{LAMBDA_SECONDS_PER_BIT:.3f} 秒/bit"
    )
    print("固定监测点：")
    for i, q in enumerate(MONITOR_POINTS):
        print(f"  Q{i}=({q[0]:.3f},{q[1]:.3f})")
    print("=" * 70)

    beliefs: Dict[int, ChannelBelief] = {
        c: ChannelBelief(c)
        for c in CHANNELS
    }

    client = SimulatorClient(
        BASE_URL,
        ROBOT_ID,
        LOCAL_LOG_FILE,
    )

    enter_response = client.enter()

    remaining_real_s = float(
        enter_response.get(
            "remaining_real_duration_s",
            1200.0,
        )
    )

    start_wall = time.monotonic()

    current_pos: Point = (0.0, 0.0)
    current_channel = 1
    virtual_time = float(
        enter_response.get(
            "virtual_time_s",
            0.0,
        )
    )

    # near后下一动作必须立即原地清除
    near_clear_channel: Optional[int] = None

    for action_no in range(1, MAX_ACTIONS + 1):

        # ----------------------------------------------------
        # 实时时间保护
        # ----------------------------------------------------
        elapsed_real = time.monotonic() - start_wall

        if (
            elapsed_real
            >= remaining_real_s - REAL_TIME_SAFETY_S
        ):
            print("接近程序现实时间上限，停止新增动作。")
            break

        # ----------------------------------------------------
        # 利用10<=N<=16更新状态
        # ----------------------------------------------------
        apply_count_logic(beliefs)

        # ----------------------------------------------------
        # 终止
        # ----------------------------------------------------
        if task_complete(beliefs):
            print("全部频道均已 C/N，或已清除16个目标。")
            try:
                response = client.exit()
                print("exit:", response)
            except Exception as e:
                print("主动 /exit 失败：", e)
            return

        # ----------------------------------------------------
        # 规则1：near -> 立即原地清除
        # ----------------------------------------------------
        if near_clear_channel is not None:
            c = near_clear_channel
            b = beliefs[c]

            print(
                f"[{action_no}] HARD near-clear | "
                f"ch={c} | q={current_pos}"
            )

            response = client.clear(
                current_pos,
                c,
            )

            virtual_time = float(
                response.get(
                    "virtual_time_s",
                    virtual_time,
                )
            )

            result = response["clear_result"]

            if result == "success":
                b.status = "C"
                b.p_exist = 0.0
                b.r_hi[:] = b.r_lo
                b.invalidate()

                print(
                    f"    success | "
                    f"virtual={virtual_time:.3f}s"
                )
            else:
                # 理论上near一定能清掉；若接口仍返回失败，
                # 严格使用20m排除信息继续。
                print(
                    "    unexpected no_target_in_range; "
                    "apply 20m exclusion"
                )
                update_after_clear_fail(
                    b,
                    current_pos,
                )

            near_clear_channel = None
            print("   ", state_summary(beliefs))
            continue

        # ----------------------------------------------------
        # 规则2：原地继续切频道监测 —— 硬优先
        #
        # 当前就在Q_i：
        # 只要还有未测且 I>0 的频道，
        # 就不允许离开Q_i。
        # ----------------------------------------------------
        stay_action = choose_forced_stay_action(
            beliefs,
            current_pos,
            current_channel,
        )

        if stay_action is not None:
            q = stay_action.q

            print(
                f"[{action_no}] HARD-STAY Q{stay_action.monitor_idx} | "
                f"ch={stay_action.channel} | "
                f"I={stay_action.info_bits:.4f} bit | "
                f"T={stay_action.time_s:.2f}s | "
                f"J={stay_action.J:.2f}"
            )

            response = client.measure(
                q,
                stay_action.channel,
            )

            virtual_time = float(
                response.get(
                    "virtual_time_s",
                    virtual_time,
                )
            )

            # /measure 后当前位置和测向机频道更新
            current_pos = q
            current_channel = stay_action.channel

            result = response["measure_result"]
            svd = response.get("svd_deg")

            b = beliefs[stay_action.channel]

            update_after_measure(
                b,
                stay_action.monitor_idx,
                result,
                svd,
            )

            if result == "direction":
                print(
                    f"    direction={float(svd):.2f}° | "
                    f"p_exist={b.p_exist:.6f} | "
                    f"virtual={virtual_time:.3f}s"
                )
            elif result == "near":
                print(
                    f"    near | virtual={virtual_time:.3f}s | "
                    "下一动作强制原地clear"
                )
                near_clear_channel = stay_action.channel
            else:
                print(
                    f"    no_signal | "
                    f"p_exist={b.p_exist:.6f} | "
                    f"virtual={virtual_time:.3f}s"
                )

            print("   ", state_summary(beliefs))
            continue

        # ----------------------------------------------------
        # 规则3：当前站已经“榨干”
        # 才允许比较：
        #     A. 移到其它七点检测：T - λI
        #     B. 已确定定位的清除：T
        # ----------------------------------------------------
        move_measure = choose_best_move_measure(
            beliefs,
            current_pos,
            current_channel,
        )

        clear_action = choose_best_clear(
            beliefs,
            current_pos,
        )

        # ----------------------------------------------------
        # 决定下一动作
        # ----------------------------------------------------
        choose_clear = False

        if clear_action is not None:
            if move_measure is None:
                choose_clear = True
            elif clear_action.J <= move_measure.J:
                choose_clear = True

        # ----------------------------------------------------
        # 3A. 清除
        # ----------------------------------------------------
        if choose_clear:
            assert clear_action is not None

            c = clear_action.channel
            q = clear_action.q
            b = beliefs[c]

            print(
                f"[{action_no}] CLEAR | "
                f"ch={c} | "
                f"q=({q[0]:.2f},{q[1]:.2f}) | "
                f"cover_r={clear_action.guaranteed_radius:.2f}m | "
                f"T={clear_action.time_s:.2f}s"
            )

            response = client.clear(
                q,
                c,
            )

            virtual_time = float(
                response.get(
                    "virtual_time_s",
                    virtual_time,
                )
            )

            # /clear 会移动，但不会改变测向机当前频道
            current_pos = q

            result = response["clear_result"]

            if result == "success":
                b.status = "C"
                b.p_exist = 0.0
                b.r_hi[:] = b.r_lo
                b.invalidate()

                print(
                    f"    success | "
                    f"virtual={virtual_time:.3f}s"
                )
            else:
                print(
                    "    no_target_in_range | "
                    "使用20m排除反馈"
                )
                update_after_clear_fail(
                    b,
                    q,
                )

            print("   ", state_summary(beliefs))
            continue

        # ----------------------------------------------------
        # 3B. 移动到另一个固定监测点检测
        # ----------------------------------------------------
        if move_measure is not None:
            a = move_measure
            q = a.q

            print(
                f"[{action_no}] MOVE-MEASURE Q{a.monitor_idx} | "
                f"ch={a.channel} | "
                f"q=({q[0]:.2f},{q[1]:.2f}) | "
                f"I={a.info_bits:.4f} bit | "
                f"T={a.time_s:.2f}s | "
                f"J={a.J:.2f}"
            )

            response = client.measure(
                q,
                a.channel,
            )

            virtual_time = float(
                response.get(
                    "virtual_time_s",
                    virtual_time,
                )
            )

            current_pos = q
            current_channel = a.channel

            result = response["measure_result"]
            svd = response.get("svd_deg")

            b = beliefs[a.channel]

            update_after_measure(
                b,
                a.monitor_idx,
                result,
                svd,
            )

            if result == "direction":
                print(
                    f"    direction={float(svd):.2f}° | "
                    f"p_exist={b.p_exist:.6f} | "
                    f"virtual={virtual_time:.3f}s"
                )
            elif result == "near":
                print(
                    f"    near | virtual={virtual_time:.3f}s | "
                    "下一动作强制原地clear"
                )
                near_clear_channel = a.channel
            else:
                print(
                    f"    no_signal | "
                    f"p_exist={b.p_exist:.6f} | "
                    f"virtual={virtual_time:.3f}s"
                )

            print("   ", state_summary(beliefs))
            continue

        # ----------------------------------------------------
        # 走到这里意味着：
        # 七点模型已经没有合法新检测动作，
        # 也没有任何频道达到20m确定清除条件。
        #
        # 严格模式下不能偷偷加入第8个监测点；
        # 直接给出诊断。
        # ----------------------------------------------------
        unresolved = [
            c
            for c, b in beliefs.items()
            if b.status not in ("C", "N")
        ]

        print(
            "严格七点模型进入死端："
            "不存在未测且有正信息增益的七点检测动作，"
            "同时不存在可保证20m清除的频道。"
        )
        print("未完成频道：", unresolved)

        for c in unresolved:
            b = beliefs[c]
            print(
                f"  ch={c}: status={b.status}, "
                f"p_exist={b.p_exist:.6f}, "
                f"measured={b.measured.astype(int).tolist()}"
            )

        break

    # --------------------------------------------------------
    # 异常/时间保护结束，尝试主动退出
    # --------------------------------------------------------
    print("未满足正常完成条件，尝试 /exit。")
    try:
        response = client.exit()
        print("exit:", response)
    except Exception as e:
        print("调用 /exit 失败：", e)


# ============================================================
# 21. 本地快速自检（不连接模拟器）
# ============================================================

def self_test() -> None:
    """
    只检查：
    - 七点覆盖几何
    - 初始期望信息增益可计算
    - HARD-STAY 能在原点选出动作
    不发送HTTP。
    """
    dmax = math.sqrt(
        ARENA_RADIUS ** 2
        + MONITOR_RING_RADIUS ** 2
        - 2.0
        * ARENA_RADIUS
        * MONITOR_RING_RADIUS
        * math.cos(math.radians(30.0))
    )

    print(f"七点理论最大覆盖距离 ≈ {dmax:.3f}m")
    assert dmax < R_MIN

    b = ChannelBelief(1)
    I0 = expected_information_gain_bits(
        b,
        0,
    )
    print(f"初始 ch1@Q0 信息增益 = {I0:.6f} bit")
    assert I0 > 0.0

    beliefs = {
        c: ChannelBelief(c)
        for c in CHANNELS
    }

    a = choose_forced_stay_action(
        beliefs,
        (0.0, 0.0),
        1,
    )
    assert a is not None
    assert a.monitor_idx == 0

    print(
        "HARD-STAY自检：",
        f"Q{a.monitor_idx}, ch={a.channel}, ",
        f"I={a.info_bits:.4f}, J={a.J:.2f}",
    )
    print("SELF TEST PASSED")


if __name__ == "__main__":
    import sys

    if "--self-test" in sys.argv:
        self_test()
    else:
        run()
