import json
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from app.database import get_db
from app.models.scene import Scene, Trigger, Action, ExecutionLog
from app.schemas.scene import (
    SceneCreate,
    SceneUpdate,
    SceneResponse,
    ExecutionLogResponse,
    SceneStats,
    ConflictCheckResult,
)
from app.services.execution import execution_engine
from app.services.conflict import conflict_detector
from app.services.stats import stats_service
from app.services.trigger_engine import trigger_engine

router = APIRouter(prefix="/scenes", tags=["场景管理"])


async def _load_scene(db: AsyncSession, scene_id: int) -> Scene:
    result = await db.execute(
        select(Scene)
        .options(
            selectinload(Scene.triggers),
            selectinload(Scene.actions).selectinload(Action.children),
        )
        .where(Scene.id == scene_id)
    )
    return result.scalar_one_or_none()


class SceneImport(BaseModel):
    data: str


class SceneExportResponse(BaseModel):
    scene: dict
    exported_at: str


@router.get("", response_model=List[SceneResponse])
async def list_scenes(
    enabled: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Scene).options(
        selectinload(Scene.triggers),
        selectinload(Scene.actions).selectinload(Action.children),
    )
    if enabled is not None:
        query = query.where(Scene.enabled == enabled)
    result = await db.execute(query.order_by(Scene.priority.desc()))
    scenes = result.scalars().unique().all()
    return scenes


@router.get("/stats", response_model=List[SceneStats])
async def get_all_stats(db: AsyncSession = Depends(get_db)):
    return await stats_service.get_all_stats(db)


