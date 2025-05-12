import cv2
import numpy as np
import math
import threading
import time
import argparse
import vlc

AUDIO_ICON_ON = "ON"
AUDIO_ICON_OFF = "OFF"

class StreamThread(threading.Thread):
    def __init__(self, url, name=None):
        super().__init__()
        self.url = url
        self.name = name or url
        self.frame = None
        self.lock = threading.Lock()
        self.cap = None
        self.stopped = threading.Event()
        self.audio_player = None
        self.audio_enabled = False

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

    def _reconnect(self):
        print(f"[{self.name}] Reconnecting...")
        if self.cap:
            self.cap.release()
        if self.audio_player:
            self.audio_player.stop()
            self.audio_player.release()
        time.sleep(1)
        self._connect()
        if self.audio_enabled:
            self._start_audio()

    def _start_audio(self):
        self.audio_player = vlc.MediaPlayer(self.url)
        self.audio_player.play()

    def _stop_audio(self):
        if self.audio_player:
            self.audio_player.stop()
            self.audio_player.release()
            self.audio_player = None

    def toggle_audio(self):
        if self.audio_enabled:
            self._stop_audio()
        else:
            self._start_audio()
        self.audio_enabled = not self.audio_enabled

    def get_frame(self):
        with self.lock:
            return self.frame.copy() if self.frame is not None else None

    def stop(self):
        self.stopped.set()
        if self.cap:
            self.cap.release()
        self._stop_audio()


def create_grid(frames, grid_dims, window_size, stream_names=None, stream_objs=None):
    rows, cols = grid_dims
    w, h = window_size
    grid = np.zeros((h, w, 3), dtype=np.uint8)
    cell_w = w // cols
    cell_h = h // rows
    positions = []

    for i, frame in enumerate(frames):
        if frame is None:
            positions.append(None)
            continue

        resized = cv2.resize(frame, (cell_w, cell_h), interpolation=cv2.INTER_AREA)

        # Draw stream name
        if stream_names:
            cv2.putText(resized, stream_names[i], (10, 25), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (0, 255, 0), 2)

        # Draw audio toggle button
        if stream_objs:
            status = stream_objs[i].audio_enabled
            icon = AUDIO_ICON_ON if status else AUDIO_ICON_OFF
            btn_x = cell_w - 60
            btn_y = 10
            cv2.rectangle(resized, (btn_x, btn_y), (btn_x + 50, btn_y + 30),
                          (255, 255, 0), -1)
            cv2.putText(resized, icon, (btn_x + 5, btn_y + 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

        x = (i % cols) * cell_w
        y = (i // cols) * cell_h
        grid[y:y + cell_h, x:x + cell_w] = resized
        positions.append(((x, y), (x + cell_w, y + cell_h)))  # top-left and bottom-right

    return grid, positions


def load_streams_from_file(filepath):
    try:
        with open(filepath) as f:
            urls = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"[Error] File not found: {filepath}")
        urls = []
    return urls


def main():
    parser = argparse.ArgumentParser(description="Multi RTSP Stream Viewer with Audio Toggle")
    parser.add_argument("--file", type=str, default="streams.txt", help="Text file with RTSP stream URLs")
    parser.add_argument("--fullscreen", action="store_true", help="Start in fullscreen")
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

    last_positions = []

    def on_mouse(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            for i, region in enumerate(last_positions):
                if region:
                    (x1, y1), (x2, y2) = region
                    btn_x1 = x2 - 60
                    btn_y1 = y1 + 10
                    btn_x2 = btn_x1 + 50
                    btn_y2 = btn_y1 + 30
                    if btn_x1 <= x <= btn_x2 and btn_y1 <= y <= btn_y2:
                        streams[i].toggle_audio()
                        print(f"Toggled audio on {streams[i].name}")

    cv2.setMouseCallback("Stream Viewer", on_mouse)

    try:
        while True:
            frames = [s.get_frame() for s in streams]
            active_frames = [f for f in frames if f is not None]
            if not active_frames:
                time.sleep(0.5)
                continue

            rows = math.ceil(math.sqrt(len(streams)))
            cols = math.ceil(len(streams) / rows)

            grid, last_positions = create_grid(frames, (rows, cols), (width, height),
                                               stream_names=[s.name for s in streams],
                                               stream_objs=streams)
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
