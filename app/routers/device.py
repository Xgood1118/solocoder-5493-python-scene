from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.devices.manager import device_manager
from app.schemas.scene import DeviceResponse, DeviceCommand

router = APIRouter(prefix="/devices", tags=["设备管理"])


@router.get("", response_model=List[DeviceResponse])
async def list_devices(
    device_type: Optional[str] = None,
    room: Optional[str] = None,
    online: Optional[bool] = None,
):
    devices = device_manager.get_all_devices()
    if device_type:
        devices = [d for d in devices if d.device_type == device_type]
    if room:
        devices = [d for d in devices if d.room == room]
    if online is not None:
        devices = [d for d in devices if d.is_online == online]
    return [d.to_dict() for d in devices]


@router.get("/{device_id}")
async def get_device(device_id: str):
    device = device_manager.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail=f"设备不存在: {device_id}")
    return device.to_dict()


@router.get("/{device_id}/state")
async def get_device_state(device_id: str):
    result = await device_manager.get_device_state(device_id)
    if not result.success:
        raise HTTPException(status_code=404, detail=result.message)
    return result.to_dict()


@router.post("/{device_id}/command")
async def execute_device_command(device_id: str, cmd: DeviceCommand):
    if not device_manager.is_device_online(device_id):
        device = device_manager.get_device(device_id)
        if not device:
            raise HTTPException(status_code=404, detail=f"设备不存在: {device_id}")
        raise HTTPException(status_code=503, detail=f"设备 [{device_id}] 离线，无法执行命令")

    result = await device_manager.execute_command(device_id, cmd.command, cmd.params)
    return result.to_dict()


class OnlineToggle(BaseModel):
    online: bool


@router.post("/{device_id}/online")
async def toggle_device_online(device_id: str, body: OnlineToggle):
    result = await device_manager.set_device_online(device_id, body.online)
    if not result.success:
        raise HTTPException(status_code=404, detail=result.message)
    return result.to_dict()


@router.get("/rooms/list")
async def list_rooms():
    devices = device_manager.get_all_devices()
    rooms = sorted(set(d.room for d in devices if d.room))
    return {"rooms": rooms}


@router.get("/types/list")
async def list_device_types():
    devices = device_manager.get_all_devices()
    types = sorted(set(d.device_type for d in devices))
    return {"device_types": types}
