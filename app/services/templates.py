from typing import Dict, List, Any
from app.schemas.scene import SceneCreate, TriggerCreate, ActionCreate


class SceneTemplate:
    def __init__(self, template_id: str, name: str, description: str, icon: str, category: str):
        self.template_id = template_id
        self.name = name
        self.description = description
        self.icon = icon
        self.category = category

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "category": self.category
        }

    def to_scene_create(self) -> SceneCreate:
        raise NotImplementedError


class GoHomeTemplate(SceneTemplate):
    def __init__(self):
        super().__init__(
            template_id="go_home",
            name="回家模式",
            description="开门自动开灯、开空调、拉窗帘、播放轻音乐，营造温馨的回家氛围",
            icon="🏠",
            category="daily"
        )

    def to_scene_create(self) -> SceneCreate:
        return SceneCreate(
            name="回家模式",
            description="开门自动开灯、开空调、拉窗帘、播放轻音乐",
            icon="🏠",
            priority=8,
            debug_mode=False,
            mutually_exclusive_with=[],
            triggers=[
                TriggerCreate(
                    trigger_type="device_state",
                    name="前门解锁",
                    enabled=True,
                    config={
                        "device_id": "lock_front_door",
                        "field": "is_locked",
                        "operator": "eq",
                        "value": False
                    }
                ),
                TriggerCreate(
                    trigger_type="geofence",
                    name="到家地理围栏",
                    enabled=True,
                    config={
                        "latitude": 39.9042,
                        "longitude": 116.4074,
                        "radius": 200,
                        "event": "enter"
                    }
                )
            ],
            actions=[
                ActionCreate(
                    action_type="parallel",
                    name="回家并行动作组",
                    execution_mode="parallel",
                    order_index=0,
                    children=[
                        ActionCreate(
                            action_type="device_command",
                            name="开客厅主灯",
                            order_index=0,
                            device_id="light_living_1",
                            command={"command": "turn_on", "params": {"brightness": 80}}
                        ),
                        ActionCreate(
                            action_type="device_command",
                            name="开客厅氛围灯",
                            order_index=1,
                            device_id="light_living_2",
                            command={"command": "turn_on", "params": {"brightness": 50, "color": "#ffd700"}}
                        ),
                        ActionCreate(
                            action_type="device_command",
                            name="开客厅空调",
                            order_index=2,
                            device_id="ac_living_1",
                            command={"command": "turn_on", "params": {"temperature": 26, "mode": "auto"}}
                        ),
                        ActionCreate(
                            action_type="device_command",
                            name="打开客厅窗帘",
                            order_index=3,
                            device_id="curtain_living_1",
                            command={"command": "open", "params": {}}
                        )
                    ]
                ),
                ActionCreate(
                    action_type="condition",
                    name="判断光线",
                    order_index=1,
                    condition={
                        "device_id": "sensor_light_living",
                        "field": "value",
                        "operator": "lt",
                        "value": 300
                    },
                    children=[
                        ActionCreate(
                            action_type="device_command",
                            name="光线暗开更多灯",
                            order_index=0,
                            device_id="light_kitchen_1",
                            command={"command": "turn_on", "params": {"brightness": 70}}
                        )
                    ]
                ),
                ActionCreate(
                    action_type="delay",
                    name="等待2秒",
                    order_index=2,
                    command={"seconds": 2}
                ),
                ActionCreate(
                    action_type="device_command",
                    name="播放回家音乐",
                    order_index=3,
                    device_id="music_living_1",
                    command={"command": "play", "params": {"playlist": "回家", "volume": 40}}
                )
            ]
        )


