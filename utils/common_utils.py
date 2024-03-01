import numpy as np
from numpy import ndarray
from typing import List, Union


def temps_to_rescaled_uints(
    img_arr: Union[List[float], np.ndarray], temp_min: float, temp_max: float
) -> np.uint8:
    """Function to convert temperatures to pixels on image"""
    img_arr = np.nan_to_num(img_arr)
    norm = np.uint8((img_arr - temp_min) * 255 / (temp_max - temp_min))
    norm.shape = (24, 32)
    return norm


def c_to_f(temp: float) -> float:
    """Convert temperature from C to F"""
    return (9.0 / 5.0) * temp + 32.0
