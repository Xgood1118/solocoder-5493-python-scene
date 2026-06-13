from typing import Dict, Any
from .base import BaseDevice, DeviceResult


class LockDevice(BaseDevice):
    device_type = "lock"
    capabilities = ["lock", "unlock", "get_status"]

    def __init__(self, device_id: str, name: str, room: str = None):
        super().__init__(device_id, name, room)
        self.state = {
            "is_locked": True,
            "battery_level": 85,
            "last_unlock_by": "",
            "last_unlock_time": None,
            "auto_lock_timer": 300
        }

    async def execute(self, command: str, params: Dict[str, Any]) -> DeviceResult:
        if not self.is_online:
            return DeviceResult(False, "设备离线")

        self._update_last_seen()

        try:
            if command == "lock":
                self.state["is_locked"] = True
                return DeviceResult(True, "已上锁", self.state.copy())

            elif command == "unlock":
                self.state["is_locked"] = False
                self.state["last_unlock_by"] = params.get("user", "app")
                self.state["last_unlock_time"] = self.last_seen.isoformat()
                return DeviceResult(True, "已解锁", self.state.copy())

            elif command == "get_status":
                return DeviceResult(True, "获取状态成功", self.state.copy())

            elif command == "set_auto_lock":
                timer = max(0, int(params.get("seconds", 300)))
                self.state["auto_lock_timer"] = timer
                return DeviceResult(True, f"自动锁时间设置为{timer}秒", self.state.copy())

            else:
                return DeviceResult(False, f"不支持的命令: {command}")

        except Exception as e:
            return DeviceResult(False, f"执行失败: {str(e)}")
