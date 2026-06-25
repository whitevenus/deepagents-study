from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.permissions import current_user, roles_for
from app.auth.schemas import MeOut, TokenOut
from app.auth.security import make_token, verify_password
from app.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # OAuth2 标准表单(username/password 字段);Swagger Authorize 按钮可直接用。
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(401, "用户名或密码错误")
    return TokenOut(access_token=make_token(user.username))


@router.get("/me", response_model=MeOut)
def me(user: str = Depends(current_user)):
    return MeOut(username=user, roles=roles_for(user))
