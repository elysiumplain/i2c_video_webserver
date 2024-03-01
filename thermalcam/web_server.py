# -*- coding: utf-8 -*-
#!/usr/bin/python3
##################################
# Flask web server for MLX90640 Thermal Camera w Raspberry Pi
# If running directly, run from root folder, not pithermalcam folder
##################################
try:
    from thermalcam.pi_thermal_cam import PiThermalCam
except:
    from pi_thermal_cam import PiThermalCam
from flask import Response, request
from flask import Flask
from flask import render_template
import threading
import time, socket, logging, traceback
import cv2
import subprocess
import inspect


# Set up Logger
logging.basicConfig(
    filename="thermal_server.log",
    filemode="a",
    format="%(asctime)s %(levelname)-8s [%(filename)s:%(name)s:%(lineno)d] %(message)s",
    level=logging.WARNING,
    datefmt="%d-%b-%y %H:%M:%S",
)
logger = logging.getLogger(__name__)

# initialize the output frame and a lock used to ensure thread-safe exchanges of the output frames (useful when multiple browsers/tabs are viewing the stream)
outputFrame = None
thermcam = None
lock = threading.Lock()

# initialize a flask object
app = Flask(__name__)


@app.route("/")
def index():
    # return the rendered template
    return render_template("index.html")


# background processes happen without any refreshing (for button clicks)
@app.route("/save")
def save_image():
    thermcam.save_image()
    return "Snapshot Saved"


@app.route("/units")
def change_units():
    thermcam.use_f = not thermcam.use_f
    return {"use_f": thermcam.use_f}


@app.route("/colormap")
def get_colormap():
    colormap = thermcam._colormap_list[thermcam._colormap_index]
    return {"colormap": colormap}


@app.route("/colormap/next")
def next_colormap():
    thermcam.change_colormap()
    colormap = thermcam._colormap_list[thermcam._colormap_index]
    return {"colormap": colormap}


@app.route("/colormap/prev")
def prev_colormap():
    thermcam.change_colormap(forward=False)
    colormap = thermcam._colormap_list[thermcam._colormap_index]
    return {"colormap": colormap}


@app.route("/filter")
def toggle_filter():
    thermcam.filter_image = not thermcam.filter_image
    return {"filter": thermcam.filter_image}


@app.route("/interpolation")
def get_interpolation():
    interpolation = thermcam._interpolation
    return {"interpolation": interpolation.fname}


@app.route("/interpolation/next")
def next_interpolation():
    thermcam.change_interpolation()
    interpolation = thermcam._interpolation
    return {"interpolation": interpolation.fname}


@app.route("/interpolation/prev")
def prev_interpolation():
    thermcam.change_interpolation(previous=True)
    interpolation = thermcam._interpolation
    return {"interpolation": interpolation.fname}


@app.route("/exit")
def appexit():
    global thermcam
    func = request.environ.get("werkzeug.server.shutdown")
    if func is None:
        raise RuntimeError("Not running with the Werkzeug Server")
    func()
    thermcam = None
    return "Server shutting down..."


@app.route("/video_feed")
def video_feed():
    # return the response generated along with the specific media
    # type (mime type)
    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")


def get_ip_address(publish=False):
    """Find the current IP address of the device"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        if publish:
            process = subprocess.Popen(
                ["curl", "-4", "ifconfig.me"], stdout=subprocess.PIPE
            )
            output, _ = process.communicate()
            ip_address = output.decode("utf-8").strip()
        else:
            s.connect(("8.8.8.8", 80))
            ip_address = s.getsockname()[0]
    finally:
        s.close()
    return ip_address


def pull_images():
    global thermcam, outputFrame
    # loop over frames from the video stream
    while thermcam is not None:
        current_frame = None
        try:
            current_frame = thermcam.update_image_frame()
        except Exception:
            print("Too many retries error caught; continuing...")
            logger.info(traceback.format_exc())

        # If we have a frame, acquire the lock, set the output frame, and release the lock
        if current_frame is not None:
            with lock:
                outputFrame = current_frame.copy()


def generate():
    # grab global references to the output frame and lock variables
    global outputFrame, lock
    # loop over frames from the output stream
    while True:
        # wait until the lock is acquired
        with lock:
            # check if the output frame is available, otherwise skip the iteration of the loop
            if outputFrame is None:
                continue
            # encode the frame in JPEG format
            (flag, encodedImage) = cv2.imencode(".jpg", outputFrame)
            # ensure the frame was successfully encoded
            if not flag:
                continue
        # yield the output frame in the byte format
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + bytearray(encodedImage) + b"\r\n"
        )


def start_server(
    thermal_cam_instance,
    publish=False,
    port=8000,
    output_folder: str = "/home/pi/Desktop/mlxFLIRCam/saved_snapshots/",
    **kwargs,
):
    global thermcam
    unknown_keys = [kw for kw in kwargs.keys()]
    if unknown_keys:
        logger.warning(
            f"Keys: {list(unknown_keys)} are not yet defined within the function. This feature may not be implemented yet, or you may have a bad configuration file."
        )
    # initialize the video stream and allow the camera sensor to warmup
    thermcam = thermal_cam_instance
    time.sleep(0.1)

    #  TODO: expand threading to process image derivatives for thermal changes without disrupting camera stream (min/max variation? hot/cold-spot movement across visual field?).
    # start a thread that will capture single frames.
    t = threading.Thread(target=pull_images)
    t.daemon = True
    t.start()

    if publish:
        ip = get_ip_address(publish=True)
    else:
        ip = get_ip_address()
    print(f"Server can be found at {ip}:{port}")

    # start the flask app
    app.run(host=ip, port=port, debug=False, threaded=True, use_reloader=False)


# If this is the main thread, simply start the server
if __name__ == "__main__":
    from thermal_sensor import MLX90640Sensor

    start_server(PiThermalCam(thermal_sensor=MLX90640Sensor()))
