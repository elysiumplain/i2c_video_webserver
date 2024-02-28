import importlib
import inspect
from thermalcam.pi_thermal_cam import PiThermalCam
from thermalcam.thermal_sensor import ThermalSensor
from typing import List, Tuple, Type
import toml


def read_config():
    try:
        with open("config.toml", "r") as config_file:
            config = toml.load(config_file)
        return config
    except FileNotFoundError:
        print("Config file not found. Exiting.")
        exit()

def get_subclasses_of_base(module_name, base_class) -> List[Tuple[str, Type]]:
    module = importlib.import_module(module_name)
    classes = inspect.getmembers(module, inspect.isclass)
    sensor_classes = [cls for cls in classes if issubclass(cls[1], base_class) and cls[1] != base_class]
    return sensor_classes

if __name__ == "__main__":
    config = read_config()

    OUTPUT_FOLDER = config["scrots"]["output_folder"]
    CAMERA_LOG = config["camera"]["log"]
    WEBSERVER_LOG = config["webserver"]["log"]

    print(f"Compatible Sensors:")
    [print(f"\t{i}. {sensor}") for (i, sensor) in enumerate(get_subclasses_of_base("thermalcam.thermal_sensor", ThermalSensor), start=1)]

    sensor_choice = config["sensor"]
    module_name = sensor_choice["module_name"]
    class_name = sensor_choice["class_name"]
    print(f'Selected Sensor:\r\n\t{module_name=}\r\n\t{class_name=}')

    sensor_class = getattr(importlib.import_module(module_name), class_name)()

    #instantiate a thermalcam instance and stage the sensor using the selected ThermalSensor subclass
    thermalcam = PiThermalCam(thermal_sensor=sensor_class, output_folder=OUTPUT_FOLDER)

    operations = config["operations"]
    print(f"Selected Operations:")
    [print(f'\t{op}: {v}') for (op, v) in operations.items()]

    if operations["display_local"]:
        thermalcam.display_camera_onscreen()
    if operations["web_server"]:
        import thermalcam.web_server as server
        webserver_configs = config["webserver"]
        server.start_server(thermalcam, **webserver_configs)
