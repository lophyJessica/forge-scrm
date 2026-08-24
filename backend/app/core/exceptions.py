"""统一业务异常。"""

from fastapi import HTTPException, status


class BizError(HTTPException):
    def __init__(self, detail: str, code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(status_code=code, detail=detail)


def not_found(name: str) -> BizError:
    return BizError(f"{name}不存在", status.HTTP_404_NOT_FOUND)


def forbidden(detail: str = "无权限执行该操作") -> BizError:
    return BizError(detail, status.HTTP_403_FORBIDDEN)


def unauthorized(detail: str = "未登录或登录已过期") -> BizError:
    return BizError(detail, status.HTTP_401_UNAUTHORIZED)
