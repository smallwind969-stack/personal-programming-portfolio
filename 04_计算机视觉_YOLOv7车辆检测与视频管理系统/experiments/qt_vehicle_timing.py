"""Measure the production Qt worker's frame-to-result timing without the MySQL UI."""

import json
import statistics
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import torch
from PyQt5.QtCore import QCoreApplication, QTimer


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vehicle_detector import VehicleDetector
from video_detection import DetectionThread, should_display_detection_result


def main():
    torch.set_num_threads(1)
    bus_path = ROOT / "inference" / "images" / "bus.jpg"
    bus = cv2.imdecode(np.fromfile(bus_path, dtype=np.uint8), cv2.IMREAD_COLOR)
    bus = cv2.resize(bus, (500, 667))
    base_detector = VehicleDetector(weights=str(ROOT / "yolov7.pt"), device="0", trace=False)
    detector_times = []
    detector_starts = []

    class TimedDetector:
        def detect(self, frame):
            started = time.perf_counter()
            detector_starts.append(started)
            result = base_detector.detect(frame)
            torch.cuda.synchronize()
            detector_times.append((time.perf_counter() - started) * 1000)
            return result

    detector = TimedDetector()
    app = QCoreApplication([])
    timer = QTimer()
    frame_count = 60
    state = {"next_frame": 0, "pending": False, "last_displayed": -1, "dropped": 0}
    latencies = []
    started_at = {}
    worker = DetectionThread(detector)

    def on_result(session, frame_id, frame, labels, boxes):
        state["pending"] = False
        if should_display_detection_result(1, session, state["last_displayed"], frame_id):
            state["last_displayed"] = frame_id
            latencies.append((time.perf_counter() - started_at[frame_id]) * 1000)
            assert frame[25, 100 + frame_id * 5, 0] != 160
            assert any(label.startswith("bus ") for label in labels) == bool(boxes)
        if state["next_frame"] == frame_count:
            timer.stop()
            app.quit()

    def tick():
        frame_id = state["next_frame"]
        if frame_id == frame_count:
            if not state["pending"]:
                timer.stop()
                app.quit()
            return
        state["next_frame"] += 1
        if state["pending"]:
            state["dropped"] += 1
            return
        frame = np.full((720, 1280, 3), 160, dtype=np.uint8)
        x = 100 + frame_id * 5
        frame[25:692, x:x + 500] = bus
        started_at[frame_id] = time.perf_counter()
        state["pending"] = worker.submit(frame, session_id=1, frame_id=frame_id)
        if not state["pending"]:
            state["dropped"] += 1

    worker.detection_complete.connect(on_result)
    worker.error_occurred.connect(lambda message: (_ for _ in ()).throw(RuntimeError(message)))
    worker.start()
    timer.timeout.connect(tick)
    timer.start(33)
    app.exec_()
    worker.stop()
    worker.wait()
    report = {
        "source": "60 synthetic bus frames through production DetectionThread and Qt event loop",
        "target_fps": 30,
        "displayed_frames": len(latencies),
        "dropped_frames": state["dropped"],
        "frame_to_result_p50_ms": round(statistics.median(latencies), 2),
        "frame_to_result_p95_ms": round(float(np.percentile(latencies, 95)), 2),
        "detector_p50_ms": round(statistics.median(detector_times), 2),
        "dispatch_to_detect_p50_ms": round(statistics.median([
            (start - started_at[frame_id]) * 1000
            for start, frame_id in zip(detector_starts, sorted(started_at))
            if frame_id < len(detector_starts)
        ]), 2),
        "stale_cross_frame_overlays": 0,
    }
    output = ROOT / "experiments" / "output"
    output.mkdir(parents=True, exist_ok=True)
    (output / "qt_vehicle_timing.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
