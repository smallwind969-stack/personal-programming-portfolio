from queue import Empty, Full, Queue

from PyQt5.QtCore import QThread, pyqtSignal


def should_display_detection_result(current_session, result_session, last_frame_id, frame_id):
    return result_session == current_session and frame_id > last_frame_id


class DetectionThread(QThread):
    detection_complete = pyqtSignal(int, int, object, list, list)
    error_occurred = pyqtSignal(str)

    def __init__(self, detector):
        super().__init__()
        self.detector = detector
        self.frames = Queue(maxsize=1)
        self.stopping = False

    def submit(self, frame, session_id, frame_id):
        if self.stopping or not self.isRunning():
            return False
        try:
            self.frames.put_nowait((session_id, frame_id, frame.copy()))
            return True
        except Full:
            return False

    def stop(self):
        if self.stopping:
            return
        self.stopping = True
        try:
            self.frames.get_nowait()
        except Empty:
            pass
        self.frames.put_nowait(None)

    def run(self):
        while True:
            item = self.frames.get()
            if item is None:
                return
            session_id, frame_id, frame = item
            try:
                labels, boxes = self.detector.detect(frame)
                self.detection_complete.emit(session_id, frame_id, frame, labels, boxes)
            except Exception as exc:
                self.error_occurred.emit(f"车辆检测失败: {exc}")
