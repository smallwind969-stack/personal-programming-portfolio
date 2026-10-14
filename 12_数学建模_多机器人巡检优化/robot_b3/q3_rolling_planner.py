#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
问题三：基于期望几何信息增益的滚动搜索—定位—清除算法

核心思想
--------
1. 对每个频道 c 维护二维位置可行域 P_c。
2. 根据 measure 的三类反馈更新可行域：
   near:
       P <- P ∩ B(q,5)
   direction(theta):
       P <- P ∩ W(q,theta) ∩ B(q,1500) \\ B(q,5)
   no_signal:
       P <- P \\ B(q,1000)
3. z_c=0 时用“期望剩余面积比例”定义搜索信息增益 I^S；
   z_c=1 时用“期望最小覆盖圆半径比例”定义定位信息增益 I^L。
4. 对有限候选检测点集合滚动求解
       J = ΔT - λ * information_gain
   并执行 J 最小的测量动作。
5. 若 near，立即清除；若最小覆盖圆半径 <= 20 m，则到覆盖圆圆心清除。
6. 当所有频道均“已清除或可行域为空”，或已清除 16 个干扰源时退出。

重要说明
--------
- 代码中的“真实可行域更新”用 Shapely 几何集合完成；
- “期望信息增益”用蒙特卡洛样本近似，以降低每轮滚动计算量；
- R_c 仍按模型中的原设定处理：每次期望计算都用 R_c~U[1000,1500] 边缘化，
  不根据历史观测更新 R_c 的分布；
- 为防止浮点/多边形离散导致误删真实点，实际几何更新默认采用很小的保守裕量；
- 附件1没有给出附件2中的完整 HTTP+JSON 字段格式，因此 SimulatorClient 中
  “请求 payload 和响应解析”被集中隔离在 ProtocolAdapter。拿到附件2后只需修改
  ProtocolAdapter，规划器主体不需要改。
