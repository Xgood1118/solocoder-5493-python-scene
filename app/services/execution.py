import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.devices.manager import device_manager
from app.database import async_session
from app.models.scene import Scene, Trigger, Action, ExecutionLog
from app.services.conflict import ConflictDetector


class ExecutionEngine:
    def __init__(self):
        self._running_executions: Dict[str, asyncio.Task] = {}
        self.conflict_detector = ConflictDetector()

    async def execute_scene(
        self,
        db: AsyncSession,
        scene: Scene,
        trigger_id: int = None,
        trigger_type: str = "manual",
        trigger_source: str = "api",
        dry_run: bool = False,
    ) -> ExecutionLog:
        await self._cleanup_stale_running_logs()

        execution_id = str(uuid.uuid4())[:8]
        log = ExecutionLog(
            scene_id=scene.id,
            trigger_id=trigger_id,
            execution_id=execution_id,
            status="running",
            trigger_type=trigger_type,
            trigger_source=trigger_source,
            started_at=datetime.utcnow(),
            is_debug=scene.debug_mode or dry_run,
        )
        db.add(log)
        await db.commit()
        await db.refresh(log)

        interrupted_scene_id = await self._handle_priority_interrupt(scene)

        scene_id = scene.id
        log_id = log.id
        task = asyncio.create_task(
            self._run_actions(scene_id, log_id, dry_run, interrupted_scene_id)
        )
        self._running_executions[f"scene_{scene.id}_{execution_id}"] = task

        task.add_done_callback(
            lambda t: self._running_executions.pop(
                f"scene_{scene.id}_{execution_id}", None
            )
        )

        return log

    async def _cleanup_stale_running_logs(self):
        running_keys = set(self._running_executions.keys())
        async with async_session() as db:
            result = await db.execute(
                select(ExecutionLog).where(ExecutionLog.status == "running")
            )
            stale_logs = result.scalars().all()
            for log in stale_logs:
                key_prefix = f"scene_{log.scene_id}_"
                is_actually_running = any(k.startswith(key_prefix) for k in running_keys)
                if not is_actually_running:
                    log.status = "interrupted"
                    log.completed_at = datetime.utcnow()
                    log.interrupt_reason = "执行异常中断（进程重启或任务丢失）"
            await db.commit()

    async def _handle_priority_interrupt(
        self, scene: Scene
    ) -> Optional[int]:
        async with async_session() as check_db:
            conflict_result = await self.conflict_detector.check_priority_interrupt(check_db, scene)
        if not conflict_result or not conflict_result.interrupted_scene_id:
            return None

        interrupted_scene_id = conflict_result.interrupted_scene_id

        for eid, task in list(self._running_executions.items()):
            if eid.startswith(f"scene_{interrupted_scene_id}_"):
                task.cancel()
                self._running_executions.pop(eid, None)

        async with async_session() as int_db:
            result = await int_db.execute(
                select(ExecutionLog).where(
                    ExecutionLog.scene_id == interrupted_scene_id,
                    ExecutionLog.status == "running",
                )
            )
            running_logs = result.scalars().all()
            for rlog in running_logs:
                rlog.status = "interrupted"
                rlog.completed_at = datetime.utcnow()
                rlog.interrupted_by = scene.id
                rlog.interrupt_reason = f"被高优先级场景 [{scene.name}](priority={scene.priority}) 打断"

            int_log = ExecutionLog(
                scene_id=interrupted_scene_id,
                execution_id=str(uuid.uuid4())[:8],
                status="interrupted",
                trigger_type="priority_interrupt",
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                interrupted_by=scene.id,
                interrupt_reason=f"被高优先级场景 [{scene.name}](priority={scene.priority}) 打断",
            )
            int_db.add(int_log)
            await int_db.commit()

        return interrupted_scene_id

    async def _run_actions(
        self,
        scene_id: int,
        log_id: int,
        dry_run: bool,
        interrupted_scene_id: Optional[int] = None,
    ):
        async with async_session() as db:
            action_results: List[Dict[str, Any]] = []
            try:
                result = await db.execute(
                    select(Scene)
                    .options(
                        selectinload(Scene.actions).selectinload(Action.children),
                    )
                    .where(Scene.id == scene_id)
                )
                scene = result.scalar_one()
                log = await db.get(ExecutionLog, log_id)

                root_actions = sorted(
                    [a for a in scene.actions if a.parent_id is None],
                    key=lambda a: a.order_index,
                )

                for action in root_actions:
                    result = await self._execute_action(db, action, dry_run)
                    action_results.append(result)
                    if not result.get("success", True) and not dry_run:
                        if result.get("critical", False):
                            break

                scene.trigger_count = (scene.trigger_count or 0) + 1
                scene.last_triggered_at = datetime.utcnow()

                log.status = "completed"
                log.completed_at = datetime.utcnow()
                log.action_results = action_results

            except asyncio.CancelledError:
                try:
                    clog = await db.get(ExecutionLog, log_id)
                    if clog and clog.status == "running":
                        clog.status = "interrupted"
                        clog.completed_at = datetime.utcnow()
                        clog.interrupt_reason = "被高优先级场景打断"
                        clog.action_results = action_results
                        await db.commit()
                except Exception:
                    pass
                raise

            except Exception as e:
                try:
                    elog = await db.get(ExecutionLog, log_id)
                    if elog:
                        elog.status = "failed"
                        elog.completed_at = datetime.utcnow()
                        elog.error_message = str(e)[:500]
                        elog.action_results = action_results
                        await db.commit()
                except Exception:
                    pass

            else:
                await db.commit()

    async def _execute_action(
        self, db: AsyncSession, action: Action, dry_run: bool
    ) -> Dict[str, Any]:
        if action.action_type == "parallel":
            return await self._execute_parallel(db, action, dry_run)
        elif action.action_type == "condition":
            return await self._execute_condition(db, action, dry_run)
        elif action.action_type == "delay":
            return await self._execute_delay(action, dry_run)
        elif action.action_type == "device_command":
            return await self._execute_device_command(action, dry_run)
        elif action.action_type == "notify":
            return {
                "action_id": action.id,
                "action_type": "notify",
                "success": True,
                "message": f"通知: {action.name}",
                "dry_run": dry_run,
            }
        return {
            "action_id": action.id,
            "action_type": action.action_type,
            "success": False,
            "message": f"未知动作类型: {action.action_type}",
        }

    async def _execute_parallel(
        self, db: AsyncSession, action: Action, dry_run: bool
    ) -> Dict[str, Any]:
        children = sorted(action.children, key=lambda a: a.order_index)
        tasks = [self._execute_action(db, child, dry_run) for child in children]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        child_results = []
        all_success = True
        for r in results:
            if isinstance(r, Exception):
                child_results.append({"success": False, "message": str(r)})
                all_success = False
            else:
                child_results.append(r)
                if not r.get("success", True):
                    all_success = False
        return {
            "action_id": action.id,
            "action_type": "parallel",
            "success": all_success,
            "children": child_results,
            "dry_run": dry_run,
        }

    async def _execute_condition(
        self, db: AsyncSession, action: Action, dry_run: bool
    ) -> Dict[str, Any]:
        condition_met = await self._evaluate_condition(action.condition, dry_run)
        child_results = []
        if condition_met:
            children = sorted(action.children, key=lambda a: a.order_index)
            for child in children:
                result = await self._execute_action(db, child, dry_run)
                child_results.append(result)
        return {
            "action_id": action.id,
            "action_type": "condition",
            "condition_met": condition_met,
            "success": True,
            "children": child_results,
            "dry_run": dry_run,
        }

    async def _execute_delay(
        self, action: Action, dry_run: bool
    ) -> Dict[str, Any]:
        seconds = action.command.get("seconds", 1) if action.command else 1
        if not dry_run:
            await asyncio.sleep(seconds)
        return {
            "action_id": action.id,
            "action_type": "delay",
            "success": True,
            "delay_seconds": seconds,
            "dry_run": dry_run,
        }

    async def _execute_device_command(
        self, action: Action, dry_run: bool
    ) -> Dict[str, Any]:
        device_id = action.device_id
        command = action.command or {}

        if not device_id:
            return {
                "action_id": action.id,
                "success": False,
                "message": "未指定设备ID",
                "skipped": True,
            }

        device = device_manager.get_device(device_id)
        if not device:
            return {
                "action_id": action.id,
                "device_id": device_id,
                "action_type": "device_command",
                "success": False,
                "skipped": True,
                "message": f"设备 [{device_id}] 不存在，已跳过",
            }

        if not device.is_online:
            return {
                "action_id": action.id,
                "device_id": device_id,
                "action_type": "device_command",
                "success": False,
                "skipped": True,
                "message": f"设备 [{device_id}] 离线，已跳过",
            }

        if dry_run:
            return {
                "action_id": action.id,
                "device_id": device_id,
                "action_type": "device_command",
                "success": True,
                "dry_run": True,
                "command": command,
                "message": f"[调试] 将向设备 {device_id} 发送命令: {command.get('command', '')}",
            }

        result = await device_manager.execute_command(
            device_id, command.get("command", ""), command.get("params", {})
        )
        return {
            "action_id": action.id,
            "device_id": device_id,
            "action_type": "device_command",
            "success": result.success,
            "message": result.message,
            "data": result.data,
        }

    async def _evaluate_condition(
        self, condition: Optional[Dict[str, Any]], dry_run: bool
    ) -> bool:
        if not condition:
            return False

        device_id = condition.get("device_id")
        field = condition.get("field")
        operator = condition.get("operator", "eq")
        expected = condition.get("value")

        if dry_run:
            return True

        if device_id:
            result = await device_manager.get_device_state(device_id)
            if not result.success:
                return False
            actual = result.data.get(field)
            return self._compare(actual, operator, expected)

        return False

    @staticmethod
    def _compare(actual: Any, operator: str, expected: Any) -> bool:
        try:
            if operator == "eq":
                return actual == expected
            elif operator == "neq":
                return actual != expected
            elif operator == "gt":
                return float(actual) > float(expected)
            elif operator == "gte":
                return float(actual) >= float(expected)
            elif operator == "lt":
                return float(actual) < float(expected)
            elif operator == "lte":
                return float(actual) <= float(expected)
            elif operator == "in":
                return actual in expected
            elif operator == "contains":
                return expected in actual
        except (TypeError, ValueError):
            return False
        return False


execution_engine = ExecutionEngine()
