from datetime import datetime, timedelta
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.scene import Scene, ExecutionLog
from app.schemas.scene import SceneStats


class StatsService:
    async def get_scene_stats(
        self, db: AsyncSession, scene_id: int
    ) -> SceneStats:
        scene = await db.get(Scene, scene_id)
        if not scene:
            raise ValueError(f"场景不存在: {scene_id}")

        total = await db.execute(
            select(func.count(ExecutionLog.id)).where(
                ExecutionLog.scene_id == scene_id
            )
        )
        total_count = total.scalar() or 0

        success = await db.execute(
            select(func.count(ExecutionLog.id)).where(
                ExecutionLog.scene_id == scene_id,
                ExecutionLog.status == "completed",
            )
        )
        success_count = success.scalar() or 0

        success_rate = round(success_count / total_count * 100, 1) if total_count > 0 else 0.0

        avg_time = 0.0
        if total_count > 0:
            time_result = await db.execute(
                select(
                    func.avg(
                        func.strftime(
                            "%s",
                            ExecutionLog.completed_at,
                        )
                        - func.strftime(
                            "%s",
                            ExecutionLog.started_at,
                        )
                    )
                ).where(
                    ExecutionLog.scene_id == scene_id,
                    ExecutionLog.status == "completed",
                    ExecutionLog.completed_at.isnot(None),
                )
            )
            avg_seconds = time_result.scalar()
            avg_time = round(float(avg_seconds), 2) if avg_seconds else 0.0

        return SceneStats(
            scene_id=scene.id,
            scene_name=scene.name,
            trigger_count=scene.trigger_count or 0,
            last_triggered_at=scene.last_triggered_at,
            success_rate=success_rate,
            avg_execution_time=avg_time,
        )

    async def get_all_stats(self, db: AsyncSession) -> List[SceneStats]:
        result = await db.execute(select(Scene))
        scenes = result.scalars().all()
        stats = []
        for scene in scenes:
            stat = await self.get_scene_stats(db, scene.id)
            stats.append(stat)
        stats.sort(key=lambda s: s.trigger_count, reverse=True)
        return stats

    async def get_top_scenes(
        self, db: AsyncSession, limit: int = 10
    ) -> List[SceneStats]:
        result = await db.execute(
            select(Scene).order_by(Scene.trigger_count.desc()).limit(limit)
        )
        scenes = result.scalars().all()
        stats = []
        for scene in scenes:
            stat = await self.get_scene_stats(db, scene.id)
            stats.append(stat)
        return stats


stats_service = StatsService()
