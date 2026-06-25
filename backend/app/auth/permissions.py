"""业务数据权限平面(Casbin RBAC + ABAC 行级数据范围)。

两个权限平面别混:这里管「谁能对哪条业务数据做什么」(FastAPI/DB 层);
agent 虚拟文件系统的读写权限是另一套(deepagents namespace + FilesystemPermission)。

身份:目前用 X-User-Id 头当 stub 身份(谁声称是谁就是谁)。
ponytail: 真正的登录/JWT 留到 Phase 3 UI(登录页 = 第二个真实页面时再上),
这里先把鉴权(authz)做扎实——授权矩阵和越权拦截不依赖认证方式。
"""

import os

import casbin
from fastapi import Depends, Header, HTTPException

_DIR = os.path.dirname(__file__)
_enforcer: casbin.Enforcer | None = None


def enforcer() -> casbin.Enforcer:
    global _enforcer
    if _enforcer is None:
        _enforcer = casbin.Enforcer(
            os.path.join(_DIR, "model.conf"), os.path.join(_DIR, "policy.csv")
        )
    return _enforcer


def can(user: str, obj: str, act: str, owner: str | None = None) -> bool:
    """单对象鉴权。owner=被操作对象的拥有者;创建/无主对象时传 user 自己即可(scope=all 时无关)。"""
    return enforcer().enforce(user, obj, act, owner if owner is not None else user)


def data_scope(user: str, obj: str, act: str) -> str | None:
    """列表场景的数据范围:返回 'all' / 'own' / None(无权)。
    探测法:用一个非本人的 owner 试 → 能过说明命中 scope=all;否则用本人试 → 能过说明 scope=own。"""
    if can(user, obj, act, owner="__nobody__"):
        return "all"
    if can(user, obj, act, owner=user):
        return "own"
    return None


def current_user(x_user_id: str | None = Header(default=None)) -> str:
    """从请求头取身份。缺身份 → 401(信任边界,默认拒绝)。"""
    if not x_user_id:
        raise HTTPException(401, "缺少身份(X-User-Id)")
    return x_user_id


def require(obj: str, act: str):
    """路由级 RBAC 依赖工厂(不涉及具体对象拥有者的动作,如 create/list 入口)。"""

    def dep(user: str = Depends(current_user)) -> str:
        if not can(user, obj, act):
            raise HTTPException(403, f"无权限:{act} {obj}")
        return user

    return dep
