from typing import Dict, Any
from datetime import datetime
from .base import BaseDevice, DeviceResult


class SensorDevice(BaseDevice):
    device_type = "sensor"
    capabilities = ["read_value", "calibrate"]

    def __init__(self, device_id: str, name: str, sensor_subtype: str = "temperature", room: str = None):
        super().__init__(device_id, name, room)
        self.sensor_subtype = sensor_subtype
        self.capabilities = [f"read_{sensor_subtype}", "calibrate"]
        self.state = self._init_state()

    def _init_state(self) -> Dict[str, Any]:
        base_state = {
            "sensor_type": self.sensor_subtype,
            "battery_level": 90,
            "last_reading_time": datetime.utcnow().isoformat(),
            "unit": ""
        }
        if self.sensor_subtype == "temperature":
            base_state.update({"value": 24.5, "unit": "°C", "min_value": 0, "max_value": 50})
        elif self.sensor_subtype == "humidity":
            base_state.update({"value": 55, "unit": "%", "min_value": 0, "max_value": 100})
        elif self.sensor_subtype == "motion":
            base_state.update({"value": False, "unit": "bool", "last_motion_time": None})
        elif self.sensor_subtype == "light":
            base_state.update({"value": 500, "unit": "lux", "min_value": 0, "max_value": 10000})
        elif self.sensor_subtype == "door":
            base_state.update({"value": "closed", "unit": "status"})
        return base_state

    async def execute(self, command: str, params: Dict[str, Any]) -> DeviceResult:
        if not self.is_online:
            return DeviceResult(False, "设备离线")

        self._update_last_seen()
        self.state["last_reading_time"] = self.last_seen.isoformat()

        try:
            if command == "read_value" or command == f"read_{self.sensor_subtype}":
                self._simulate_reading()
                return DeviceResult(True, "读取成功", self.state.copy())

            elif command == "calibrate":
                offset = float(params.get("offset", 0))
                if "value" in self.state and isinstance(self.state["value"], (int, float)):
                    self.state["value"] += offset
                return DeviceResult(True, f"校准完成，偏移量: {offset}", self.state.copy())

            elif command == "set_value":
                if "value" in params:
                    self.state["value"] = params["value"]
                    if self.sensor_subtype == "motion" and params["value"]:
                        self.state["last_motion_time"] = self.last_seen.isoformat()
                    return DeviceResult(True, "传感器值已设置", self.state.copy())

            else:
                return DeviceResult(False, f"不支持的命令: {command}")

        except Exception as e:
            return DeviceResult(False, f"执行失败: {str(e)}")

    def _simulate_reading(self):
        import random
        if self.sensor_subtype in ["temperature", "humidity", "light"]:
            base_val = self.state["value"]
            noise = random.uniform(-1, 1) * (base_val * 0.02)
            self.state["value"] = round(base_val + noise, 1)
        elif self.sensor_subtype == "motion":
            self.state["value"] = random.random() < 0.1
            if self.state["value"]:
                self.state["last_motion_time"] = self.last_seen.isoformat()
