from typing import Dict, Any
from .base import BaseDevice, DeviceResult


class CurtainDevice(BaseDevice):
    device_type = "curtain"
    capabilities = ["open", "close", "set_position", "stop"]

    def __init__(self, device_id: str, name: str, room: str = None):
        super().__init__(device_id, name, room)
        self.state = {
            "position": 100,
            "status": "stopped",
            "is_open": True
        }

    async def execute(self, command: str, params: Dict[str, Any]) -> DeviceResult:
        if not self.is_online:
            return DeviceResult(False, "设备离线")

        self._update_last_seen()

        try:
            if command == "open":
                self.state["position"] = 100
                self.state["status"] = "opened"
                self.state["is_open"] = True
                return DeviceResult(True, "窗帘已打开", self.state.copy())

            elif command == "close":
                self.state["position"] = 0
                self.state["status"] = "closed"
                self.state["is_open"] = False
                return DeviceResult(True, "窗帘已关闭", self.state.copy())

            elif command == "set_position":
                pos = max(0, min(100, int(params.get("value", 100))))
                self.state["position"] = pos
                self.state["status"] = "opened" if pos > 50 else "closed"
                self.state["is_open"] = pos > 0
                return DeviceResult(True, f"窗帘开合度设置为{pos}%", self.state.copy())

            elif command == "stop":
                self.state["status"] = "stopped"
                return DeviceResult(True, "窗帘已停止", self.state.copy())

            else:
                return DeviceResult(False, f"不支持的命令: {command}")

        except Exception as e:
            return DeviceResult(False, f"执行失败: {str(e)}")