class LeaveHomeTemplate(SceneTemplate):
    def __init__(self):
        super().__init__(
            template_id="leave_home",
            name="离家模式",
            description="一键关闭所有灯光、空调，拉上窗帘，锁门，开启安防",
            icon="🚪",
            category="daily"
        )

    def to_scene_create(self) -> SceneCreate:
        return SceneCreate(
            name="离家模式",
            description="关闭所有灯光空调，拉窗帘，锁门",
            icon="🚪",
            priority=8,
            mutually_exclusive_with=[],
            triggers=[
                TriggerCreate(
                    trigger_type="device_state",
                    name="门已上锁",
                    enabled=True,
                    config={
                        "device_id": "lock_front_door",
                        "field": "is_locked",
                        "operator": "eq",
                        "value": True
                    }
                ),
                TriggerCreate(
                    trigger_type="geofence",
                    name="离开地理围栏",
                    enabled=True,
                    config={
                        "latitude": 39.9042,
                        "longitude": 116.4074,
                        "radius": 500,
                        "event": "exit"
                    }
                )
            ],
            actions=[
                ActionCreate(
                    action_type="parallel",
                    name="离家并行动作组",
                    execution_mode="parallel",
                    children=[
                        ActionCreate(
                            action_type="device_command",
                            name="关客厅主灯",
                            device_id="light_living_1",
                            command={"command": "turn_off", "params": {}}
                        ),
                        ActionCreate(
                            action_type="device_command",
                            name="关客厅氛围灯",
                            device_id="light_living_2",
                            command={"command": "turn_off", "params": {}}
                        ),
                        ActionCreate(
                            action_type="device_command",
                            name="关卧室灯",
                            device_id="light_bedroom_1",
                            command={"command": "turn_off", "params": {}}
                        ),
                        ActionCreate(
                            action_type="device_command",
                            name="关厨房灯",
                            device_id="light_kitchen_1",
                            command={"command": "turn_off", "params": {}}
                        ),
                        ActionCreate(
                            action_type="device_command",
                            name="关客厅空调",
                            device_id="ac_living_1",
                            command={"command": "turn_off", "params": {}}
                        ),
                        ActionCreate(
                            action_type="device_command",
                            name="关卧室空调",
                            device_id="ac_bedroom_1",
                            command={"command": "turn_off", "params": {}}
                        ),
                        ActionCreate(
                            action_type="device_command",
                            name="拉上客厅窗帘",
                            device_id="curtain_living_1",
                            command={"command": "close", "params": {}}
                        ),
                        ActionCreate(
                            action_type="device_command",
                            name="拉上卧室窗帘",
                            device_id="curtain_bedroom_1",
                            command={"command": "close", "params": {}}
                        ),
                        ActionCreate(
                            action_type="device_command",
                            name="停止音乐",
                            device_id="music_living_1",
                            command={"command": "stop", "params": {}}
                        )
                    ]
                ),
                ActionCreate(
                    action_type="device_command",
                    name="锁门",
                    order_index=1,
                    device_id="lock_front_door",
                    command={"command": "lock", "params": {}}
                )
            ]
        )