@router.get("/stats/top", response_model=List[SceneStats])
async def get_top_scenes(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    return await stats_service.get_top_scenes(db, limit)


@router.post("", response_model=SceneResponse, status_code=201)
async def create_scene(
    scene_create: SceneCreate,
    db: AsyncSession = Depends(get_db),
):
    scene = Scene(
        name=scene_create.name,
        description=scene_create.description,
        icon=scene_create.icon,
        priority=scene_create.priority,
        enabled=scene_create.enabled,
        debug_mode=scene_create.debug_mode,
        mutually_exclusive_with=scene_create.mutually_exclusive_with,
    )
    db.add(scene)
    await db.flush()

    for trigger_data in scene_create.triggers:
        trigger = Trigger(
            scene_id=scene.id,
            trigger_type=trigger_data.trigger_type,
            name=trigger_data.name,
            enabled=trigger_data.enabled,
            config=trigger_data.config,
        )
        db.add(trigger)
        if trigger_data.trigger_type == "cron" and trigger_data.enabled:
            await trigger_engine.register_cron_trigger(trigger)

    await _save_actions(db, scene.id, scene_create.actions)
    await db.commit()
    scene = await _load_scene(db, scene.id)

    conflict = await conflict_detector.check_mutually_exclusive(db, scene)
    if conflict.has_conflict:
        raise HTTPException(status_code=409, detail=conflict.message)

    return scene


@router.get("/{scene_id}", response_model=SceneResponse)
async def get_scene(scene_id: int, db: AsyncSession = Depends(get_db)):
    scene = await _load_scene(db, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="场景不存在")
    return scene


@router.put("/{scene_id}", response_model=SceneResponse)
async def update_scene(
    scene_id: int,
    scene_update: SceneUpdate,
    db: AsyncSession = Depends(get_db),
):
    scene = await _load_scene(db, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="场景不存在")

    update_data = scene_update.model_dump(exclude_unset=True)

    if "mutually_exclusive_with" in update_data:
        scene.mutually_exclusive_with = update_data["mutually_exclusive_with"]
        conflict = await conflict_detector.check_mutually_exclusive(db, scene)
        if conflict.has_conflict:
            raise HTTPException(status_code=409, detail=conflict.message)

    for field in ["name", "description", "icon", "priority", "enabled", "debug_mode"]:
        if field in update_data:
            setattr(scene, field, update_data[field])

    scene.updated_at = datetime.utcnow()

    if "triggers" in update_data and update_data["triggers"] is not None:
        for t in scene.triggers:
            if t.trigger_type == "cron":
                await trigger_engine.remove_cron_trigger(t.id)
        for t in scene.triggers:
            await db.delete(t)
        await db.flush()

        for trigger_data in update_data["triggers"]:
            trigger = Trigger(
                scene_id=scene.id,
                trigger_type=trigger_data.trigger_type,
                name=trigger_data.name,
                enabled=trigger_data.enabled,
                config=trigger_data.config,
            )
            db.add(trigger)
            if trigger_data.trigger_type == "cron" and trigger_data.enabled:
                await trigger_engine.register_cron_trigger(trigger)

    if "actions" in update_data and update_data["actions"] is not None:
        for a in scene.actions:
            await db.delete(a)
        await db.flush()
        await _save_actions(db, scene.id, update_data["actions"])

    await db.commit()
    scene = await _load_scene(db, scene.id)
    return scene


@router.delete("/{scene_id}")
async def delete_scene(scene_id: int, db: AsyncSession = Depends(get_db)):
    scene = await _load_scene(db, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="场景不存在")

    for t in scene.triggers:
        if t.trigger_type == "cron":
            await trigger_engine.remove_cron_trigger(t.id)

    await db.delete(scene)
    await db.commit()
    return {"message": "场景已删除"}


@router.post("/{scene_id}/trigger", response_model=ExecutionLogResponse)
async def trigger_scene(
    scene_id: int,
    dry_run: bool = Query(False, description="调试模式，不实际执行设备命令"),
    db: AsyncSession = Depends(get_db),
):
    scene = await _load_scene(db, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="场景不存在")
    if not scene.enabled:
        raise HTTPException(status_code=400, detail="场景已禁用")

    log = await execution_engine.execute_scene(
        db, scene, trigger_type="manual", trigger_source="api", dry_run=dry_run
    )
    return log


@router.post("/{scene_id}/debug", response_model=ExecutionLogResponse)
async def debug_scene(scene_id: int, db: AsyncSession = Depends(get_db)):
    scene = await _load_scene(db, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="场景不存在")

    log = await execution_engine.execute_scene(
        db, scene, trigger_type="manual", trigger_source="debug", dry_run=True
    )
    return log


@router.get("/{scene_id}/conflict", response_model=ConflictCheckResult)
async def check_conflict(scene_id: int, db: AsyncSession = Depends(get_db)):
    scene = await _load_scene(db, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="场景不存在")

    exclusive = await conflict_detector.check_mutually_exclusive(db, scene)
    offline = await conflict_detector.check_offline_devices(scene)

    conflicts = []
    if exclusive.has_conflict:
        conflicts.append(exclusive)
    if offline.has_conflict:
        conflicts.append(offline)

    if not conflicts:
        return ConflictCheckResult(has_conflict=False, message="无冲突")

    primary = conflicts[0]
    return ConflictCheckResult(
        has_conflict=True,
        conflict_type=primary.conflict_type,
        conflicting_scenes=primary.conflicting_scene_ids or [],
        message="; ".join(c.message for c in conflicts if c.message),
    )


@router.get("/{scene_id}/stats", response_model=SceneStats)
async def get_scene_stats(scene_id: int, db: AsyncSession = Depends(get_db)):
    try:
        return await stats_service.get_scene_stats(db, scene_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{scene_id}/logs", response_model=List[ExecutionLogResponse])
async def get_execution_logs(
    scene_id: int,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    scene = await _load_scene(db, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="场景不存在")

    result = await db.execute(
        select(ExecutionLog)
        .where(ExecutionLog.scene_id == scene_id)
        .order_by(ExecutionLog.started_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.post("/{scene_id}/export")
async def export_scene(scene_id: int, db: AsyncSession = Depends(get_db)):
    scene = await _load_scene(db, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="场景不存在")

    export_data = _scene_to_dict(scene)
    return {
        "data": json.dumps(export_data, ensure_ascii=False, default=str),
        "exported_at": datetime.utcnow().isoformat(),
    }


@router.post("/import", response_model=SceneResponse, status_code=201)
async def import_scene(
    import_body: SceneImport,
    db: AsyncSession = Depends(get_db),
):
    try:
        data = json.loads(import_body.data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="无效的JSON数据")

    try:
        scene_create = SceneCreate(**data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"数据格式错误: {str(e)}")

    return await create_scene(scene_create, db)


async def _save_actions(db: AsyncSession, scene_id: int, actions: list, parent_id: int = None):
    for idx, action_data in enumerate(actions):
        children_data = None
        action_dict = action_data if isinstance(action_data, dict) else action_data.model_dump()

        if "children" in action_dict and action_dict["children"]:
            children_data = action_dict.pop("children")
        else:
            action_dict.pop("children", None)

        action = Action(
            scene_id=scene_id,
            parent_id=parent_id,
            action_type=action_dict.get("action_type", "device_command"),
            name=action_dict.get("name"),
            execution_mode=action_dict.get("execution_mode", "sequential"),
            order_index=action_dict.get("order_index", idx),
            device_id=action_dict.get("device_id"),
            command=action_dict.get("command", {}),
            condition=action_dict.get("condition"),
            timeout=action_dict.get("timeout", 30),
            retry_count=action_dict.get("retry_count", 1),
        )
        db.add(action)
        await db.flush()

        if children_data:
            await _save_actions(db, scene_id, children_data, action.id)


def _scene_to_dict(scene: Scene) -> dict:
    return {
        "name": scene.name,
        "description": scene.description,
        "icon": scene.icon,
        "priority": scene.priority,
        "enabled": scene.enabled,
        "debug_mode": scene.debug_mode,
        "mutually_exclusive_with": scene.mutually_exclusive_with or [],
        "triggers": [
            {
                "trigger_type": t.trigger_type,
                "name": t.name,
                "enabled": t.enabled,
                "config": t.config or {},
            }
            for t in scene.triggers
        ],
        "actions": _actions_to_list([a for a in scene.actions if a.parent_id is None]),
    }


def _actions_to_list(actions: list) -> list:
    result = []
    for a in sorted(actions, key=lambda x: x.order_index):
        action_dict = {
            "action_type": a.action_type,
            "name": a.name,
            "execution_mode": a.execution_mode,
            "order_index": a.order_index,
            "device_id": a.device_id,
            "command": a.command or {},
            "condition": a.condition,
            "timeout": a.timeout,
            "retry_count": a.retry_count,
        }
        if hasattr(a, "children") and a.children:
            action_dict["children"] = _actions_to_list(a.children)
        result.append(action_dict)
    return result
