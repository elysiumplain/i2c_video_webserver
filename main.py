import importlib
import inspect
from thermalcam.pi_thermal_cam import PiThermalCam
from thermalcam.thermal_sensor import ThermalSensor
from typing import List, Tuple, Type


def get_subclasses_of_base(module_name, base_class) -> List[Tuple[str, Type]]:
    module = importlib.import_module(module_name)
    classes = inspect.getmembers(module, inspect.isclass)
    sensor_classes = [cls for cls in classes if issubclass(cls[1], base_class) and cls[1] != base_class]
    return sensor_classes

if __name__ == "__main__":
    OUTPUT_FOLDER = "/home/pi/Desktop/mlxFLIRCam/saved_snapshots/"
    
    sensor_classes = get_subclasses_of_base("thermalcam.thermal_sensor", ThermalSensor)
    print(f"Which Sensor are you using?")
    [print(f"\t{i + 1}. {sensor}") for (i, sensor) in enumerate(sensor_classes)]
    sensor_choice = int(input("number: "))

    if 1 <= sensor_choice <= len(sensor_classes):
        sensor_class = sensor_classes[sensor_choice - 1][1]()
    else:
        print("Invalid sensor choice. Exiting.")
        exit()

    #instantiate a thermalcam instance and stage the sensor using the selected ThermalSensor subclass
    thermalcam = PiThermalCam(thermal_sensor=sensor_class, output_folder=OUTPUT_FOLDER)

    usage=["display_camera_onscreen","start_webserver","display_camera_onscreen and start_webserver"]
    print(f"What would you like to do?")
    [print(f"\t{i + 1}. {use}") for (i, use) in enumerate(usage)]
    operation_choice = int(input("number: "))

    if operation_choice == 1:
        thermalcam.display_camera_onscreen()
    elif operation_choice == 2:
        import thermalcam.web_server as server
        publish = input("Allow public access? (y/n): ") == "y"
        server.start_server(thermalcam, publish=publish)
    elif operation_choice == 3:
        import thermalcam.web_server
        thermalcam.display_camera_onscreen()
        server.start_server(thermalcam)
    else:
        print("Invalid operation choice. Exiting.")
        exit()
