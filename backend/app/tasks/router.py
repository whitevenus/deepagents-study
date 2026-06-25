from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.permissions import can, current_user, data_scope, require
from app.database import get_db
from app.tasks.models import Task
from app.tasks.schemas import TaskCreate, TaskOut

# ponytail: 业务简单,暂不拆 service/crud 层;逻辑变复杂时再按 FBA 五段式拆出来。
router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskOut)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    user: str = Depends(require("task", "create")),  # RBAC:只有能 create 的角色放行
):
    # Phase 2:只入库,执行由独立 worker 轮询接单(不再写死在 POST 里)。
    # decompose=True → 状态 decomposing,worker 会先拆成子任务而非直接执行。
    task = Task(
        title=payload.title,
        description=payload.description,
        status="decomposing" if payload.decompose else "pending",
        owner_id=user,  # 行级数据权限的归属人
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("", response_model=list[TaskOut])
def list_tasks(db: Session = Depends(get_db), user: str = Depends(current_user)):
    # ABAC 数据范围:all 看全部,own 只看自己的,None 无权。
    scope = data_scope(user, "task", "read")
    if scope is None:
        raise HTTPException(403, "无权限:read task")
    q = db.query(Task)
    if scope == "own":
        q = q.filter(Task.owner_id == user)
    return q.order_by(Task.created_at.desc()).all()


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: str, db: Session = Depends(get_db), user: str = Depends(current_user)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "task not found")
    if not can(user, "task", "read", owner=task.owner_id):
        raise HTTPException(403, "无权限:read task")
    return task


@router.post("/{task_id}/cancel", response_model=TaskOut)
def cancel_task(task_id: str, db: Session = Depends(get_db), user: str = Depends(current_user)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "task not found")
    if not can(user, "task", "cancel", owner=task.owner_id):
        raise HTTPException(403, "无权限:cancel task")
    if task.status in ("done", "failed", "cancelled"):
        raise HTTPException(409, f"任务已 {task.status},无法取消")
    # ponytail: 可靠取消的是尚未开始的 pending;in_progress 的真正中断需 Ch6 异步子 agent 的 cancel,
    # 这里标记为 cancelled,worker 跑完会丢弃结果不覆盖(_finish 里判断)。
    task.status = "cancelled"
    db.commit()
    db.refresh(task)
    return task