"""

from __future__ import annotations

import argparse
import json
import math
import random
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import requests

from shapely.geometry import GeometryCollection, MultiPolygon, Point, Polygon
from shapely.geometry.base import BaseGeometry

try:
    from shapely import contains_xy
except Exception:  # 兼容部分 Shapely 版本
    contains_xy = None


# ============================================================
# 1. 超参数
# ============================================================

@dataclass
class Config:
    # ---------- 物理/题目参数 ----------
    target_radius: float = 1800.0
    speed: float = 5.0
    detect_time: float = 5.0
    switch_time: float = 1.0
    clear_success_time: float = 5.0
    near_radius: float = 5.0
    clear_radius: float = 20.0
    recv_min: float = 1000.0
    recv_max: float = 1500.0
    angle_error_deg: float = 1.0
    n_channels: int = 20
    max_sources: int = 16

    # ---------- 滚动目标函数 ----------
    # J = ΔT - lambda_info * [alpha_search*I^S 或 beta_locate*I^L]
    lambda_info: float = 450.0
    alpha_search: float = 1.0
    beta_locate: float = 1.8

    # 若采用“频道存在概率”修正，则用 pi_c 乘几何信息增益。
    # 10~16 个源 / 20 个频道，中点先验为 13/20=0.65。
    use_existence_prior_in_score: bool = True
    pi0: float = 0.65

    # ---------- 期望信息增益的数值近似 ----------
    belief_samples: int = 350
    direction_outcome_samples: int = 10
    rng_seed: int = 2026

    # ---------- 候选检测点 ----------
    search_ring_radii: Tuple[float, ...] = (0.0, 450.0, 900.0)
    locate_ring_radii: Tuple[float, ...] = (0.0, 250.0, 500.0, 800.0)
    candidate_angles: int = 8
    max_candidates_per_channel: int = 28

    # ---------- 几何保守裕量 ----------
    # 目的：真实可行域更新尽量“宁可留大一点，不误删真实源”。
    radial_margin: float = 0.5       # m
    angular_margin_deg: float = 0.05 # degree
    circle_resolution: int = 96
    area_eps: float = 1e-4

    # ---------- 运行限制 ----------
    max_actions: int = 500
    http_timeout: float = 8.0
    http_retries: int = 4
    retry_wait: float = 0.5


HYPERPARAM_RANGES = {
    "lambda_info": (150.0, 1000.0),
    "alpha_search": (0.5, 2.0),
    "beta_locate": (1.0, 4.0),
    "pi0": (0.50, 0.80),
    "belief_samples": (200, 1500),
    "direction_outcome_samples": (6, 24),
    "search_ring_radius_typical": (300.0, 1200.0),
    "locate_ring_radius_typical": (150.0, 1000.0),
    "candidate_angles": (6, 16),
    "max_candidates_per_channel": (12, 60),
    "radial_margin": (0.1, 2.0),
    "angular_margin_deg": (0.02, 0.20),
}


# ============================================================
# 2. 基础几何
# ============================================================

def normalize_deg(a: float) -> float:
    return a % 360.0


def angle_diff_deg(a: np.ndarray | float, b: float) -> np.ndarray | float:
    """返回 a-b 的最小有向角差，范围 [-180,180)。"""
    return (np.asarray(a) - b + 180.0) % 360.0 - 180.0


def signal_probability_from_distance(d: np.ndarray, cfg: Config) -> np.ndarray:
    """
    f(d)=P(R_c>=d), R_c~U[1000,1500].
    不表示实际距离已知；d 是对可行域中每个假想位置 x 计算 ||x-q||。
    """
    d = np.asarray(d, dtype=float)
    out = np.zeros_like(d)
    out[d <= cfg.recv_min] = 1.0
    mid = (d > cfg.recv_min) & (d < cfg.recv_max)
    out[mid] = (cfg.recv_max - d[mid]) / (cfg.recv_max - cfg.recv_min)
    return out


def safe_circle(center: Tuple[float, float], radius: float, cfg: Config) -> BaseGeometry:
    return Point(float(center[0]), float(center[1])).buffer(
        max(float(radius), 0.0),
        resolution=cfg.circle_resolution,
    )


def wedge_polygon(
    q: Tuple[float, float],
    theta_deg: float,
    half_angle_deg: float,
    cover_geom: BaseGeometry,
) -> Polygon:
    """
    构造足够长的窄扇形（三角形即可覆盖窄角域内 cover_geom 的全部点）。
    """
    qx, qy = float(q[0]), float(q[1])

    if cover_geom.is_empty:
        L = 10000.0
    else:
        minx, miny, maxx, maxy = cover_geom.bounds
        corners = np.array([
            [minx, miny], [minx, maxy], [maxx, miny], [maxx, maxy]
        ], dtype=float)
        dmax = np.sqrt((corners[:, 0] - qx)**2 + (corners[:, 1] - qy)**2).max()
        # half_angle 约 1°，乘 1.2 后足够让远端弦在 cover_geom 外。
        L = max(100.0, float(dmax) * 1.25 + 50.0)

    a1 = math.radians(theta_deg - half_angle_deg)
    a2 = math.radians(theta_deg + half_angle_deg)
    p1 = (qx + L * math.cos(a1), qy + L * math.sin(a1))
    p2 = (qx + L * math.cos(a2), qy + L * math.sin(a2))
    return Polygon([(qx, qy), p1, p2])


# ============================================================
# 3. 最小覆盖圆（随机增量）
# ============================================================

Circle = Tuple[float, float, float]  # cx, cy, r


def _is_in_circle(c: Circle, p: Tuple[float, float], eps: float = 1e-9) -> bool:
    cx, cy, r = c
    return (p[0]-cx)**2 + (p[1]-cy)**2 <= (r + eps)**2


def _circle_from_one(p: Tuple[float, float]) -> Circle:
    return (float(p[0]), float(p[1]), 0.0)


def _circle_from_two(a: Tuple[float, float], b: Tuple[float, float]) -> Circle:
    cx = (a[0] + b[0]) / 2.0
    cy = (a[1] + b[1]) / 2.0
    r = math.hypot(a[0] - b[0], a[1] - b[1]) / 2.0
    return (cx, cy, r)


def _circle_from_three(
    a: Tuple[float, float],
    b: Tuple[float, float],
    c: Tuple[float, float],
) -> Optional[Circle]:
    ax, ay = a
    bx, by = b
    cx, cy = c
    d = 2.0 * (ax * (by-cy) + bx * (cy-ay) + cx * (ay-by))
    if abs(d) < 1e-12:
        return None
    ux = (
        (ax*ax + ay*ay) * (by-cy)
        + (bx*bx + by*by) * (cy-ay)
        + (cx*cx + cy*cy) * (ay-by)
    ) / d
    uy = (
        (ax*ax + ay*ay) * (cx-bx)
        + (bx*bx + by*by) * (ax-cx)
        + (cx*cx + cy*cy) * (bx-ax)
    ) / d
    r = math.hypot(ux-ax, uy-ay)
    return (ux, uy, r)


def minimum_enclosing_circle(
    points: Sequence[Tuple[float, float]],
    seed: int = 0,
) -> Circle:
    pts = [(float(x), float(y)) for x, y in points]
    if not pts:
        return (0.0, 0.0, 0.0)
    rnd = random.Random(seed)
    rnd.shuffle(pts)

    c: Optional[Circle] = None
    for i, p in enumerate(pts):
        if c is not None and _is_in_circle(c, p):
            continue
        c = _circle_from_one(p)
        for j in range(i):
            q = pts[j]
            if _is_in_circle(c, q):
                continue
            c = _circle_from_two(p, q)
            for k in range(j):
                r = pts[k]
                if _is_in_circle(c, r):
                    continue
                c3 = _circle_from_three(p, q, r)
                if c3 is None:
                    # 三点共线时，取能覆盖三点的最远两点圆。
                    cand = [
                        _circle_from_two(p, q),
                        _circle_from_two(p, r),
                        _circle_from_two(q, r),
                    ]
                    c = min(
                        (cc for cc in cand if all(_is_in_circle(cc, t) for t in (p, q, r))),
                        key=lambda cc: cc[2],
                    )
                else:
                    c = c3
    assert c is not None
    return c


def mec_of_geometry(geom: BaseGeometry, seed: int = 0) -> Circle:
    if geom.is_empty:
        return (0.0, 0.0, 0.0)

    hull = geom.convex_hull
    gtype = hull.geom_type

    if gtype == "Point":
        return (float(hull.x), float(hull.y), 0.0)

    if gtype == "LineString":
        pts = list(hull.coords)
    elif gtype == "Polygon":
        pts = list(hull.exterior.coords)[:-1]
    else:
        rp = hull.representative_point()
        return (float(rp.x), float(rp.y), 0.0)

    return minimum_enclosing_circle(pts, seed=seed)


def mec_of_samples(points: np.ndarray, seed: int = 0) -> Circle:
    if len(points) == 0:
        return (0.0, 0.0, 0.0)
    if len(points) == 1:
        return (float(points[0, 0]), float(points[0, 1]), 0.0)
    return minimum_enclosing_circle(
        [(float(x), float(y)) for x, y in points],
        seed=seed,
    )


# ============================================================
# 4. 在可行域中均匀采样（仅用于期望计算，不用于真实删域）
# ============================================================

def _contains_many(geom: BaseGeometry, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    if contains_xy is not None:
        return np.asarray(contains_xy(geom, xs, ys), dtype=bool)
    # 兼容回退；较慢
    return np.array([geom.contains(Point(float(x), float(y))) for x, y in zip(xs, ys)])


def sample_uniform_in_geometry(
    geom: BaseGeometry,
    n: int,
    rng: np.random.Generator,
) -> np.ndarray:
    if geom.is_empty or n <= 0:
        return np.empty((0, 2), dtype=float)

    minx, miny, maxx, maxy = geom.bounds
    if not all(map(math.isfinite, (minx, miny, maxx, maxy))):
        return np.empty((0, 2), dtype=float)

    if maxx-minx < 1e-10 and maxy-miny < 1e-10:
        rp = geom.representative_point()
        return np.repeat([[rp.x, rp.y]], n, axis=0).astype(float)

    collected: List[np.ndarray] = []
    total = 0
    trials = 0
    max_trials = 120

    while total < n and trials < max_trials:
        need = n - total
        batch = max(1000, need * 8)
        xs = rng.uniform(minx, maxx, batch)
        ys = rng.uniform(miny, maxy, batch)
        mask = _contains_many(geom, xs, ys)
        if np.any(mask):
            arr = np.column_stack([xs[mask], ys[mask]])
            collected.append(arr)
            total += len(arr)
        trials += 1

    if total == 0:
        rp = geom.representative_point()
        return np.repeat([[rp.x, rp.y]], n, axis=0).astype(float)

    pts = np.vstack(collected)
    if len(pts) >= n:
        return pts[:n]

    # 极细长几何时，样本不足就重复已有样本；仅影响期望近似，不影响真实可行域。
    idx = rng.integers(0, len(pts), size=n-len(pts))
    return np.vstack([pts, pts[idx]])


# ============================================================
# 5. 频道状态与真实可行域更新
# ============================================================

@dataclass
class ChannelState:
    channel: int
    feasible: BaseGeometry
    pi_exist: float
    direction_seen: bool = False
    cleared: bool = False
    absent_proved: bool = False
    near_pending: bool = False
    near_position: Optional[Tuple[float, float]] = None
    last_feedback: Optional[str] = None

    @property
    def terminal(self) -> bool:
        return self.cleared or self.absent_proved


class BeliefModel:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        # 初始域略放大 radial_margin，避免圆的多边形近似误删边界真值。
        self.initial_domain = safe_circle(
            (0.0, 0.0),
            cfg.target_radius + cfg.radial_margin,
            cfg,
        )

    def make_states(self) -> List[ChannelState]:
        return [
            ChannelState(
                channel=c,
                feasible=self.initial_domain,
                pi_exist=self.cfg.pi0,
            )
            for c in range(1, self.cfg.n_channels + 1)
        ]

    def update_after_measure(
        self,
        st: ChannelState,
        q: Tuple[float, float],
        feedback: str,
        direction_deg: Optional[float],
        p_no_given_exist_before: Optional[float],
    ) -> None:
        cfg = self.cfg
        P = st.feasible
        feedback = feedback.strip().lower()
        st.last_feedback = feedback

        if feedback == "near":
            # 保守：交 B(5+margin)
            B5 = safe_circle(q, cfg.near_radius + cfg.radial_margin, cfg)
            st.feasible = P.intersection(B5)
            st.pi_exist = 1.0
            st.near_pending = True
            st.near_position = (float(q[0]), float(q[1]))

        elif feedback == "direction":
            if direction_deg is None:
                raise ValueError("direction 反馈必须提供示向度。")

            B_outer = safe_circle(q, cfg.recv_max + cfg.radial_margin, cfg)
            # direction 已排除 d<=5。为了保守，实际只删到 5-margin。
            inner_r = max(0.0, cfg.near_radius - cfg.radial_margin)
            B_inner = safe_circle(q, inner_r, cfg)
            W = wedge_polygon(
                q,
                float(direction_deg),
                cfg.angle_error_deg + cfg.angular_margin_deg,
                P,
            )
            st.feasible = P.intersection(W).intersection(B_outer).difference(B_inner)
            st.pi_exist = 1.0
            st.direction_seen = True
            st.near_pending = False
            st.near_position = None

        elif feedback == "no_signal":
            # 对真实可行域，确定性排除 d <= 1000。
            # 为保守，实际只删除到 1000-margin。
            remove_r = max(0.0, cfg.recv_min - cfg.radial_margin)
            B_remove = safe_circle(q, remove_r, cfg)
            st.feasible = P.difference(B_remove)

            # 可选：更新频道存在概率 π_c（只影响滚动评分，不作为删域依据）。
            if p_no_given_exist_before is not None:
                pno = float(np.clip(p_no_given_exist_before, 0.0, 1.0))
                num = st.pi_exist * pno
                den = (1.0 - st.pi_exist) + num
                if den > 1e-15:
                    st.pi_exist = num / den

            st.near_pending = False
            st.near_position = None

            if st.feasible.is_empty or st.feasible.area <= cfg.area_eps:
                st.absent_proved = True
                st.pi_exist = 0.0

        else:
            raise ValueError(f"未知 measure 反馈: {feedback!r}")

    def update_after_clear(self, st: ChannelState, clear_feedback: str) -> None:
        fb = clear_feedback.strip().lower()
        if fb == "success":
            st.cleared = True
            st.pi_exist = 0.0
            st.near_pending = False
            st.near_position = None
        elif fb == "no_target_in_range":
            # 正常策略只在可保证成功时 clear；若失败，安全地删掉 20m 内区域，
            # 并继续滚动，而不是直接判定频道不存在。
            # 具体 clear 位置由 Planner 在调用前传给 run()，run() 会做更新。
            pass
        else:
            raise ValueError(f"未知 clear 反馈: {clear_feedback!r}")


# ============================================================
# 6. 候选动作评分
# ============================================================

@dataclass
class FeedbackPrediction:
    p_near: float
    p_dir: float
    p_no: float
    I_search: float
    I_locate: float


@dataclass
class MeasureAction:
    channel: int
    position: Tuple[float, float]
    score: float
    time_cost: float
    info_gain: float
    prediction: FeedbackPrediction


@dataclass
class ClearAction:
    channel: int
    position: Tuple[float, float]
    estimated_time: float
    reason: str


class RollingPlanner:
    def __init__(self, cfg: Config, belief: BeliefModel):
        self.cfg = cfg
        self.belief = belief
        self.rng = np.random.default_rng(cfg.rng_seed)

    def _candidate_positions(
        self,
        st: ChannelState,
        current_pos: Tuple[float, float],
    ) -> List[Tuple[float, float]]:
        cfg = self.cfg
        P = st.feasible

        points: List[Tuple[float, float]] = [tuple(map(float, current_pos))]

        if not P.is_empty:
            cent = P.centroid
            rep = P.representative_point()
            mec = mec_of_geometry(P, seed=cfg.rng_seed + st.channel)
            bases = [
                (float(cent.x), float(cent.y)),
                (float(rep.x), float(rep.y)),
                (float(mec[0]), float(mec[1])),
                tuple(map(float, current_pos)),
            ]

            # 多连通分支各放一个代表点，防止 no_signal 多次切割后遗漏残余分支。
            if P.geom_type == "MultiPolygon":
                geoms = sorted(list(P.geoms), key=lambda g: g.area, reverse=True)
                for g in geoms[:4]:
                    rp = g.representative_point()
                    bases.append((float(rp.x), float(rp.y)))

            radii = cfg.locate_ring_radii if st.direction_seen else cfg.search_ring_radii
            angles = np.linspace(0.0, 360.0, cfg.candidate_angles, endpoint=False)

            for bx, by in bases:
                points.append((bx, by))
                for r in radii:
                    if r <= 1e-12:
                        continue
                    for a in angles:
                        ar = math.radians(float(a))
                        points.append((bx + r*math.cos(ar), by + r*math.sin(ar)))

        # 去重
        dedup: Dict[Tuple[int, int], Tuple[float, float]] = {}
        for x, y in points:
            key = (int(round(x * 10.0)), int(round(y * 10.0)))  # 0.1m 精度
            dedup[key] = (float(x), float(y))

        pts = list(dedup.values())
        if len(pts) <= cfg.max_candidates_per_channel:
            return pts

        # 保留关键点 + 对其余点按距离当前点的“近/远混合”抽样。
        cx, cy = current_pos
        pts.sort(key=lambda p: math.hypot(p[0]-cx, p[1]-cy))
        n = cfg.max_candidates_per_channel
        n_near = max(4, n // 2)
        near = pts[:n_near]
        rest = pts[n_near:]
        if not rest:
            return near

        # 其余均匀取索引，避免只保留近点。
        idx = np.linspace(0, len(rest)-1, max(0, n-len(near))).astype(int)
        far_mix = [rest[i] for i in idx]
        return near + far_mix

    def _predict_for_candidate(
        self,
        st: ChannelState,
        q: Tuple[float, float],
        samples: np.ndarray,
    ) -> FeedbackPrediction:
        cfg = self.cfg

        if len(samples) == 0:
            return FeedbackPrediction(0.0, 0.0, 1.0, 0.0, 0.0)

        qv = np.array(q, dtype=float)
        delta = samples - qv[None, :]
        d = np.sqrt(np.sum(delta * delta, axis=1))
        bearings = (np.degrees(np.arctan2(delta[:, 1], delta[:, 0])) + 360.0) % 360.0

        # 三种反馈概率（条件于频道存在）
        near_mask = d <= cfg.near_radius
        w_dir = signal_probability_from_distance(d, cfg)
        w_dir = w_dir * (d > cfg.near_radius)

        p_near = float(np.mean(near_mask))
        p_dir = float(np.mean(w_dir))
        p_no = float(np.clip(1.0 - p_near - p_dir, 0.0, 1.0))

        # ---------------- 搜索阶段 I^S ----------------
        zeta_near = float(np.mean(near_mask))
        no_mask = d > cfg.recv_min
        zeta_no = float(np.mean(no_mask))

        zeta_dir_values: List[float] = []
        rho_dir_values: List[float] = []

        weight_sum = float(np.sum(w_dir))
        if weight_sum > 1e-15 and p_dir > 1e-12:
            probs = w_dir / weight_sum
            m = cfg.direction_outcome_samples
            chosen = self.rng.choice(len(samples), size=m, replace=True, p=probs)
            errors = self.rng.uniform(-cfg.angle_error_deg, cfg.angle_error_deg, size=m)

            for idx, err in zip(chosen, errors):
                theta = normalize_deg(float(bearings[idx] + err))
                ang_ok = np.abs(angle_diff_deg(bearings, theta)) <= cfg.angle_error_deg
                # 后验 P_dir 使用确定性 1500m 上界和 >5m 条件
                dir_mask = (
                    (d > cfg.near_radius)
                    & (d <= cfg.recv_max)
                    & ang_ok
                )
                zeta_dir_values.append(float(np.mean(dir_mask)))

                sub = samples[dir_mask]
                if len(sub) >= 2:
                    rho_dir_values.append(
                        mec_of_samples(sub, seed=int(cfg.rng_seed + int(idx)))[2]
                    )
                elif len(sub) == 1:
                    rho_dir_values.append(0.0)
                else:
                    # 不让有限样本造成虚假“超高信息收益”
                    rho_dir_values.append(float("nan"))
        else:
            zeta_dir_values = [1.0]
            rho_dir_values = [float("nan")]

        E_zeta_dir = float(np.nanmean(zeta_dir_values)) if zeta_dir_values else 1.0
        I_search = 1.0 - (
            p_near * zeta_near
            + p_no * zeta_no
            + p_dir * E_zeta_dir
        )
        I_search = float(np.clip(I_search, 0.0, 1.0))

        # ---------------- 定位阶段 I^L ----------------
        current_rho = mec_of_geometry(
            st.feasible,
            seed=cfg.rng_seed + 1000 + st.channel,
        )[2]

        if current_rho <= 1e-9:
            I_locate = 1.0
        else:
            # near 后验位于 5m 圆内；用 5m 作稳健上界。
            rho_near = min(cfg.near_radius, current_rho)

            no_sub = samples[no_mask]
            if len(no_sub) >= 2:
                rho_no = mec_of_samples(
                    no_sub,
                    seed=cfg.rng_seed + 2000 + st.channel,
                )[2]
            elif len(no_sub) == 1:
                rho_no = 0.0
            else:
                rho_no = 0.0

            clean_rhos = [x for x in rho_dir_values if math.isfinite(x)]
            if clean_rhos:
                E_rho_dir = float(np.mean(clean_rhos))
            else:
                E_rho_dir = current_rho

            expected_rho = (
                p_near * rho_near
                + p_no * rho_no
                + p_dir * E_rho_dir
            )
            I_locate = 1.0 - expected_rho / current_rho
            I_locate = float(np.clip(I_locate, 0.0, 1.0))

        return FeedbackPrediction(
            p_near=p_near,
            p_dir=p_dir,
            p_no=p_no,
            I_search=I_search,
            I_locate=I_locate,
        )

    def immediate_clear_action(
        self,
        states: Sequence[ChannelState],
        current_pos: Tuple[float, float],
    ) -> Optional[ClearAction]:
        cfg = self.cfg
        candidates: List[ClearAction] = []

        for st in states:
            if st.terminal:
                continue

            # near -> 直接当前位置清除
            if st.near_pending and st.near_position is not None:
                q = st.near_position
                t = math.hypot(q[0]-current_pos[0], q[1]-current_pos[1]) / cfg.speed
                t += cfg.clear_success_time
                candidates.append(ClearAction(
                    channel=st.channel,
                    position=q,
                    estimated_time=t,
                    reason="near",
                ))
                continue

            # 已确认存在且最小覆盖圆半径 <=20 -> 圆心清除
            if st.direction_seen and not st.feasible.is_empty:
                cx, cy, rho = mec_of_geometry(
                    st.feasible,
                    seed=cfg.rng_seed + 3000 + st.channel,
                )
                if rho <= cfg.clear_radius:
                    q = (cx, cy)
                    t = math.hypot(q[0]-current_pos[0], q[1]-current_pos[1]) / cfg.speed
                    t += cfg.clear_success_time
                    candidates.append(ClearAction(
                        channel=st.channel,
                        position=q,
                        estimated_time=t,
                        reason=f"MEC radius={rho:.3f}m",
                    ))

        if not candidates:
            return None

        # 处于“确定可清除”状态后，按最近清除优先。
        return min(candidates, key=lambda a: a.estimated_time)

    def choose_measure_action(
        self,
        states: Sequence[ChannelState],
        current_pos: Tuple[float, float],
        current_channel: int,
    ) -> MeasureAction:
        cfg = self.cfg
        best: Optional[MeasureAction] = None

        for st in states:
            if st.terminal or st.feasible.is_empty:
                continue

            samples = sample_uniform_in_geometry(
                st.feasible,
                cfg.belief_samples,
                self.rng,
            )
            if len(samples) == 0:
                continue

            for q in self._candidate_positions(st, current_pos):
                pred = self._predict_for_candidate(st, q, samples)

                move_time = math.hypot(
                    q[0]-current_pos[0],
                    q[1]-current_pos[1],
                ) / cfg.speed
                switch = cfg.switch_time if st.channel != current_channel else 0.0
                dt = move_time + switch + cfg.detect_time

                raw_info = (
                    cfg.beta_locate * pred.I_locate
                    if st.direction_seen
                    else cfg.alpha_search * pred.I_search
                )

                if cfg.use_existence_prior_in_score:
                    effective_info = st.pi_exist * raw_info
                else:
                    effective_info = raw_info

                score = dt - cfg.lambda_info * effective_info

                act = MeasureAction(
                    channel=st.channel,
                    position=q,
                    score=float(score),
                    time_cost=float(dt),
                    info_gain=float(effective_info),
                    prediction=pred,
                )
                if best is None or act.score < best.score:
                    best = act

        if best is None:
            raise RuntimeError("没有可用的 measure 候选动作；请检查可行域/停止条件。")
        return best


# ============================================================
# 7. 官方模拟器协议适配层
# ============================================================

class ProtocolAdapter:
    """
    适配官方模拟器 HTTP+JSON 协议。
    payload 必须包含 arena_id、robot_id、request_id。
    """

    def __init__(self, arena_id: str = "default"):
        self.arena_id = arena_id

    def _base(self, robot_id: str, request_id: str) -> Dict[str, Any]:
        return {
            "arena_id": self.arena_id,
            "robot_id": robot_id,
            "request_id": request_id,
        }

    def enter_payload(self, robot_id: str, request_id: str) -> Dict[str, Any]:
        return self._base(robot_id, request_id)

    def exit_payload(self, robot_id: str, request_id: str) -> Dict[str, Any]:
        return self._base(robot_id, request_id)

    def measure_payload(
        self,
        robot_id: str,
        request_id: str,
        position: Tuple[float, float],
        channel: int,
    ) -> Dict[str, Any]:
        payload = self._base(robot_id, request_id)
        payload.update({
            "position": {"x": float(position[0]), "y": float(position[1])},
            "channel": int(channel),
        })
        return payload

    def clear_payload(
        self,
        robot_id: str,
        request_id: str,
        position: Tuple[float, float],
        channel: int,
    ) -> Dict[str, Any]:
        payload = self._base(robot_id, request_id)
        payload.update({
            "position": {"x": float(position[0]), "y": float(position[1])},
            "channel": int(channel),
        })
        return payload

    @staticmethod
    def _walk_values(obj: Any) -> Iterable[Any]:
        if isinstance(obj, dict):
            for v in obj.values():
                yield v
                yield from ProtocolAdapter._walk_values(v)
        elif isinstance(obj, list):
            for v in obj:
                yield v
                yield from ProtocolAdapter._walk_values(v)

    @staticmethod
    def _find_numeric_by_keys(obj: Any, keys: Sequence[str]) -> Optional[float]:
        keyset = {k.lower() for k in keys}
        if isinstance(obj, dict):
            for k, v in obj.items():
                if str(k).lower() in keyset and isinstance(v, (int, float)):
                    return float(v)
            for v in obj.values():
                ans = ProtocolAdapter._find_numeric_by_keys(v, keys)
                if ans is not None:
                    return ans
        elif isinstance(obj, list):
            for v in obj:
                ans = ProtocolAdapter._find_numeric_by_keys(v, keys)
                if ans is not None:
                    return ans
        return None

    def parse_measure_response(self, data: Dict[str, Any]) -> Tuple[str, Optional[float]]:
        """
        尽量兼容常见返回结构。
        附件2若给出固定字段，建议改成“直接按字段取值”，更稳。
        """
        strings = [str(v).lower() for v in self._walk_values(data) if isinstance(v, str)]

        if any(s == "no_signal" for s in strings):
            return "no_signal", None
        if any(s == "near" for s in strings):
            return "near", None
        if any(s == "direction" for s in strings):
            angle = self._find_numeric_by_keys(
                data,
                ["svd_deg", "svd", "direction", "angle", "azimuth", "bearing", "degree", "degrees"],
            )
            if angle is None:
                raise ValueError(f"返回 direction 但找不到角度字段：{data}")
            return "direction", normalize_deg(angle)

        raise ValueError(
            "无法解析 /measure 返回。请按附件2修改 "
            f"ProtocolAdapter.parse_measure_response。原始返回={data}"
        )

    def parse_clear_response(self, data: Dict[str, Any]) -> str:
        strings = [str(v).lower() for v in self._walk_values(data) if isinstance(v, str)]
        if any(s == "success" for s in strings):
            return "success"
        if any(s == "no_target_in_range" for s in strings):
            return "no_target_in_range"
        raise ValueError(
            "无法解析 /clear 返回。请按附件2修改 "
            f"ProtocolAdapter.parse_clear_response。原始返回={data}"
        )


class SimulatorClient:
    def __init__(
        self,
        robot_id: str,
        cfg: Config,
        base_url: str = "http://127.0.0.1:2026",
        adapter: Optional[ProtocolAdapter] = None,
    ):
        self.robot_id = robot_id
        self.cfg = cfg
        self.base_url = base_url.rstrip("/")
        self.adapter = adapter or ProtocolAdapter()
        self.session = requests.Session()

    def _new_request_id(self) -> str:
        return uuid.uuid4().hex

    def _post_same_request_on_retry(
        self,
        path: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        网络中断重试时复用同一 payload 和同一 request_id，
        符合附件1的要求。
        """
        url = self.base_url + path
        last_err: Optional[Exception] = None

        for attempt in range(self.cfg.http_retries):
            try:
                resp = self.session.post(
                    url,
                    json=payload,
                    timeout=self.cfg.http_timeout,
                )
                resp.raise_for_status()
                data = resp.json()
                if not isinstance(data, dict):
                    raise ValueError(f"返回 JSON 不是对象：{data!r}")
                return data
            except Exception as e:
                last_err = e
                if attempt + 1 >= self.cfg.http_retries:
                    break
                time.sleep(self.cfg.retry_wait * (attempt + 1))

        raise RuntimeError(f"请求 {path} 失败：{last_err}") from last_err

    def enter(self) -> Dict[str, Any]:
        rid = self._new_request_id()
        payload = self.adapter.enter_payload(self.robot_id, rid)
        return self._post_same_request_on_retry("/enter", payload)

    def exit(self) -> Dict[str, Any]:
        rid = self._new_request_id()
        payload = self.adapter.exit_payload(self.robot_id, rid)
        return self._post_same_request_on_retry("/exit", payload)

    def measure(
        self,
        position: Tuple[float, float],
        channel: int,
    ) -> Tuple[Dict[str, Any], str, Optional[float]]:
        rid = self._new_request_id()
        payload = self.adapter.measure_payload(
            self.robot_id, rid, position, channel
        )
        data = self._post_same_request_on_retry("/measure", payload)
        fb, theta = self.adapter.parse_measure_response(data)
        return data, fb, theta

    def clear(
        self,
        position: Tuple[float, float],
        channel: int,
    ) -> Tuple[Dict[str, Any], str]:
        rid = self._new_request_id()
        payload = self.adapter.clear_payload(
            self.robot_id, rid, position, channel
        )
        data = self._post_same_request_on_retry("/clear", payload)
        fb = self.adapter.parse_clear_response(data)
        return data, fb


