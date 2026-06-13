from typing import Dict, Any
from .base import BaseDevice, DeviceResult


class LightDevice(BaseDevice):
    device_type = "light"
    capabilities = ["turn_on", "turn_off", "set_brightness", "set_color", "toggle"]

    def __init__(self, device_id: str, name: str, room: str = None):
        super().__init__(device_id, name, room)
        self.state = {
            "power": "off",
            "brightness": 100,
            "color": "#ffffff",
            "color_temp": 4000
        }

    async def execute(self, command: str, params: Dict[str, Any]) -> DeviceResult:
        if not self.is_online:
            return DeviceResult(False, "设备离线")

        self._update_last_seen()

        try:
            if command == "turn_on":
                self.state["power"] = "on"
                if "brightness" in params:
                    self.state["brightness"] = max(0, min(100, int(params["brightness"])))
                if "color" in params:
                    self.state["color"] = params["color"]
                return DeviceResult(True, "开灯成功", self.state.copy())

            elif command == "turn_off":
                self.state["power"] = "off"
                return DeviceResult(True, "关灯成功", self.state.copy())

            elif command == "toggle":
                self.state["power"] = "off" if self.state["power"] == "on" else "on"
                return DeviceResult(True, "切换成功", self.state.copy())

            elif command == "set_brightness":
                brightness = max(0, min(100, int(params.get("value", 100))))
                self.state["brightness"] = brightness
                self.state["power"] = "on"
                return DeviceResult(True, f"亮度设置为{brightness}%", self.state.copy())

            elif command == "set_color":
                self.state["color"] = params.get("color", "#ffffff")
                self.state["power"] = "on"
                return DeviceResult(True, "颜色设置成功", self.state.copy())

            elif command == "set_color_temp":
                self.state["color_temp"] = max(2700, min(6500, int(params.get("value", 4000))))
                return DeviceResult(True, "色温设置成功", self.state.copy())

            else:
                return DeviceResult(False, f"不支持的命令: {command}")

        except Exception as e:
            return DeviceResult(False, f"执行失败: {str(e)}")
