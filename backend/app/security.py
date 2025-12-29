import bcrypt
from datetime import datetime, timedelta
from jose.exceptions import ExpiredSignatureError
from typing import Optional
from jose import JWTError, jwt
from pydantic import BaseModel

from .config import get_settings

settings = get_settings()

import logging
logger = logging.getLogger(__name__)

# JWT配置
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.jwt_access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS = settings.jwt_refresh_token_expire_days
JWT_SECRET_KEY = settings.jwt_secret_key

# Token Payload模型
class TokenPayload(BaseModel):
    sub: int
    exp: datetime
    type: str

# ------------------------------ 密码哈希 ------------------------------
def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )

# ------------------------------ JWT令牌 ------------------------------
def create_access_token(user_id: int) -> str:
    """生成访问令牌"""
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # 使用 UNIX 时间戳（int）以确保序列化与解析一致
    payload = {
        # jose 验证子 (sub) 时期望为字符串，使用字符串格式以兼容库验证
        "sub": str(user_id),
        "exp": int(expire.timestamp()),
        "type": "access"
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def create_refresh_token(user_id: int) -> str:
    """生成刷新令牌"""
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "exp": int(expire.timestamp()),
        "type": "refresh"
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def verify_token(token: str, token_type: str = "access") -> Optional[TokenPayload]:
    """验证令牌"""
    try:
        # 去除可能的前后空白
        token = token.strip() if isinstance(token, str) else token
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"verify_exp": True}
        )
        logger.debug(f"JWT payload decoded: {payload}")
        if payload.get("type") != token_type:
            raise JWTError(f"Invalid token type (expected {token_type})")
        # 兼容 exp 的不同格式（int timestamp 或 ISO 字符串）
        exp_val = payload.get("exp")
        if isinstance(exp_val, (int, float)):
            exp_dt = datetime.fromtimestamp(exp_val)
        else:
            try:
                exp_dt = datetime.fromisoformat(str(exp_val))
            except Exception:
                # 最后兜底：尝试将其转换为 float 再解析
                try:
                    exp_dt = datetime.fromtimestamp(float(exp_val))
                except Exception:
                    raise JWTError("Invalid exp format in token")

        sub_val = payload.get("sub")
        try:
            sub_int = int(sub_val)
        except Exception:
            raise JWTError("Invalid sub format in token")

        return TokenPayload(
            sub=sub_int,
            exp=exp_dt,
            type=payload.get("type")
        )
    except ExpiredSignatureError:
        # 令牌已过期；尝试放宽验证（使用配置的时钟偏差）以便在小幅时间不同步下仍能接受
        logger.warning("JWT 过期，尝试使用时钟偏差容忍进行二次验证")
        try:
            # 使用 get_unverified_claims 获取未验证的 payload，避免 jose 在解码时对 sub 做类型验证失败
            unverified = jwt.get_unverified_claims(token)
            logger.debug(f"JWT unverified payload for debug (expired): {unverified}")
            # 手动检查 exp 并允许小幅时钟偏差
            exp_val = unverified.get("exp")
            if isinstance(exp_val, (int, float)):
                exp_ts = float(exp_val)
            else:
                try:
                    exp_ts = float(exp_val)
                except Exception:
                    logger.exception("无法解析 token 中的 exp 字段")
                    return None

            now_ts = datetime.utcnow().timestamp()
            skew = getattr(settings, "jwt_clock_skew_seconds", 60)
            logger.debug(f"now_ts={now_ts}, exp_ts={exp_ts}, skew={skew}")
            if now_ts <= exp_ts + float(skew):
                # 仍在允许的偏差范围内，构建 TokenPayload
                sub_val = unverified.get("sub")
                try:
                    sub_int = int(sub_val)
                except Exception:
                    logger.exception("Invalid sub format in token (expired handling)")
                    return None
                return TokenPayload(sub=sub_int, exp=datetime.fromtimestamp(exp_ts), type=unverified.get("type"))
            else:
                logger.warning("Token expired beyond allowed clock skew")
                return None
        except Exception:
            logger.exception('二次解析已过期 token 失败')
            return None
    except JWTError:
        # 记录详细错误并尝试解码不验证 exp 以便调试
        logger.exception('JWT 验证失败')
        try:
            unverified = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM], options={"verify_exp": False})
            logger.debug(f"JWT unverified payload for debugging: {unverified}")
        except Exception:
            logger.debug("无法解码 token 获取未验证的 payload")
        return None