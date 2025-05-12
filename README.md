# 🎥 RTSP CCTV Viewer

A simple multithreaded RTSP CCTV stream viewer built with Python and OpenCV. 📡

---

## 🚀 Quick Start

1. **Clone the repo**

   ```bash
   git clone https://github.com/GerasimosKan/rtsp-cctv.git
   cd rtsp-cctv
   ```
2. **Create a virtual environment**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # macOS/Linux
   venv\Scripts\activate     # Windows
   ```
3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```
4. **Add your RTSP URLs**

   * Open `streams.txt` and add one RTSP URL per line:

     ```txt
     rtsp://username:password@camera-ip/stream
     ```
5. **Run the viewer**

   ```bash
   python main.py
   ```

---

## 📦 Requirements

* Python 3.7+
* OpenCV (`opencv-python`)
* NumPy (`numpy`)

All other libs are in the standard library.