class SleepTemplate(SceneTemplate):
    def __init__(self):
        super().__init__(
            template_id="sleep",
            name="睡眠模式",
            description="关闭主灯，开启夜灯，调节空调睡眠温度，拉窗帘，播放助眠音乐",
            icon="🌙",
            category="daily"
        )

    def to_scene_create(self) -> SceneCreate:
        return SceneCreate(
            name="睡眠模式",
            description="关闭主灯，开夜灯，空调调至睡眠温度",
            icon="🌙",
            priority=7,
            mutually_exclusive_with=[],
            triggers=[
                TriggerCreate(
                    trigger_type="cron",
                    name="每晚22:30",
                    enabled=True,
                    config={"expression": "30 22 * * *"}
                )
            ],
            actions=[
                ActionCreate(
                    action_type="parallel",
                    name="睡眠并行动作组",
                    execution_mode="parallel",
                    children=[
                        ActionCreate(
                            action_type="device_command",
                            name="关客厅主灯",
                            device_id="light_living_1",
                            command={"command": "turn_off", "params": {}}
                        ),
                        ActionCreate(
                            action_type="device_command",
                            name="关客厅氛围灯",
                            device_id="light_living_2",
                            command={"command": "turn_off", "params": {}}
                        ),
                        ActionCreate(
                            action_type="device_command",
                            name="关厨房灯",
                            device_id="light_kitchen_1",
                            command={"command": "turn_off", "params": {}}
                        ),
                        ActionCreate(
                            action_type="device_command",
                            name="卧室灯调至夜灯模式",
                            device_id="light_bedroom_1",
                            command={"command": "turn_on", "params": {"brightness": 10, "color": "#ff9900"}}
                        ),
                        ActionCreate(
                            action_type="device_command",
                            name="空调设为睡眠模式",
                            device_id="ac_bedroom_1",
                            command={"command": "turn_on", "params": {"temperature": 27, "mode": "auto", "fan_speed": "low"}}
                        ),
                        ActionCreate(
                            action_type="device_command",
                            name="拉上卧室窗帘",
                            device_id="curtain_bedroom_1",
                            command={"command": "close", "params": {}}
                        )
                    ]
                ),
                ActionCreate(
                    action_type="device_command",
                    name="播放助眠音乐",
                    order_index=1,
                    device_id="music_bedroom_1",
                    command={"command": "play", "params": {"playlist": "助眠", "volume": 20}}
                )
            ]
        )


class HomeTheaterTemplate(SceneTemplate):
    def __init__(self):
        super().__init__(
            template_id="home_theater",
            name="影院模式",
            description="调暗灯光，拉上窗帘，开启空调，准备好观看电影的环境",
            icon="🎬",
            category="entertainment"
        )

    def to_scene_create(self) -> SceneCreate:
        return SceneCreate(
            name="影院模式",
            description="调暗灯光，拉窗帘，营造影院氛围",
            icon="🎬",
            priority=6,
            mutually_exclusive_with=[],
            triggers=[
                TriggerCreate(
                    trigger_type="manual",
                    name="手动触发",
                    enabled=True,
                    config={}
                )
            ],
            actions=[
                ActionCreate(
                    action_type="parallel",
                    name="影院并行动作组",
                    execution_mode="parallel",
                    children=[
                        ActionCreate(
                            action_type="device_command",
                            name="客厅主灯调暗",
                            device_id="light_living_1",
                            command={"command": "set_brightness", "params": {"value": 20}}
                        ),
                        ActionCreate(
                            action_type="device_command",
                            name="氛围灯设为电影色",
                            device_id="light_living_2",
                            command={"command": "turn_on", "params": {"brightness": 30, "color": "#4a0080"}}
                        ),
                        ActionCreate(
                            action_type="device_command",
                            name="拉上客厅窗帘",
                            device_id="curtain_living_1",
                            command={"command": "close", "params": {}}
                        ),
                        ActionCreate(
                            action_type="device_command",
                            name="开启客厅空调",
                            device_id="ac_living_1",
                            command={"command": "turn_on", "params": {"temperature": 25, "mode": "cool"}}
                        )
                    ]
                ),
                ActionCreate(
                    action_type="device_command",
                    name="播放电影原声",
                    order_index=1,
                    device_id="music_living_1",
                    command={"command": "play", "params": {"playlist": "电影原声", "volume": 50}}
                )
            ]
        )


