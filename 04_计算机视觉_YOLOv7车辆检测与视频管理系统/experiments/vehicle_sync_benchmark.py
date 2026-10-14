"""Measure vehicle box alignment on a reproducible fast-pan sequence."""

import json
import statistics
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vehicle_detector import VehicleDetector


OUTPUT = ROOT / "experiments" / "output"
FRAME_COUNT = 45
STALE_FRAMES = 8


def overlap(left, right):
    x1 = max(left[0], right[0])
    y1 = max(left[1], right[1])
    x2 = min(left[2], right[2])
    y2 = min(left[3], right[3])
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    area_left = max(0, left[2] - left[0]) * max(0, left[3] - left[1])
    area_right = max(0, right[2] - right[0]) * max(0, right[3] - right[1])
    return intersection / max(area_left + area_right - intersection, 1)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    bus_path = ROOT / "inference" / "images" / "bus.jpg"
    bus = cv2.imdecode(np.fromfile(bus_path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if bus is None:
        raise RuntimeError("Missing local bus.jpg test image")
    bus = cv2.resize(bus, (500, 667))
    detector = VehicleDetector(weights=str(ROOT / "yolov7.pt"), device="0", trace=False)

    frames = []
    boxes = []
    times = []
    for index in range(FRAME_COUNT):
        frame = np.full((720, 1280, 3), 160, dtype=np.uint8)
        x = 100 + index * 12
        frame[25:692, x:x + 500] = bus
        torch.cuda.synchronize()
        started = time.perf_counter()
        labels, found = detector.detect(frame)
        torch.cuda.synchronize()
        times.append((time.perf_counter() - started) * 1000)
        frames.append(frame)
        bus_boxes = [box for label, box in zip(labels, found) if label.startswith("bus ")]
        boxes.append(bus_boxes[0] if bus_boxes else None)

    paired = [index for index in range(STALE_FRAMES, FRAME_COUNT)
              if boxes[index] and boxes[index - STALE_FRAMES]]
    stale_ious = [overlap(boxes[index - STALE_FRAMES], boxes[index]) for index in paired]
    report = {
        "source": "synthetic horizontal pan of repository bus.jpg; not a road-video test",
        "gpu": torch.cuda.get_device_name(0),
        "frame_count": FRAME_COUNT,
        "frame_rate_target": 30,
        "pixels_per_frame": 12,
        "model_input_size": detector.img_size,
        "detected_bus_frames": sum(box is not None for box in boxes),
        "gpu_detection_p50_ms": round(statistics.median(times[5:]), 2),
        "gpu_detection_p95_ms": round(float(np.percentile(times[5:], 95)), 2),
        "stale_box_offset_frames": STALE_FRAMES,
        "stale_box_median_iou": round(statistics.median(stale_ious), 3) if stale_ious else None,
        "paired_box_alignment": "exact source frame, no cross-frame overlay",
    }
    (OUTPUT / "vehicle_sync_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    sample = 25
    comparison = []
    for stale in (True, False):
        canvas = frames[sample].copy()
        box = boxes[sample - STALE_FRAMES] if stale else boxes[sample]
        if box:
            cv2.rectangle(canvas, box[:2], box[2:], (0, 0, 255) if stale else (0, 255, 0), 4)
        cv2.putText(canvas, "OLD: stale box" if stale else "NEW: paired frame",
                    (30, 45), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 3)
        comparison.append(cv2.resize(canvas, (640, 360)))
    cv2.imencode(".png", cv2.hconcat(comparison))[1].tofile(
        OUTPUT / "vehicle_sync_comparison.png"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
