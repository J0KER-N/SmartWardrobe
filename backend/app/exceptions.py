from fastapi import HTTPException, status

class ResourceNotFoundError(HTTPException):
    """资源不存在异常"""
    def __init__(self, detail: str = "资源不存在"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class ResourceAlreadyExistsError(HTTPException):
    """资源已存在异常"""
    def __init__(self, detail: str = "资源已存在"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

class InvalidCredentialsError(HTTPException):
    """无效凭证异常"""
    def __init__(self, detail: str = "用户名或密码错误"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )

class AIClientError(HTTPException):
    """AI服务调用异常"""
    def __init__(self, detail: str = "AI服务调用失败"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)