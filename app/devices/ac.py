from typing import Dict, Any
from .base import BaseDevice, DeviceResult


class ACDevice(BaseDevice):
    device_type = "ac"
    capabilities = ["turn_on", "turn_off", "set_temp", "set_mode", "set_fan_speed", "toggle"]

    def __init__(self, device_id: str, name: str, room: str = None):
        super().__init__(device_id, name, room)
        self.state = {
            "power": "off",
            "temperature": 26,
            "mode": "cool",
            "fan_speed": "auto",
            "swing": "off"
        }

    async def execute(self, command: str, params: Dict[str, Any]) -> DeviceResult:
        if not self.is_online:
            return DeviceResult(False, "设备离线")

        self._update_last_seen()

        try:
            if command == "turn_on":
                self.state["power"] = "on"
                if "temperature" in params:
                    self.state["temperature"] = max(16, min(30, int(params["temperature"])))
                if "mode" in params:
                    self.state["mode"] = params["mode"]
                return DeviceResult(True, "空调已开启", self.state.copy())

            elif command == "turn_off":
                self.state["power"] = "off"
                return DeviceResult(True, "空调已关闭", self.state.copy())

            elif command == "toggle":
                self.state["power"] = "off" if self.state["power"] == "on" else "on"
                return DeviceResult(True, "切换成功", self.state.copy())

            elif command == "set_temp":
                temp = max(16, min(30, int(params.get("value", 26))))
                self.state["temperature"] = temp
                self.state["power"] = "on"
                return DeviceResult(True, f"温度设置为{temp}°C", self.state.copy())

            elif command == "set_mode":
                mode = params.get("value", "cool")
                if mode in ["cool", "heat", "auto", "dry", "fan"]:
                    self.state["mode"] = mode
                    self.state["power"] = "on"
                    return DeviceResult(True, f"模式设置为{mode}", self.state.copy())
                return DeviceResult(False, f"不支持的模式: {mode}")

            elif command == "set_fan_speed":
                speed = params.get("value", "auto")
                if speed in ["low", "medium", "high", "auto"]:
                    self.state["fan_speed"] = speed
                    return DeviceResult(True, f"风速设置为{speed}", self.state.copy())
                return DeviceResult(False, f"不支持的风速: {speed}")

            else:
                return DeviceResult(False, f"不支持的命令: {command}")

        except Exception as e:
            return DeviceResult(False, f"执行失败: {str(e)}")
