import cv2
import numpy as np
import math
import threading
import time
import argparse


class StreamThread(threading.Thread):
    def __init__(self, url, name=None):
        super().__init__()
        self.url = url
        self.name = name or url
        self.frame = None
        self.lock = threading.Lock()
        self.cap = None
        self.stopped = threading.Event()

    def run(self):
        self._connect()

        while not self.stopped.is_set():
            if self.cap is None or not self.cap.isOpened():
                self._reconnect()
                continue

            ret, frame = self.cap.read()
            if ret:
                with self.lock:
                    self.frame = frame.copy()
            else:
                time.sleep(1)
                self._reconnect()

    def _connect(self):
        self.cap = cv2.VideoCapture(self.url)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))  # fallback codec
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

    def _reconnect(self):
        print(f"[{self.name}] Reconnecting...")
        if self.cap:
            self.cap.release()
        time.sleep(1)
        self._connect()

    def get_frame(self):
        with self.lock:
            return self.frame.copy() if self.frame is not None else None

    def stop(self):
        self.stopped.set()
        if self.cap:
            self.cap.release()


def create_grid(frames, grid_dims, window_size, overlay=False, stream_names=None):
    rows, cols = grid_dims
    w, h = window_size
    grid = np.zeros((h, w, 3), dtype=np.uint8)

    cell_w = w // cols
    cell_h = h // rows

    for i, frame in enumerate(frames):
        if frame is None:
            continue

        resized = cv2.resize(frame, (cell_w, cell_h), interpolation=cv2.INTER_AREA)

        if overlay and stream_names:
            cv2.putText(resized, f"{stream_names[i]}", (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        x = (i % cols) * cell_w
        y = (i // cols) * cell_h
        grid[y:y + cell_h, x:x + cell_w] = resized

    return grid


def load_streams_from_file(filepath):
    try:
        with open(filepath) as f:
            urls = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"[Error] File not found: {filepath}")
        urls = []
    return urls


def main():
    parser = argparse.ArgumentParser(description="Multi RTSP Stream Viewer")
    parser.add_argument("--file", type=str, default="streams.txt", help="Text file with RTSP stream URLs")
    parser.add_argument("--fullscreen", action="store_true", help="Start in fullscreen")
    parser.add_argument("--overlay", action="store_true", help="Overlay stream info on each feed")
    parser.add_argument("--window-size", type=str, default="1920x1080", help="Window resolution (e.g. 1280x720)")
    args = parser.parse_args()

    width, height = map(int, args.window_size.lower().split('x'))
    urls = load_streams_from_file(args.file)
    if not urls:
        print("No valid streams found.")
        return

    print(f"Starting viewer with {len(urls)} streams.")

    streams = [StreamThread(url, name=f"Cam {i+1}") for i, url in enumerate(urls)]
    for stream in streams:
        stream.start()

    cv2.namedWindow("Stream Viewer", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Stream Viewer", width, height)

    if args.fullscreen:
        cv2.setWindowProperty("Stream Viewer", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    try:
        while True:
            frames = [s.get_frame() for s in streams]
            active_frames = [f for f in frames if f is not None]
            if not active_frames:
                time.sleep(0.5)
                continue

            rows = math.ceil(math.sqrt(len(active_frames)))
            cols = math.ceil(len(active_frames) / rows)

            grid = create_grid(active_frames, (rows, cols), (width, height), overlay=args.overlay, stream_names=[s.name for s in streams])
            cv2.imshow("Stream Viewer", grid)

            key = cv2.waitKey(1)
            if key == 27:
                break
            elif key == ord('f'):
                current = cv2.getWindowProperty("Stream Viewer", cv2.WND_PROP_FULLSCREEN)
                new_state = cv2.WINDOW_NORMAL if current == 1.0 else cv2.WINDOW_FULLSCREEN
                cv2.setWindowProperty("Stream Viewer", cv2.WND_PROP_FULLSCREEN, new_state)
    finally:
        print("Shutting down...")
        for s in streams:
            s.stop()
        for s in streams:
            s.join()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
