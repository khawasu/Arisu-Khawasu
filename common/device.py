from __future__ import annotations

import json

from khawasu_stuff.action import ActionType
from khawasu_stuff.device import DeviceType
import khawasu_stuff
from common.khawasu import driver

_devices = []
_yandex_device_param_map = None
_yandex_device_type_map = None


def get_yandex_device_param_map() -> dict:
    global _yandex_device_param_map
    if _yandex_device_param_map is None:
        with open("assets/yandex_device_param_map.json", "r", encoding="utf-8") as file:
            _yandex_device_param_map = json.loads(file.read())

    return _yandex_device_param_map


def get_yandex_device_type_map() -> dict:
    global _yandex_device_type_map
    if _yandex_device_type_map is None:
        with open("assets/yandex_device_type_map.json", "r", encoding="utf-8") as file:
            _yandex_device_type_map = json.loads(file.read())

    return _yandex_device_type_map


class Device:
    DEFAULT_MANUFACTURER = "Khawasu chan"
    DEFAULT_MODEL = 0
    DEFAULT_HARDWARE_VERSION = 1.0
    DEFAULT_SOFTWARE_VERSION = 1.0

    IGNORE_TYPES = [ActionType.UNKNOWN, ActionType.IMMEDIATE, ActionType.LABEL]

    def __init__(self, _id: str, name: str, description: str, room: str, type: str, capabilities=None, properties=None,
                 device_info=None):
        if capabilities is None:
            capabilities = []
        if properties is None:
            properties = []

        if device_info is None:
            device_info = {
                "manufacturer": self.DEFAULT_MANUFACTURER,
                "model": str(self.DEFAULT_MODEL),
                "hw_version": str(self.DEFAULT_HARDWARE_VERSION),
                "sw_version": str(self.DEFAULT_SOFTWARE_VERSION)
            }

        self.id = _id
        self.name = name
        self.description = description
        self.room = room
        self.type = type
        self.capabilities = capabilities
        self.properties = properties
        self.device_info = device_info

    def get_row_object(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "room": self.room if len(self.room) > 0 else "Неизвестная комната",
            "type": self.type,
            "capabilities": self.capabilities,
            "properties": self.properties,
            "device_info": self.device_info,
        }

    def query(self) -> dict:
        khawasu_device = khawasu_stuff.device.Device.get_by_address(driver(), self.id)
        result = {'id': self.id, 'capabilities': [], 'properties': []}

        if khawasu_device is None:
            return []

        for cap in self.capabilities:
            if not cap.get("retrievable", True):
                continue

            current_state = khawasu_device.get(cap["__khawasu_action"])

            result['capabilities'].append({
                'type': cap["type"],
                'state': {
                    "instance": cap["parameters"]["instance"],
                    "value": current_state
                }
            })

        for prop in self.properties:
            if not prop.get("retrievable", True):
                continue

            current_state = khawasu_device.get(prop["__khawasu_action"])

            result['properties'].append({
                'type': prop["type"],
                'state': {
                    "instance": prop["parameters"]["instance"],
                    "value": current_state
                }
            })

        return result

    def get_most_similar_cap_action(self, cap_row) -> str | None:
        for cap in self.capabilities:
            if cap["type"] == cap_row["type"]:
                return cap["__khawasu_action"]

        return None

    def action(self, capabilities):
        khawasu_device = khawasu_stuff.device.Device.get_by_address(driver(), self.id)
        result = {'id': self.id, 'capabilities': []}

        if khawasu_device is None:
            return []

        for cap in capabilities:
            new_value = cap["state"]["value"]
            similar_action = self.get_most_similar_cap_action(cap)

            if similar_action is None:
                continue

            khawasu_device.execute(similar_action, new_value)

            result['capabilities'].append({
                'type': cap["type"],
                'state': {
                    "instance": cap["state"]["instance"],
                    "action_result": {
                        "status": "DONE",
                        "error_code": "",  # todo implement error handling
                        "error_message": ""
                    }
                }
            })

        return result

    @classmethod
    def get_capability(cls, khawasu_action: khawasu_stuff.action.Action):
        cap = {
            "type": get_yandex_device_type_map()[khawasu_action.type.name]["type"],
            "parameters": {},
            "retrievable": True,
            "reportable": False,
            "__khawasu_action": khawasu_action.name
        }

        cap["parameters"] = cap["parameters"] | get_yandex_device_type_map()[khawasu_action.type.name]["parameters"]

        if khawasu_action.type == ActionType.RANGE:
            cap["parameters"]["instance"] = "brightness"
            cap["parameters"]["unit"] = "unit.percent"
            cap["parameters"]["range"] = {
                "min": 0,
                "max": 100
            }
        if khawasu_action.type == ActionType.TEMPERATURE:
            cap["parameters"]["instance"] = "temperature"
            cap["parameters"]["unit"] = "unit.temperature.celsius"

        if khawasu_action.type == ActionType.HUMIDITY:
            cap["parameters"]["instance"] = "humidity"
            cap["parameters"]["unit"] = "unit.percent"

        return cap

    @classmethod
    def is_capability(cls, khawasu_action):
        return khawasu_action.type not in cls.IGNORE_TYPES and \
               get_yandex_device_type_map()[khawasu_action.type.name]["type"].find(
                   "properties") == -1  # todo: replace find to beautiful way

    @classmethod
    def is_property(cls, khawasu_action):
        return khawasu_action.type not in cls.IGNORE_TYPES and \
               get_yandex_device_type_map()[khawasu_action.type.name]["type"].find("properties") != -1

    @classmethod
    def from_khawasu_device(cls, khawasu_device: khawasu_stuff.device.Device):
        return cls(khawasu_device.address,
                   khawasu_device.name,
                   get_yandex_device_param_map()[khawasu_device.type.name]["desc"],
                   khawasu_device.group,
                   get_yandex_device_param_map()[khawasu_device.type.name]["type"],
                   [cls.get_capability(action) for action in khawasu_device.actions if
                    cls.is_capability(action)],
                   [cls.get_capability(action) for action in khawasu_device.actions if
                    cls.is_property(action)])

    @classmethod
    def get_by_id(cls, id: str) -> Device | None:
        global _devices

        if len(_devices) == 0:
            cls.get_all()

        for dev in _devices:
            if dev.id == id:
                return dev

        return None

    @classmethod
    def get_all(cls) -> list[Device]:
        global _devices
        _devices = [cls.from_khawasu_device(device) for device in khawasu_stuff.device.Device.get_all(driver())]

        return _devices
