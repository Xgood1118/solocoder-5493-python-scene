from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.scene import Scene, ExecutionLog
from app.devices.manager import device_manager


@dataclass
class ConflictResult:
    has_conflict: bool
    conflict_type: Optional[str] = None
    message: Optional[str] = None
    conflicting_scene_ids: Optional[List[int]] = None
    interrupted_scene_id: Optional[int] = None


class ConflictDetector:
    async def check_mutually_exclusive(
        self, db: AsyncSession, scene: Scene
    ) -> ConflictResult:
        if not scene.mutually_exclusive_with:
            return ConflictResult(has_conflict=False)

        conflicting = []
        for ex_id in scene.mutually_exclusive_with:
            other = await db.get(Scene, ex_id)
            if other and other.enabled:
                if scene.id in (other.mutually_exclusive_with or []):
                    conflicting.append(ex_id)

        if conflicting:
            return ConflictResult(
                has_conflict=True,
                conflict_type="mutually_exclusive",
                conflicting_scene_ids=conflicting,
                message=f"场景与以下场景互斥，无法保存: {conflicting}",
            )
        return ConflictResult(has_conflict=False)

    async def check_priority_interrupt(
        self, db: AsyncSession, scene: Scene
    ) -> Optional[ConflictResult]:
        running_logs = await db.execute(
            select(ExecutionLog).where(
                ExecutionLog.status == "running",
                ExecutionLog.scene_id != scene.id,
            )
        )
        running = running_logs.scalars().all()

        for log in running:
            other_scene = await db.get(Scene, log.scene_id)
            if other_scene and other_scene.priority < scene.priority:
                return ConflictResult(
                    has_conflict=True,
                    conflict_type="priority_interrupt",
                    interrupted_scene_id=other_scene.id,
                    message=f"高优先级场景 [{scene.name}](priority={scene.priority}) 打断低优先级 [{other_scene.name}](priority={other_scene.priority})",
                )
        return None

    async def check_offline_devices(
        self, scene: Scene,
    ) -> ConflictResult:
        offline_devices = []
        self._collect_device_ids(scene, offline_devices)

        offline = []
        for device_id in offline_devices:
            if not device_manager.is_device_online(device_id):
                offline.append(device_id)

        if offline:
            return ConflictResult(
                has_conflict=True,
                conflict_type="offline_devices",
                message=f"以下设备离线，执行时将跳过: {offline}",
                conflicting_scene_ids=offline,
            )
        return ConflictResult(has_conflict=False)

    def _collect_device_ids(self, scene: Scene, device_ids: list):
        if not hasattr(scene, "actions") or not scene.actions:
            return
        for action in scene.actions:
            if action.device_id:
                device_ids.append(action.device_id)
            if hasattr(action, "children") and action.children:
                for child in action.children:
                    if child.device_id:
                        device_ids.append(child.device_id)

    async def validate_scene_save(
        self, db: AsyncSession, scene: Scene
    ) -> ConflictResult:
        exclusive_result = await self.check_mutually_exclusive(db, scene)
        if exclusive_result.has_conflict:
            return exclusive_result

        return ConflictResult(has_conflict=False)


conflict_detector = ConflictDetector()
