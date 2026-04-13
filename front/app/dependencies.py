from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .security import verify_token
import logging
logger = logging.getLogger(__name__)

# OAuth2认证方案
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """获取当前登录用户（依赖注入）"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="令牌验证失败，请重新登录",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # 验证令牌
    logger.debug(f"Verifying token: {token}")
    payload = verify_token(token)
    logger.debug(f"verify_token returned: {payload}")
    if not payload:
        raise credentials_exception
    
    # 查询用户
    user = db.query(User).filter(User.id == payload.sub).first()
    if not user or not user.is_active:
        raise credentials_exception
    
    return user