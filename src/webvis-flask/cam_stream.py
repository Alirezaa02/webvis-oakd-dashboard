# cam_stream_picamera2.py
from flask import Flask, Response
from picamera2 import Picamera2
import cv2, time, os

app = Flask(__name__)
PORT = int(os.environ.get("PORT", "5066"))

picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"size": (1280, 720)})
picam2.configure(config)
picam2.start()

def gen():
    while True:
        frame = picam2.capture_array()
        ret, jpg = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if not ret:
            time.sleep(0.05)
            continue
        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpg.tobytes() + b"\r\n")

@app.get("/video_feed")
def video_feed():
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, threaded=True)
