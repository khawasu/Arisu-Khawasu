from __future__ import annotations
from enum import Enum
from typing import Any

import driver_khawasu.driver

from khawasu_stuff.action import Action, ActionType


class DeviceType(Enum):
    UNKNOWN = 0
    BUTTON = 1
    RELAY = 2
    TEMPERATURE_SENSOR = 3
    TEMP_HUM_SENSOR = 4
    CONTROLLER = 5
    PC2LOGICAL_ADAPTER = 6
    LUA_INTERPRETER = 7
    LED_1_DIM = 8


_khawasu_devices_cache = None


class Device:
    def __init__(self, row, khawasu_inst: driver_khawasu.driver.LogicalDriver):
        self.actions = [Action(name, type) for name, type in row["actions"].items()]
        self.address = row["address"]
        self.attribs = row["attribs"]
        self.dev_class = row["dev_class"]
        self.type = DeviceType(int(self.dev_class))
        self.group = row["group_name"]
        self.name = row["name"]
        self.khawasu_inst = khawasu_inst

    def execute(self, action_name: str, data: Any) -> bool:
        for action in self.actions:
            if action.name != action_name:
                continue

            # cast from [0, 100] to [0, 1] for yandex
            if action.type == ActionType.RANGE:
                data /= 100

            self.khawasu_inst.execute(self.address, action_name, action.format_args_to_bytes(data))
            return True

        return False

    def get(self, action_name: str) -> Any:
        for action in self.actions:
            if action.name != action_name:
                continue
            data = self.khawasu_inst.action_get(self.address, action_name)

            if "status" in data:
                print("Error in action fetch: ", data["status"])
                return None

            result = action.format_bytes_to_data(data["data"])

            # cast from [0, 1] to [0, 100] for yandex
            if action.type == ActionType.RANGE:
                result *= 100

            return result

        return None

    """ 
        period - for regularly updated devices: how often updated info will be sent. (in milliseconds)
        duration - subscription time (in seconds)
    """

    def subscribe(self, action_name: str, period: int, duration: int, handler) -> Any:
        for action in self.actions:
            if action != action_name:
                continue

            self.khawasu_inst.subscribe(self.address, action_name, period, duration, handler)

            return False

        return True

    @classmethod
    def get_by_address(cls, khawasu_inst: driver_khawasu.driver.LogicalDriver, address: str) -> Device | None:
        global _khawasu_devices_cache

        # Trigger for update
        if _khawasu_devices_cache is None:
            cls.get_all(khawasu_inst)

        for dev in _khawasu_devices_cache:
            if dev.address == address:
                return dev

        return None

    @classmethod
    def get_all(cls, khawasu_inst: driver_khawasu.driver.LogicalDriver) -> list[Device]:
        global _khawasu_devices_cache
        _khawasu_devices_cache = [cls(dev, khawasu_inst) for dev in khawasu_inst.get("list-devices")]

        return _khawasu_devices_cache
