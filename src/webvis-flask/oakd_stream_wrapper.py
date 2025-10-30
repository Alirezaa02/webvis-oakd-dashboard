from flask import Flask, Response
import cv2, time
from utility.oakd_capture import OakDLite  

app = Flask(__name__)
oak = OakDLite()          # uses the OAK-D on the Pi
oak.start()

def gen():
    while True:
        frame = oak.get_video_frame() or oak.get_preview_frame()
        if frame is None:
            time.sleep(0.05)
            continue
        ok, jpg = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if ok:
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpg.tobytes() + b"\r\n")

@app.get("/video_feed")
def video_feed():
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")

if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=5066, threaded=True)  # use 5066 so we don't collide with 5051
    finally:
        oak.close()
