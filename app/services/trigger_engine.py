import asyncio
from datetime import datetime
from typing import Dict, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from croniter import croniter

from app.database import async_session
from app.models.scene import Scene, Trigger
from app.services.execution import execution_engine


class TriggerEngine:
    def __init__(self):
        self._scheduler: Optional[AsyncIOScheduler] = None
        self._cron_jobs: Dict[int, str] = {}
        self._running = False

    async def start(self):
        if self._running:
            return
        self._scheduler = AsyncIOScheduler()
        self._scheduler.start()
        self._running = True
        await self._load_cron_triggers()

    async def stop(self):
        if self._scheduler and self._running:
            self._scheduler.shutdown(wait=False)
            self._running = False
            self._cron_jobs.clear()

    async def _load_cron_triggers(self):
        async with async_session() as db:
            from sqlalchemy import select

            result = await db.execute(
                select(Trigger).where(
                    Trigger.trigger_type == "cron", Trigger.enabled == True
                )
            )
            triggers = result.scalars().all()
            for trigger in triggers:
                await self.register_cron_trigger(trigger)

    async def register_cron_trigger(self, trigger: Trigger):
        if not self._scheduler or not self._running:
            return

        job_id = f"cron_trigger_{trigger.id}"

        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)

        expression = trigger.config.get("expression", "* * * * *")
        if not croniter.is_valid(expression):
            return

        self._scheduler.add_job(
            self._fire_cron_trigger,
            "cron",
            args=[trigger.id],
            id=job_id,
            replace_existing=True,
            **self._parse_cron(expression),
        )
        self._cron_jobs[trigger.id] = expression

    async def remove_cron_trigger(self, trigger_id: int):
        if not self._scheduler:
            return
        job_id = f"cron_trigger_{trigger_id}"
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)
        self._cron_jobs.pop(trigger_id, None)

    async def _fire_cron_trigger(self, trigger_id: int):
        async with async_session() as db:
            trigger = await db.get(Trigger, trigger_id)
            if not trigger or not trigger.enabled:
                return

            scene = await db.get(Scene, trigger.scene_id)
            if not scene or not scene.enabled:
                return

            trigger.last_evaluated_at = datetime.utcnow()
            trigger.last_evaluated_result = True
            await db.commit()

            await execution_engine.execute_scene(
                db,
                scene,
                trigger_id=trigger.id,
                trigger_type="cron",
                trigger_source=trigger.config.get("expression", ""),
            )

    async def evaluate_trigger(self, trigger: Trigger) -> bool:
        if not trigger.enabled:
            return False

        trigger_type = trigger.trigger_type
        config = trigger.config or {}

        if trigger_type == "manual":
            return True

        elif trigger_type == "device_state":
            return await self._eval_device_state(config)

        elif trigger_type == "sensor":
            return await self._eval_sensor(config)

        elif trigger_type == "geofence":
            return await self._eval_geofence(config)

        elif trigger_type == "cron":
            return await self._eval_cron(config)

        return False

    async def _eval_device_state(self, config: Dict) -> bool:
        from app.devices.manager import device_manager

        device_id = config.get("device_id")
        field = config.get("field")
        operator = config.get("operator", "eq")
        expected = config.get("value")

        if not device_id or not field:
            return False

        result = await device_manager.get_device_state(device_id)
        if not result.success:
            return False

        actual = result.data.get(field)
        return self._compare(actual, operator, expected)

    async def _eval_sensor(self, config: Dict) -> bool:
        from app.devices.manager import device_manager

        device_id = config.get("device_id")
        field = config.get("field", "value")
        operator = config.get("operator", "eq")
        expected = config.get("value")
        duration = config.get("duration", 0)

        if not device_id:
            return False

        result = await device_manager.execute_command(device_id, "read_value", {})
        if not result.success:
            return False

        actual = result.data.get(field)
        return self._compare(actual, operator, expected)

    async def _eval_geofence(self, config: Dict) -> bool:
        event = config.get("event", "enter")
        return False

    async def _eval_cron(self, config: Dict) -> bool:
        expression = config.get("expression", "")
        if not expression:
            return False
        now = datetime.utcnow()
        cron = croniter(expression, now)
        prev = cron.get_prev(datetime)
        return (now - prev).total_seconds() < 60

    @staticmethod
    def _compare(actual, operator: str, expected) -> bool:
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
        except (TypeError, ValueError):
            return False
        return False

    @staticmethod
    def _parse_cron(expression: str) -> Dict:
        parts = expression.split()
        if len(parts) != 5:
            return {}
        return {
            "minute": parts[0],
            "hour": parts[1],
            "day": parts[2],
            "month": parts[3],
            "day_of_week": parts[4],
        }


trigger_engine = TriggerEngine()
