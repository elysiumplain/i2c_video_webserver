from abc import ABC, abstractmethod

import numpy as np
from adafruit_mlx90640 import MLX90640, RefreshRate
import busio
import board
import time
import warnings
import logging


class ThermalSensor(ABC):
    @abstractmethod
    def initialize(self):
        pass

    @abstractmethod
    def get_raw_data(self):
        pass


class MLX90640Sensor(ThermalSensor):
    def __init__(self):
        self.i2c = None
        self.mlx = None

    def initialize(self):
        """Initialize the MLX90640 thermal sensor."""
        logging.info(f"initializing {self.__class__} sensor")
        try:
            warnings.filterwarnings("ignore")
            self.i2c = busio.I2C(board.SCL, board.SDA, frequency=800000)
            self.mlx = MLX90640(self.i2c)
            self.mlx.refresh_rate = RefreshRate.REFRESH_8_HZ
            time.sleep(0.1)
        except IOError as e:
            logging.error(f"Error initializing MLX90640 sensor: {e}")
            raise
        except Exception as e:
            logging.error(f"Error initializing MLX90640 sensor: {e}")
            raise

    def get_raw_data(self):
        """Get one pull of the raw image data."""
        try:
            raw_image = np.zeros((24 * 32,))
            self.mlx.getFrame(raw_image)
            return raw_image
        except Exception as e:
            logging.error(f"Error getting raw data from MLX90640 sensor: {e}")
            raise
