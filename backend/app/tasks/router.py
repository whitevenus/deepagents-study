from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agent_runtime.executor import run_task as run_agent_task
from app.database import SessionLocal, get_db
from app.tasks.models import Task
from app.tasks.schemas import TaskCreate, TaskOut

# ponytail: 业务简单,暂不拆 service/crud 层;逻辑变复杂时再按 FBA 五段式拆出来。
router = APIRouter(prefix="/tasks", tags=["tasks"])


def _execute(task_id: str):
    """后台执行:pending → in_progress → done/failed,把结果写回。"""
    # ponytail: MVP 用 FastAPI BackgroundTasks;并发量大或要可取消时再上 Celery / 异步 worker(Ch6)。
    db = SessionLocal()
    try:
        task = db.get(Task, task_id)
        if not task:
            return
        task.status = "in_progress"
        db.commit()
        try:
            task.result = run_agent_task(task.title, task.description)
            task.status = "done"
        except Exception as e:  # noqa: BLE001  失败也要落库,看板才能显示
            task.result = f"执行失败:{e}"
            task.status = "failed"
        db.commit()
    finally:
        db.close()


@router.post("", response_model=TaskOut)
def create_task(payload: TaskCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    task = Task(title=payload.title, description=payload.description)
    db.add(task)
    db.commit()
    db.refresh(task)
    background_tasks.add_task(_execute, task.id)  # 立即返回 pending,后台跑 agent
    return task


@router.get("", response_model=list[TaskOut])
def list_tasks(db: Session = Depends(get_db)):
    return db.query(Task).order_by(Task.created_at.desc()).all()


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: str, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "task not found")
    return task
