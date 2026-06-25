"""认证(authn)原语:密码哈希 + JWT 签发/校验。
与授权(authz, permissions.py 的 Casbin)解耦——这里只回答「你是谁」,不管「你能干什么」。"""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import JWT_EXPIRE_HOURS, JWT_SECRET

_ALG = "HS256"


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def make_token(username: str) -> str:
    payload = {
        "sub": username,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=_ALG)


def read_token(token: str) -> str:
    """校验签名+过期,返回 username(sub)。无效/过期会抛 jwt 异常,由调用方转 401。"""
    return jwt.decode(token, JWT_SECRET, algorithms=[_ALG])["sub"]
