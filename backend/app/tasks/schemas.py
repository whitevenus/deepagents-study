from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TaskCreate(BaseModel):
    title: str
    description: str = ""
    decompose: bool = False  # True:先把任务拆成子任务,而不是直接执行


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str
    status: str
    result: str
    parent_id: str | None = None
    created_at: datetime
    updated_at: datetime
