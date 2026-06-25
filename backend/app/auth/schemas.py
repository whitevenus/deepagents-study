from pydantic import BaseModel


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeOut(BaseModel):
    username: str
    roles: list[str]  # 从 Casbin g 策略查出来
