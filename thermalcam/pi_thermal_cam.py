# -*- coding: utf-8 -*-
# !/usr/bin/python3
##################################
# MLX90640 Thermal Camera w Raspberry Pi
##################################
import board
import busio
import datetime as dt
import logging
import time
import traceback
from typing import Optional, Tuple, List, Union

import adafruit_mlx90640
import cmapy
import cv2
import numpy as np
from numpy import ndarray
from scipy import ndimage
import hashlib
from enum import Enum
from utils import common_utils

try:
    from thermalcam.thermal_sensor import ThermalSensor, MLX90640Sensor
except:
    from thermal_sensor import ThermalSensor, MLX90640Sensor


# Set up logging
logging.basicConfig(
    filename="thermal_cam.log",
    filemode="a",
    format="%(asctime)s %(levelname)-8s [%(filename)s:%(name)s:%(lineno)d] %(message)s",
    level=logging.WARNING,
    datefmt="%d-%b-%y %H:%M:%S",
)
logger = logging.getLogger(__name__)


def _print_shortcuts_keys():
    """Print out a summary of the shortcut keys available during video runtime."""
    print(f"The following keys are shortcuts for controlling the video during a run:\r\n \
Esc - Exit and Close\r\n \
S   - Save a Snapshot of the Current Frame\r\n \
X   - Cycle the Colormap Backwards\r\n \
C   - Cycle the Colormap forward\r\n \
F   - Toggle Filtering On/Off\r\n \
T   - Toggle Temperature Units between C/F\r\n \
U   - Go back to the previous Interpolation Algorithm\r\n \
I   - Change the Interpolation Algorithm Used\r\n \
Double-click with Mouse - Save a Snapshot of the Current Frame")


class Interpolation(Enum):
    INTER_NEAREST = (cv2.INTER_NEAREST, "Nearest")
    INTER_LINEAR = (cv2.INTER_LINEAR, "Inter Linear")
    INTER_AREA = (cv2.INTER_AREA, "Inter Area")
    INTER_CUBIC = (cv2.INTER_CUBIC, "Inter Cubic")
    INTER_LANCZOS4 = (cv2.INTER_LANCZOS4, "Inter Lanczos4")
    PURE_SCIPY = (5, "Pure Scipy")
    SCIPY_CV2_MIXED = (6, "Scipy/CV2 Mixed")
    
    def __new__(cls, value, name):
        obj = object.__new__(cls)
        obj._value_ = value
        obj._name_ = name
        obj.fname = name
        return obj
    
    def next(current):
        """Cycle interpolation forward"""
        dex = list(Interpolation)
        return dex[(current.value + 1) % len(dex)]
    
    def prev(current):
        """Cycle interpolation backwards"""
        dex = list(Interpolation)
        return dex[(current.value - 1) % len(dex)]

    @classmethod
    def to_dict(cls):
        return {entry.name: entry.value[0] for entry in cls}


