import time
import unittest

import numpy as np
from PyQt5.QtCore import QCoreApplication

from video_detection import DetectionThread, should_display_detection_result


class FakeDetector:
    def detect(self, frame):
        time.sleep(0.01)
        return ["car 0.90"], [(int(frame[0, 0, 0]), 1, 8, 8)]


class VideoDetectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def test_worker_returns_boxes_with_their_source_frame(self):
        frame = np.full((12, 12, 3), 4, dtype=np.uint8)
        results = []
        worker = DetectionThread(FakeDetector())
        worker.detection_complete.connect(lambda *args: results.append(args))
        worker.start()
        self.assertTrue(worker.submit(frame, session_id=2, frame_id=9))
        deadline = time.perf_counter() + 3
        while not results and time.perf_counter() < deadline:
            self.app.processEvents()
            time.sleep(0.005)
        worker.stop()
        self.assertTrue(worker.wait(3000))

        self.assertEqual(len(results), 1)
        session_id, frame_id, source_frame, labels, boxes = results[0]
        self.assertEqual((session_id, frame_id), (2, 9))
        self.assertEqual(labels, ["car 0.90"])
        self.assertEqual(boxes, [(4, 1, 8, 8)])
        self.assertTrue(np.array_equal(source_frame, frame))
        self.assertIsNot(source_frame, frame)

    def test_results_from_old_session_or_old_frame_are_rejected(self):
        self.assertFalse(should_display_detection_result(3, 2, 7, 8))
        self.assertFalse(should_display_detection_result(3, 3, 7, 7))
        self.assertTrue(should_display_detection_result(3, 3, 7, 8))

    def test_worker_reuses_thread_for_successive_frames_and_stops_cleanly(self):
        results = []
        worker = DetectionThread(FakeDetector())
        worker.detection_complete.connect(lambda *args: results.append(args))
        worker.start()
        for frame_id in (1, 2):
            frame = np.full((12, 12, 3), frame_id, dtype=np.uint8)
            self.assertTrue(worker.submit(frame, session_id=4, frame_id=frame_id))
            deadline = time.perf_counter() + 3
            while len(results) < frame_id and time.perf_counter() < deadline:
                self.app.processEvents()
                time.sleep(0.005)
        worker.stop()
        worker.stop()
        self.assertTrue(worker.wait(3000))
        self.assertFalse(worker.submit(frame, session_id=4, frame_id=3))
        self.assertEqual([result[1] for result in results], [1, 2])
        self.assertEqual([result[4][0][0] for result in results], [1, 2])


if __name__ == "__main__":
    unittest.main()
