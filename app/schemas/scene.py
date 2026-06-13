from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class TriggerBase(BaseModel):
    trigger_type: str = Field(..., description="manual|device_state|cron|geofence|sensor")
    name: Optional[str] = None
    enabled: bool = True
    config: Dict[str, Any] = Field(default_factory=dict)


class TriggerCreate(TriggerBase):
    pass


class TriggerUpdate(BaseModel):
    trigger_type: Optional[str] = None
    name: Optional[str] = None
    enabled: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


class TriggerResponse(TriggerBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    scene_id: int
    last_evaluated_at: Optional[datetime] = None
    last_evaluated_result: Optional[bool] = None


class ActionBase(BaseModel):
    action_type: str = Field(..., description="device_command|delay|parallel|condition|notify")
    name: Optional[str] = None
    execution_mode: str = "sequential"
    order_index: int = 0
    device_id: Optional[str] = None
    command: Dict[str, Any] = Field(default_factory=dict)
    condition: Optional[Dict[str, Any]] = None
    timeout: int = 30
    retry_count: int = 1


class ActionCreate(ActionBase):
    children: Optional[List["ActionCreate"]] = None


class ActionUpdate(BaseModel):
    action_type: Optional[str] = None
    name: Optional[str] = None
    execution_mode: Optional[str] = None
    order_index: Optional[int] = None
    device_id: Optional[str] = None
    command: Optional[Dict[str, Any]] = None
    condition: Optional[Dict[str, Any]] = None
    timeout: Optional[int] = None
    retry_count: Optional[int] = None


class ActionResponse(ActionBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    scene_id: int
    parent_id: Optional[int] = None
    children: List["ActionResponse"] = Field(default_factory=list)


class SceneBase(BaseModel):
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    priority: int = 5
    enabled: bool = True
    debug_mode: bool = False
    mutually_exclusive_with: List[int] = Field(default_factory=list)


class SceneCreate(SceneBase):
    triggers: List[TriggerCreate] = Field(default_factory=list)
    actions: List[ActionCreate] = Field(default_factory=list)


class SceneUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    priority: Optional[int] = None
    enabled: Optional[bool] = None
    debug_mode: Optional[bool] = None
    mutually_exclusive_with: Optional[List[int]] = None
    triggers: Optional[List[TriggerCreate]] = None
    actions: Optional[List[ActionCreate]] = None


class SceneResponse(SceneBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_template: bool = False
    template_category: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_triggered_at: Optional[datetime] = None
    trigger_count: int = 0
    triggers: List[TriggerResponse] = Field(default_factory=list)
    actions: List[ActionResponse] = Field(default_factory=list)


class ExecutionLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    scene_id: int
    trigger_id: Optional[int] = None
    execution_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    trigger_type: Optional[str] = None
    trigger_source: Optional[str] = None
    action_results: List[Dict[str, Any]] = Field(default_factory=list)
    error_message: Optional[str] = None
    is_debug: bool = False
    interrupted_by: Optional[int] = None
    interrupt_reason: Optional[str] = None


class DeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    device_type: str
    room: Optional[str] = None
    is_online: bool
    state: Dict[str, Any] = Field(default_factory=dict)
    last_seen: datetime
    capabilities: List[str] = Field(default_factory=list)


class DeviceCommand(BaseModel):
    command: str
    params: Dict[str, Any] = Field(default_factory=dict)


class ConflictCheckResult(BaseModel):
    has_conflict: bool
    conflict_type: Optional[str] = None
    conflicting_scenes: List[int] = Field(default_factory=list)
    message: Optional[str] = None


class SceneStats(BaseModel):
    scene_id: int
    scene_name: str
    trigger_count: int
    last_triggered_at: Optional[datetime] = None
    success_rate: float
    avg_execution_time: float