class PiThermalCam:


    # See https://gitlab.com/cvejarano-oss/cmapy/-/blob/master/docs/colorize_all_examples.md to for options that can be put in this list
    _colormap_list: List[str] = [
        "jet",
        "bwr",
        "seismic",
        "coolwarm",
        "PiYG_r",
        "tab10",
        "tab20",
        "gnuplot2",
        "brg",
    ]
    _current_frame_processed: bool = (
        False  # Tracks if the current processed image matches the current raw image
    )
    #i2c: Optional[busio.I2C] = None
    #mlx: Optional[adafruit_mlx90640.MLX90640] = None
    _temp_min: Optional[float] = None
    _temp_max: Optional[float] = None
    _raw_image: Optional[np.ndarray] = None
    _image: Optional[np.ndarray] = None
    _file_saved_notification_start: Optional[float] = None
    _displaying_onscreen: bool = False
    _exit_requested: bool = False

    def __init__(
        self,
        thermal_sensor: ThermalSensor,
        use_f: bool = True,
        filter_image: bool = False,
        image_width: int = 1200,
        image_height: int = 900,
        output_folder: str = "/home/pi/Desktop/mlxFLIRCam/saved_snapshots/",
    ):
        self.thermal_sensor = thermal_sensor
        self.use_f: bool = use_f
        self.filter_image: bool = filter_image
        self.image_width: int = image_width
        self.image_height: int = image_height
        self.output_folder: str = output_folder

        self._colormap_index: int = 0
        self._interpolation: Interpolation = Interpolation.INTER_CUBIC
        self._setup_therm_cam()
        self._t0: float = time.time()
        self.update_image_frame()

    def __del__(self):
        logger.debug("ThermalCam Object deleted.")

    def _setup_therm_cam(self):
        """Initialize the thermal camera"""
        self.thermal_sensor.initialize()

    def get_mean_temp(self) -> Tuple[float, float]:
        """
        Get mean temp of entire field of view. Return both temp C and temp F.
        """
        frame = np.zeros((24 * 32,))  # setup array for storing all 768 temperatures
        while True:
            try:
                frame = self.thermal_sensor.get_raw_data()  # read MLX temperatures into frame var
                break
            except ValueError:
                continue  # if error, just read again

        temp_c = np.mean(frame)
        temp_f = common_utils.c_to_f(temp_c)
        return temp_c, temp_f

    def _pull_raw_image(self):
        """Get one pull of the raw image data"""
        self._raw_image = self.thermal_sensor.get_raw_data()
        self._set_minmax_image_temp(self._raw_image)
        self._raw_image = self._scale_image_temps(self._raw_image, self._temp_min, self._temp_max)
        logger.debug(f"img hash = {hashlib.sha256(str(self._raw_image).encode('utf-8')).hexdigest()}")

    def _set_minmax_image_temp(self, img):
        self._temp_min = np.min(img)
        self._temp_max = np.max(img)

    def _scale_image_temps(self, img, min, max):
        """Scale image temp units based on the thermal range within view, then flag frame as unprocessed."""
        try:
            img = common_utils.temps_to_rescaled_uints(
                img, min, max
            )
            self._current_frame_processed = (
                False  # Note that the newly updated raw frame has not been processed
            )
        except ValueError:
            print("Math error; continuing...")
            img = np.zeros(
                (24 * 32,)
            )  # If something went wrong, make sure the raw image has numbers
            logger.info(traceback.format_exc())
        except OSError:
            print("IO Error; continuing...")
            img = np.zeros(
                (24 * 32,)
            )  # If something went wrong, make sure the raw image has numbers
            logger.info(traceback.format_exc())
        return img

    def _process_raw_image(self):
        """Process the raw temp data to a colored image. Filter if necessary"""
        # Image processing
        # Can't apply colormap before ndimage, so reversed in first two options, even though it seems slower
        if (
            self._interpolation == Interpolation.PURE_SCIPY
        ):  # Scale via scipy only - slowest but seems higher quality
            self._image = ndimage.zoom(self._raw_image, 25)  # interpolate with scipy
            self._image = cv2.applyColorMap(
                self._image, cmapy.cmap(self._colormap_list[self._colormap_index])
            )
        elif (
            self._interpolation == Interpolation.SCIPY_CV2_MIXED
        ):  # Scale partially via scipy and partially via cv2 - mix of speed and quality
            self._image = ndimage.zoom(self._raw_image, 10)  # interpolate with scipy
            self._image = cv2.applyColorMap(
                self._image, cmapy.cmap(self._colormap_list[self._colormap_index])
            )
            self._image = cv2.resize(
                self._image, (800, 600), interpolation=cv2.INTER_CUBIC
            )
        else:
            self._image = cv2.applyColorMap(
                np.uint8(self._raw_image), cmapy.cmap(self._colormap_list[self._colormap_index])
            )
            self._image = cv2.resize(
                self._image,
                (800, 600),
                interpolation = self._interpolation.value,
            )
        self._image = cv2.flip(self._image, 1)
        if self.filter_image:
            self._image = cv2.bilateralFilter(self._image, 15, 80, 80)

    def _add_image_text(self):
        """Set image text content"""
        if self.use_f:
            temp_min = common_utils.c_to_f(self._temp_min)
            temp_max = common_utils.c_to_f(self._temp_max)
            text = f"Tmin={temp_min:+.1f}F - Tmax={temp_max:+.1f}F - FPS={1 / (time.time() - self._t0):.1f} - Interpolation: {self._interpolation.fname} - Colormap: {self._colormap_list[self._colormap_index]} - Filtered: {self.filter_image}"
        else:
            text = f"Tmin={self._temp_min:+.1f}C - Tmax={self._temp_max:+.1f}C - FPS={1 / (time.time() - self._t0):.1f} - Interpolation: {self._interpolation.fname} - Colormap: {self._colormap_list[self._colormap_index]} - Filtered: {self.filter_image}"
        self._set_image_text_background()
        cv2.putText(
            self._image,
            text,
            (30, 18),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (255, 255, 255),
            1,
        )
        self._t0 = time.time()  # Update time to this pull

        # For a brief period after saving, display saved notification
        if (
            self._file_saved_notification_start is not None
            and (time.monotonic() - self._file_saved_notification_start) < 1
        ):
            cv2.putText(
                self._image,
                "Snapshot Saved!",
                (300, 300),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2,
            )

    def _set_image_text_background(self):
        """Set image text background banner for readability"""
        # Draw a horizontal banner
        banner_height = 20
        cv2.rectangle(
            self._image, (0, 0), (self._image.shape[1], banner_height), (20, 20, 20), -1
        )  # -1 fills the rectangle

    def add_customized_text(self, text: str):
        """Add custom text to the center of the image, used mostly to notify user that server is off."""
        cv2.putText(
            self._image,
            text,
            (300, 300),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2,
        )
        time.sleep(0.1)

    def _show_processed_image(self):
        """Resize image window and display it"""
        cv2.namedWindow("Thermal Image", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Thermal Image", self.image_width, self.image_height)
        cv2.imshow("Thermal Image", self._image)

    def _set_click_keyboard_events(self):
        """Add click and keyboard actions to image"""
        # Set mouse click events
        cv2.setMouseCallback("Thermal Image", self._mouse_click)

        # Set keyboard events
        # if 's' is pressed - saving of picture
        key = cv2.waitKey(1) & 0xFF
        if key == ord("s"):  # If s is chosen, save an image to filec
            self.save_image()
        elif key == ord("c"):  # If c is chosen cycle the colormap used
            self.change_colormap()
        elif key == ord("x"):  # If c is chosen cycle the colormap used
            self.change_colormap(forward=False)
        elif key == ord("f"):  # If f is chosen cycle the image filtering
            self.filter_image = not self.filter_image
        elif key == ord("t"):  # If t is chosen cycle the units used for Temperature
            self.use_f = not self.use_f
        elif key == ord("u"):  # If t is chosen cycle the units used for temperature
            self._interpolation = Interpolation.next(self._interpolation)
        elif key == ord("i"):  # If i is chosen cycle interpolation algorithm
            self._interpolation = Interpolation.prev(self._interpolation)
        elif key == 27:  # Exit nicely if escape key is used
            cv2.destroyAllWindows()
            self._displaying_onscreen = False
            print("Code Stopped by User")
            self._exit_requested = True

    def _mouse_click(self, event: int, x: int, y: int, flags: int, param):
        """Used to save an image on double-click"""
        if event == cv2.EVENT_LBUTTONDBLCLK:
            self.save_image()

    def change_interpolation(self, previous=False):
        """Iterate through the interpolation options provided by the Interpolation Enum. A parameter of previous will call iterate backward through the list."""
        if previous:
            self._interpolation = Interpolation.prev(self._interpolation)
        else:
            self._interpolation = Interpolation.next(self._interpolation)


    def display_next_frame_onscreen(self):
        """Display the camera live to the display"""
        # Display shortcuts reminder to user on first run
        if not self._displaying_onscreen:
            _print_shortcuts_keys()
            self._displaying_onscreen = True
        self.update_image_frame()
        self._show_processed_image()
        self._set_click_keyboard_events()

    def change_colormap(self, forward: bool = True):
        """Cycle colormap. Forward by default, backwards if param set to false."""
        if forward:
            self._colormap_index += 1
            if self._colormap_index == len(self._colormap_list):
                self._colormap_index = 0
        else:
            self._colormap_index -= 1
            if self._colormap_index < 0:
                self._colormap_index = len(self._colormap_list) - 1

    def update_image_frame(self):
        """Pull raw temperature data, process it to an image, and update image text"""
        self._pull_raw_image()
        self._process_raw_image()
        self._add_image_text()
        self._current_frame_processed = True
        return self._image

    def update_raw_image_only(self):
        """Update only raw data without any further image processing or text updating"""
        self._pull_raw_image()

    def get_current_raw_image_frame(self) -> ndarray:
        """Return the current raw image"""
        self._pull_raw_image()
        return self._raw_image

    def get_current_image_frame(self) -> Union[ndarray, None]:
        """Get the processed image"""
        # If the current raw image hasn't been processed, process and return it
        if not self._current_frame_processed:
            self._process_raw_image()
            self._add_image_text()
            self._current_frame_processed = True
        return self._image

    def save_image(self):
        """Save the current frame as a snapshot to the output folder."""
        fname = (
            self.output_folder
            + "pic_"
            + dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            + ".jpg"
        )
        cv2.imwrite(fname, self._image)
        self._file_saved_notification_start = time.monotonic()
        print("Thermal Image ", fname)

    def display_camera_onscreen(self):
        # Loop to display frames unless/until user requests exit
        while not self._exit_requested:
            try:
                self.display_next_frame_onscreen()
            # Catch a common I2C Error. If you get this too often consider checking/adjusting your I2C Baudrate
            except RuntimeError as e:
                if "Too many retries" in str(e):
                    print(
                        "Too many retries error caught, potential I2C baudrate issue: continuing..."
                    )
                    continue
                raise


if __name__ == "__main__":
    # If class is run as main, read ini and set up a live feed displayed to screen
    OUTPUT_FOLDER = "/home/pi/Desktop/mlxFLIRCam/saved_snapshots/"

    thermcam = PiThermalCam(thermal_sensor=MLX90640Sensor(), output_folder=OUTPUT_FOLDER)  # Instantiate class
    thermcam.display_camera_onscreen()