# ============================================================
# 8. 主滚动循环
# ============================================================

def all_done(states: Sequence[ChannelState], cfg: Config) -> bool:
    cleared = sum(st.cleared for st in states)
    if cleared >= cfg.max_sources:
        return True
    return all(st.terminal for st in states)


def estimate_p_no_given_exist_at_action(
    planner: RollingPlanner,
    st: ChannelState,
    q: Tuple[float, float],
) -> float:
    samples = sample_uniform_in_geometry(
        st.feasible,
        planner.cfg.belief_samples,
        planner.rng,
    )
    pred = planner._predict_for_candidate(st, q, samples)
    return pred.p_no


def run_strategy(
    client: SimulatorClient,
    cfg: Config,
    verbose: bool = True,
) -> Dict[str, Any]:
    belief = BeliefModel(cfg)
    states = belief.make_states()
    planner = RollingPlanner(cfg, belief)

    current_pos = (0.0, 0.0)
    current_channel = 1
    action_log: List[Dict[str, Any]] = []

    enter_resp = client.enter()
    if verbose:
        print("[ENTER]", json.dumps(enter_resp, ensure_ascii=False))

    for step in range(1, cfg.max_actions + 1):
        if all_done(states, cfg):
            if verbose:
                print(f"[STOP] step={step}: 已满足停止条件")
            break

        # 1) 有确定可清除目标时，直接清除
        clear_act = planner.immediate_clear_action(states, current_pos)
        if clear_act is not None:
            st = states[clear_act.channel - 1]
            raw, fb = client.clear(clear_act.position, clear_act.channel)

            # clear 不改变测向机频道
            current_pos = clear_act.position

            if fb == "success":
                belief.update_after_clear(st, fb)
            else:
                # 安全利用 clear 失败信息：20m 内无该频道目标。
                # 为保守，删到 20-margin。
                remove_r = max(0.0, cfg.clear_radius - cfg.radial_margin)
                st.feasible = st.feasible.difference(
                    safe_circle(current_pos, remove_r, cfg)
                )
                belief.update_after_clear(st, fb)
                if st.feasible.is_empty or st.feasible.area <= cfg.area_eps:
                    st.absent_proved = True
                    st.pi_exist = 0.0

            rec = {
                "step": step,
                "action": "clear",
                "channel": clear_act.channel,
                "position": list(clear_act.position),
                "reason": clear_act.reason,
                "feedback": fb,
                "raw": raw,
            }
            action_log.append(rec)
            if verbose:
                print("[CLEAR]", json.dumps(rec, ensure_ascii=False))
            continue

        # 2) 否则滚动选择 J 最小的 measure
        act = planner.choose_measure_action(
            states,
            current_pos=current_pos,
            current_channel=current_channel,
        )
        st = states[act.channel - 1]

        # no_signal 时更新 pi 需要用动作执行前的 p(no|exist)
        pno_before = act.prediction.p_no

        raw, fb, theta = client.measure(act.position, act.channel)

        current_pos = act.position
        current_channel = act.channel  # measure 会切换并停留在该频道

        belief.update_after_measure(
            st=st,
            q=act.position,
            feedback=fb,
            direction_deg=theta,
            p_no_given_exist_before=pno_before,
        )

        rec = {
            "step": step,
            "action": "measure",
            "channel": act.channel,
            "position": list(act.position),
            "score": act.score,
            "time_cost_est": act.time_cost,
            "info_gain_est": act.info_gain,
            "pi_exist_after": st.pi_exist,
            "feedback": fb,
            "direction": theta,
            "feasible_area": 0.0 if st.feasible.is_empty else st.feasible.area,
            "raw": raw,
        }
        action_log.append(rec)
        if verbose:
            print("[MEASURE]", json.dumps(rec, ensure_ascii=False))

    else:
        print(f"[WARN] 达到 max_actions={cfg.max_actions}，主动退出。")

    exit_resp = client.exit()
    if verbose:
        print("[EXIT]", json.dumps(exit_resp, ensure_ascii=False))

    result = {
        "cleared_count": sum(st.cleared for st in states),
        "absent_proved_count": sum(st.absent_proved for st in states),
        "current_position": current_pos,
        "current_channel": current_channel,
        "states": [
            {
                "channel": st.channel,
                "cleared": st.cleared,
                "absent_proved": st.absent_proved,
                "direction_seen": st.direction_seen,
                "pi_exist": st.pi_exist,
                "feasible_area": 0.0 if st.feasible.is_empty else st.feasible.area,
            }
            for st in states
        ],
        "action_log": action_log,
        "exit_response": exit_resp,
    }
    return result


# ============================================================
# 9. CLI
# ============================================================

def print_hyperparameter_ranges() -> None:
    print("建议调参范围：")
    for k, v in HYPERPARAM_RANGES.items():
        print(f"  {k:30s}: {v}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="问题三：期望信息增益滚动搜索/定位/清除"
    )
    parser.add_argument(
        "--robot-id",
        required=True,
        help="当前登录参赛队号（附件1要求作为 robot_id）",
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:2026",
        help="模拟器接口地址",
    )
    parser.add_argument(
        "--log",
        default="q3_action_log.json",
        help="本地动作日志输出文件",
    )
    parser.add_argument(
        "--show-ranges",
        action="store_true",
        help="运行前打印建议超参数范围",
    )
    args = parser.parse_args()

    cfg = Config()
    if args.show_ranges:
        print_hyperparameter_ranges()

    client = SimulatorClient(
        robot_id=args.robot_id,
        cfg=cfg,
        base_url=args.base_url,
    )

    result = run_strategy(client, cfg, verbose=True)
    with open(args.log, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"本地日志已保存：{args.log}")


if __name__ == "__main__":
    main()
