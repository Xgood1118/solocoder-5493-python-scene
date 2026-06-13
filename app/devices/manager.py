from typing import Dict, List, Optional, Any
from datetime import datetime
from .base import BaseDevice, DeviceResult
from .light import LightDevice
from .ac import ACDevice
from .curtain import CurtainDevice
from .music import MusicDevice
from .lock import LockDevice
from .sensor import SensorDevice


class DeviceManager:
    def __init__(self):
        self._devices: Dict[str, BaseDevice] = {}
        self._init_mock_devices()

    def _init_mock_devices(self):
        mock_devices = [
            LightDevice("light_living_1", "客厅主灯", "客厅"),
            LightDevice("light_living_2", "客厅氛围灯", "客厅"),
            LightDevice("light_bedroom_1", "卧室主灯", "卧室"),
            LightDevice("light_kitchen_1", "厨房灯", "厨房"),
            LightDevice("light_bathroom_1", "卫生间灯", "卫生间"),
            ACDevice("ac_living_1", "客厅空调", "客厅"),
            ACDevice("ac_bedroom_1", "卧室空调", "卧室"),
            CurtainDevice("curtain_living_1", "客厅窗帘", "客厅"),
            CurtainDevice("curtain_bedroom_1", "卧室窗帘", "卧室"),
            MusicDevice("music_living_1", "客厅音响", "客厅"),
            MusicDevice("music_bedroom_1", "卧室音响", "卧室"),
            LockDevice("lock_front_door", "前门智能锁", "入户"),
            SensorDevice("sensor_temp_living", "客厅温度传感器", "temperature", "客厅"),
            SensorDevice("sensor_humidity_living", "客厅湿度传感器", "humidity", "客厅"),
            SensorDevice("sensor_motion_living", "客厅人体传感器", "motion", "客厅"),
            SensorDevice("sensor_motion_bedroom", "卧室人体传感器", "motion", "卧室"),
            SensorDevice("sensor_light_living", "客厅光照传感器", "light", "客厅"),
            SensorDevice("sensor_door_front", "前门磁传感器", "door", "入户"),
        ]
        for device in mock_devices:
            self._devices[device.id] = device

    def get_device(self, device_id: str) -> Optional[BaseDevice]:
        return self._devices.get(device_id)

    def get_all_devices(self) -> List[BaseDevice]:
        return list(self._devices.values())

    def get_devices_by_type(self, device_type: str) -> List[BaseDevice]:
        return [d for d in self._devices.values() if d.device_type == device_type]

    def get_devices_by_room(self, room: str) -> List[BaseDevice]:
        return [d for d in self._devices.values() if d.room == room]

    async def execute_command(self, device_id: str, command: str, params: Dict[str, Any] = None) -> DeviceResult:
        device = self.get_device(device_id)
        if not device:
            return DeviceResult(False, f"设备不存在: {device_id}")
        return await device.execute(command, params or {})

    async def get_device_state(self, device_id: str) -> DeviceResult:
        device = self.get_device(device_id)
        if not device:
            return DeviceResult(False, f"设备不存在: {device_id}")
        return await device.get_state()

    async def set_device_online(self, device_id: str, online: bool) -> DeviceResult:
        device = self.get_device(device_id)
        if not device:
            return DeviceResult(False, f"设备不存在: {device_id}")
        return await device.set_online(online)

    def is_device_online(self, device_id: str) -> bool:
        device = self.get_device(device_id)
        return device.is_online if device else False

    def sync_to_db_devices(self):
        return [
            {
                "id": d.id,
                "name": d.name,
                "device_type": d.device_type,
                "room": d.room,
                "is_online": d.is_online,
                "state": d.state.copy(),
                "last_seen": d.last_seen,
                "capabilities": d.capabilities
            }
            for d in self._devices.values()
        ]


device_manager = DeviceManager()
