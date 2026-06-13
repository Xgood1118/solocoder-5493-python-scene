from typing import Dict, Any
from .base import BaseDevice, DeviceResult


class MusicDevice(BaseDevice):
    device_type = "music"
    capabilities = ["play", "pause", "stop", "next", "prev", "set_volume", "set_playlist"]

    def __init__(self, device_id: str, name: str, room: str = None):
        super().__init__(device_id, name, room)
        self.state = {
            "status": "stopped",
            "volume": 50,
            "current_track": "",
            "playlist": "default",
            "is_muted": False
        }

    async def execute(self, command: str, params: Dict[str, Any]) -> DeviceResult:
        if not self.is_online:
            return DeviceResult(False, "设备离线")

        self._update_last_seen()

        try:
            if command == "play":
                self.state["status"] = "playing"
                if "track" in params:
                    self.state["current_track"] = params["track"]
                if "playlist" in params:
                    self.state["playlist"] = params["playlist"]
                return DeviceResult(True, "开始播放", self.state.copy())

            elif command == "pause":
                self.state["status"] = "paused"
                return DeviceResult(True, "已暂停", self.state.copy())

            elif command == "stop":
                self.state["status"] = "stopped"
                self.state["current_track"] = ""
                return DeviceResult(True, "已停止", self.state.copy())

            elif command == "next":
                self.state["current_track"] = f"track_{abs(hash('next')) % 100}"
                self.state["status"] = "playing"
                return DeviceResult(True, "下一首", self.state.copy())

            elif command == "prev":
                self.state["current_track"] = f"track_{abs(hash('prev')) % 100}"
                self.state["status"] = "playing"
                return DeviceResult(True, "上一首", self.state.copy())

            elif command == "set_volume":
                vol = max(0, min(100, int(params.get("value", 50))))
                self.state["volume"] = vol
                self.state["is_muted"] = vol == 0
                return DeviceResult(True, f"音量设置为{vol}%", self.state.copy())

            elif command == "set_playlist":
                self.state["playlist"] = params.get("name", "default")
                return DeviceResult(True, f"已切换到播放列表: {self.state['playlist']}", self.state.copy())

            else:
                return DeviceResult(False, f"不支持的命令: {command}")

        except Exception as e:
            return DeviceResult(False, f"执行失败: {str(e)}")
