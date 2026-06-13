from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from app.database import Base


class Scene(Base):
    __tablename__ = "scenes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500))
    icon = Column(String(100))
    priority = Column(Integer, default=5)
    enabled = Column(Boolean, default=True)
    debug_mode = Column(Boolean, default=False)
    is_template = Column(Boolean, default=False)
    template_category = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_triggered_at = Column(DateTime)
    trigger_count = Column(Integer, default=0)
    mutually_exclusive_with = Column(JSON, default=list)

    triggers = relationship("Trigger", back_populates="scene", cascade="all, delete-orphan")
    actions = relationship("Action", back_populates="scene", cascade="all, delete-orphan")
    execution_logs = relationship("ExecutionLog", back_populates="scene")


class Trigger(Base):
    __tablename__ = "triggers"

    id = Column(Integer, primary_key=True, index=True)
    scene_id = Column(Integer, ForeignKey("scenes.id"), nullable=False)
    trigger_type = Column(String(30), nullable=False)
    name = Column(String(100))
    enabled = Column(Boolean, default=True)
    config = Column(JSON, default=dict)
    last_evaluated_at = Column(DateTime)
    last_evaluated_result = Column(Boolean)

    scene = relationship("Scene", back_populates="triggers")


class Action(Base):
    __tablename__ = "actions"

    id = Column(Integer, primary_key=True, index=True)
    scene_id = Column(Integer, ForeignKey("scenes.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("actions.id"))
    action_type = Column(String(30), nullable=False)
    name = Column(String(100))
    execution_mode = Column(String(20), default="sequential")
    order_index = Column(Integer, default=0)
    device_id = Column(String(100))
    command = Column(JSON, default=dict)
    condition = Column(JSON)
    timeout = Column(Integer, default=30)
    retry_count = Column(Integer, default=1)

    scene = relationship("Scene", back_populates="actions")
    parent = relationship("Action", remote_side=[id], backref="children")


class ExecutionLog(Base):
    __tablename__ = "execution_logs"

    id = Column(Integer, primary_key=True, index=True)
    scene_id = Column(Integer, ForeignKey("scenes.id"), nullable=False)
    trigger_id = Column(Integer, ForeignKey("triggers.id"))
    execution_id = Column(String(50), nullable=False)
    status = Column(String(30), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    trigger_type = Column(String(30))
    trigger_source = Column(String(200))
    action_results = Column(JSON, default=list)
    error_message = Column(String(500))
    is_debug = Column(Boolean, default=False)
    interrupted_by = Column(Integer)
    interrupt_reason = Column(String(200))

    scene = relationship("Scene", back_populates="execution_logs")


class Device(Base):
    __tablename__ = "devices"

    id = Column(String(100), primary_key=True)
    name = Column(String(100), nullable=False)
    device_type = Column(String(50), nullable=False)
    room = Column(String(100))
    is_online = Column(Boolean, default=True)
    state = Column(JSON, default=dict)
    last_seen = Column(DateTime, default=datetime.utcnow)
    capabilities = Column(JSON, default=list)