class MorningRoutineTemplate(SceneTemplate):
    def __init__(self):
        super().__init__(
            template_id="morning_routine",
            name="早安模式",
            description="早晨自动拉开窗帘，播放晨间音乐，开启咖啡机（模拟）",
            icon="☀️",
            category="daily"
        )

    def to_scene_create(self) -> SceneCreate:
        return SceneCreate(
            name="早安模式",
            description="拉开窗帘，播放晨间音乐",
            icon="☀️",
            priority=6,
            mutually_exclusive_with=[],
            triggers=[
                TriggerCreate(
                    trigger_type="cron",
                    name="工作日早上7点",
                    enabled=True,
                    config={"expression": "0 7 * * 1-5"}
                )
            ],
            actions=[
                ActionCreate(
                    action_type="parallel",
                    name="早安并行动作组",
                    execution_mode="parallel",
                    children=[
                        ActionCreate(
                            action_type="device_command",
                            name="打开卧室窗帘",
                            device_id="curtain_bedroom_1",
                            command={"command": "open", "params": {}}
                        ),
                        ActionCreate(
                            action_type="device_command",
                            name="打开客厅窗帘",
                            device_id="curtain_living_1",
                            command={"command": "set_position", "params": {"value": 80}}
                        ),
                        ActionCreate(
                            action_type="device_command",
                            name="空调设为白天模式",
                            device_id="ac_bedroom_1",
                            command={"command": "turn_off", "params": {}}
                        )
                    ]
                ),
                ActionCreate(
                    action_type="device_command",
                    name="播放晨间新闻/音乐",
                    order_index=1,
                    device_id="music_living_1",
                    command={"command": "play", "params": {"playlist": "晨间", "volume": 45}}
                )
            ]
        )


class SecurityAlarmTemplate(SceneTemplate):
    def __init__(self):
        super().__init__(
            template_id="security_alarm",
            name="安防警报",
            description="检测到异常时开启所有灯光，播放警报声",
            icon="🚨",
            category="security"
        )

    def to_scene_create(self) -> SceneCreate:
        return SceneCreate(
            name="安防警报",
            description="异常时开启所有灯光，播放警报",
            icon="🚨",
            priority=10,
            mutually_exclusive_with=[],
            triggers=[
                TriggerCreate(
                    trigger_type="device_state",
                    name="检测到有人闯入",
                    enabled=True,
                    config={
                        "device_id": "sensor_motion_living",
                        "field": "value",
                        "operator": "eq",
                        "value": True,
                        "duration": 5
                    }
                )
            ],
            actions=[
                ActionCreate(
                    action_type="parallel",
                    name="警报并行动作组",
                    execution_mode="parallel",
                    children=[
                        ActionCreate(
                            action_type="device_command",
                            name="开客厅主灯",
                            device_id="light_living_1",
                            command={"command": "turn_on", "params": {"brightness": 100}}
                        ),
                        ActionCreate(
                            action_type="device_command",
                            name="开卧室灯",
                            device_id="light_bedroom_1",
                            command={"command": "turn_on", "params": {"brightness": 100}}
                        ),
                        ActionCreate(
                            action_type="device_command",
                            name="开厨房灯",
                            device_id="light_kitchen_1",
                            command={"command": "turn_on", "params": {"brightness": 100}}
                        )
                    ]
                ),
                ActionCreate(
                    action_type="device_command",
                    name="播放警报声",
                    order_index=1,
                    device_id="music_living_1",
                    command={"command": "play", "params": {"playlist": "警报", "volume": 100}}
                )
            ]
        )


class TemplateService:
    def __init__(self):
        self._templates: Dict[str, SceneTemplate] = {}
        self._register_templates()

    def _register_templates(self):
        templates = [
            GoHomeTemplate(),
            LeaveHomeTemplate(),
            SleepTemplate(),
            HomeTheaterTemplate(),
            MorningRoutineTemplate(),
            SecurityAlarmTemplate()
        ]
        for t in templates:
            self._templates[t.template_id] = t

    def list_templates(self, category: str = None) -> List[Dict[str, Any]]:
        result = []
        for t in self._templates.values():
            if category is None or t.category == category:
                result.append(t.to_dict())
        return result

    def get_template(self, template_id: str) -> SceneTemplate:
        return self._templates.get(template_id)

    def get_categories(self) -> List[str]:
        return sorted(list(set(t.category for t in self._templates.values())))

    def create_scene_from_template(self, template_id: str, custom_name: str = None) -> SceneCreate:
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"模板不存在: {template_id}")
        scene_create = template.to_scene_create()
        if custom_name:
            scene_create.name = custom_name
        return scene_create


template_service = TemplateService()
