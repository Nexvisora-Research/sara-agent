"""Shared serializable models for Sara Phase B."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return uuid4().hex


# ── Kanban ────────────────────────────────────────────────────────────────


class KanbanColumn(StrEnum):
    BACKLOG = "backlog"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class TaskPriority(StrEnum):
    LOWEST = "lowest"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class KanbanTask(BaseModel):
    id: str = Field(default_factory=new_id)
    title: str
    description: str = ""
    column: KanbanColumn = KanbanColumn.BACKLOG
    priority: TaskPriority = TaskPriority.MEDIUM
    assigned_agent: str | None = None
    dependencies: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    board_id: str = ""
    parent_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    started_at: datetime | None = None
    completed_at: datetime | None = None


class KanbanBoard(BaseModel):
    id: str = Field(default_factory=new_id)
    name: str
    description: str = ""
    created_at: datetime = Field(default_factory=utc_now)


# ── Workflow ──────────────────────────────────────────────────────────────


class WorkflowStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowStepType(StrEnum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    SUB_WORKFLOW = "sub_workflow"


class WorkflowStep(BaseModel):
    id: str = Field(default_factory=new_id)
    name: str
    step_type: WorkflowStepType = WorkflowStepType.SEQUENTIAL
    handler: str = ""
    input_map: dict[str, Any] = Field(default_factory=dict)
    condition: str | None = None
    retry_count: int = 0
    retry_delay_seconds: float = 1.0
    timeout_seconds: float | None = None
    depends_on: list[str] = Field(default_factory=list)


class WorkflowDefinition(BaseModel):
    id: str = Field(default_factory=new_id)
    name: str
    description: str = ""
    version: str = "1.0"
    steps: list[WorkflowStep] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class WorkflowExecution(BaseModel):
    id: str = Field(default_factory=new_id)
    workflow_id: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    current_step: str | None = None
    step_results: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    started_at: datetime | None = None
    completed_at: datetime | None = None


# ── Swarm ─────────────────────────────────────────────────────────────────


class SwarmAgentRole(StrEnum):
    PLANNER = "planner"
    RESEARCH = "research"
    CODING = "coding"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    MEMORY = "memory"
    CRITIC = "critic"
    SUPERVISOR = "supervisor"


class SwarmMessage(BaseModel):
    id: str = Field(default_factory=new_id)
    sender_id: str
    recipient_id: str | None = None
    message_type: str = "text"
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utc_now)


class SwarmAgentSpec(BaseModel):
    id: str = Field(default_factory=new_id)
    name: str
    role: SwarmAgentRole
    description: str = ""
    capabilities: list[str] = Field(default_factory=list)
    max_concurrent_tasks: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)


class SwarmRun(BaseModel):
    id: str = Field(default_factory=new_id)
    goal: str
    agents: list[str] = Field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.PENDING
    result: str | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None


class SwarmConsensusVote(BaseModel):
    run_id: str
    agent_id: str
    approve: bool
    comment: str = ""
    timestamp: datetime = Field(default_factory=utc_now)


# ── Watch / Monitor ────────────────────────────────────────────────────────


class WatchTargetType(StrEnum):
    FOLDER = "folder"
    REPOSITORY = "repository"
    LOG = "log"
    WEBSITE = "website"
    SYSTEM = "system"


class WatchEventKind(StrEnum):
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    ERROR = "error"


class WatchTarget(BaseModel):
    id: str = Field(default_factory=new_id)
    name: str
    target_type: WatchTargetType
    path: str = ""
    url: str = ""
    interval_seconds: float = 10.0
    rules: list[WatchRule] = Field(default_factory=list)
    enabled: bool = True
    created_at: datetime = Field(default_factory=utc_now)


class WatchRule(BaseModel):
    pattern: str = "*"
    event_kind: WatchEventKind | None = None
    action: str = "notify"


class WatchEventRecord(BaseModel):
    id: str = Field(default_factory=new_id)
    target_id: str
    kind: WatchEventKind
    path: str = ""
    message: str = ""
    timestamp: datetime = Field(default_factory=utc_now)


# ── Model Router ───────────────────────────────────────────────────────────


class ModelCapability(StrEnum):
    CODE = "code"
    REASONING = "reasoning"
    RESEARCH = "research"
    CONVERSATION = "conversation"
    VISION = "vision"
    FUNCTION_CALLING = "function_calling"
    LONG_CONTEXT = "long_context"
    FAST = "fast"
    CHEAP = "cheap"


class ModelRoute(BaseModel):
    id: str = Field(default_factory=new_id)
    provider: str
    model_name: str
    base_url: str = ""
    api_key_env: str = ""
    capabilities: list[ModelCapability] = Field(default_factory=list)
    priority: int = 0
    cost_per_1k_tokens: float = 0.0
    latency_p50_ms: float = 0.0
    max_context_tokens: int = 8192
    enabled: bool = True


class RouterConfig(BaseModel):
    id: str = Field(default_factory=new_id)
    name: str = "default"
    routes: list[ModelRoute] = Field(default_factory=list)
    fallback_strategy: str = "next_available"
    created_at: datetime = Field(default_factory=utc_now)


# ── Reflection ─────────────────────────────────────────────────────────────


class CritiqueAspect(StrEnum):
    CORRECTNESS = "correctness"
    COMPLETENESS = "completeness"
    EFFICIENCY = "efficiency"
    STYLE = "style"
    SECURITY = "security"
    BEST_PRACTICES = "best_practices"


class CritiqueResult(BaseModel):
    task_id: str
    agent_id: str
    aspect: CritiqueAspect
    score: float = Field(ge=0.0, le=1.0)
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    summary: str = ""
    timestamp: datetime = Field(default_factory=utc_now)


class ReflectionReport(BaseModel):
    id: str = Field(default_factory=new_id)
    task_id: str
    agent_id: str
    critiques: list[CritiqueResult] = Field(default_factory=list)
    overall_score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    improvement_suggestions: list[str] = Field(default_factory=list)
    should_retry: bool = False
    retry_count: int = 0
    max_retries: int = 3
    timestamp: datetime = Field(default_factory=utc_now)


# ── Planner ────────────────────────────────────────────────────────────────


class PlannerGoal(BaseModel):
    id: str = Field(default_factory=new_id)
    description: str
    constraints: list[str] = Field(default_factory=list)
    priority: TaskPriority = TaskPriority.MEDIUM
    created_at: datetime = Field(default_factory=utc_now)


class PlannerTask(BaseModel):
    id: str = Field(default_factory=new_id)
    goal_id: str
    title: str
    description: str = ""
    role: str = "coding"
    dependencies: list[str] = Field(default_factory=list)
    estimated_effort: str = "medium"
    priority: int = 0
    status: WorkflowStatus = WorkflowStatus.PENDING


class TaskGraphNode(BaseModel):
    task_id: str
    title: str
    depth: int = 0
    children: list[TaskGraphNode] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExecutionStrategy(BaseModel):
    id: str = Field(default_factory=new_id)
    goal_id: str
    approach: str
    steps: list[str] = Field(default_factory=list)
    parallel_groups: list[list[str]] = Field(default_factory=list)
    estimated_duration_seconds: float = 0.0
    risk_factors: list[str] = Field(default_factory=list)
