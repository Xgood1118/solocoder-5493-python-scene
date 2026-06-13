from abc import ABC, abstractmethod
from typing import Dict, Any, List
from datetime import datetime


class DeviceResult:
    def __init__(self, success: bool, message: str = "", data: Dict[str, Any] = None):
        self.success = success
        self.message = message
        self.data = data or {}
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "timestamp": self.timestamp
        }


class BaseDevice(ABC):
    device_type: str = "base"
    capabilities: List[str] = []

    def __init__(self, device_id: str, name: str, room: str = None):
        self.id = device_id
        self.name = name
        self.room = room
        self.is_online = True
        self.state: Dict[str, Any] = {}
        self.last_seen = datetime.utcnow()

    @abstractmethod
    async def execute(self, command: str, params: Dict[str, Any]) -> DeviceResult:
        pass

    async def get_state(self) -> DeviceResult:
        self._update_last_seen()
        return DeviceResult(True, data=self.state.copy())

    async def set_online(self, online: bool) -> DeviceResult:
        self.is_online = online
        self._update_last_seen()
        return DeviceResult(True, data={"is_online": self.is_online})

    def _update_last_seen(self):
        self.last_seen = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "device_type": self.device_type,
            "room": self.room,
            "is_online": self.is_online,
            "state": self.state.copy(),
            "last_seen": self.last_seen.isoformat(),
            "capabilities": self.capabilities
        }
