# 快速修复指南

本文档提供了项目中发现的关键问题的快速修复方案。

## 🔴 必须立即修复的问题

### 1. 添加数据库事务回滚处理

**问题**: 所有路由中的 `db.commit()` 缺少错误回滚处理

**修复方案**: 在所有数据库操作中添加 try-except 和 rollback

**示例修复** (`backend/app/routers/auth.py`):
```python
@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """用户注册"""
    # 检查手机号是否已存在
    if db.query(User).filter(User.phone == user_data.phone).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该手机号已注册"
        )
    
    try:
        # 创建用户
        hashed_password = get_password_hash(user_data.password)
        new_user = User(
            phone=user_data.phone,
            hashed_password=hashed_password,
            nickname=user_data.nickname
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # 生成令牌
        access_token = create_access_token(new_user.id)
        refresh_token = create_refresh_token(new_user.id)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token
        )
    except Exception as e:
        db.rollback()
        logger.error(f"用户注册失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注册失败，请稍后重试"
        )
```

**需要修复的文件**:
- `backend/app/routers/auth.py`
- `backend/app/routers/wardrobe.py`
- `backend/app/routers/profile.py`
- `backend/app/routers/records.py`
- `backend/app/routers/tryon.py`

---

### 2. 修复 datetime.utcnow() 弃用警告

**问题**: Python 3.12+ 中 `datetime.utcnow()` 已弃用

**修复方案**: 替换为 `datetime.now(timezone.utc)`

**修复步骤**:

1. 在 `backend/app/models.py` 顶部添加导入:
```python
from datetime import datetime, timezone
```

2. 替换所有 `datetime.utcnow()` 为 `datetime.now(timezone.utc)`:
```python
# 修改前
created_at = Column(DateTime, default=datetime.utcnow)
updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# 修改后
created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
```

3. 在 `backend/app/security.py` 中:
```python
from datetime import datetime, timedelta, timezone

# 修改前
expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

# 修改后
expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
```

---

### 3. 添加静态文件服务

**问题**: 上传的图片无法通过 `/uploads/` 路径访问

**修复方案**: 在 `backend/app/main.py` 中添加静态文件中间件

**修复步骤**:

在 `backend/app/main.py` 中添加:
```python
from fastapi.staticfiles import StaticFiles

# 在创建 app 之后，注册路由之前添加
if settings.object_storage_type == "local":
    app.mount("/uploads", StaticFiles(directory=settings.image_storage_path), name="uploads")
```

**注意**: 确保 `settings.image_storage_path` 目录存在，且应用有读取权限。

---

### 4. 修复 N+1 查询问题

**问题**: `backend/app/routers/records.py` 第 88-89 行在循环中查询数据库

**修复方案**: 使用 SQLAlchemy 的预加载

**修复步骤**:

在 `backend/app/routers/records.py` 中:
```python
from sqlalchemy.orm import joinedload

@router.get("/favorites", response_model=List[FavoriteResponse])
def get_favorites(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取收藏列表"""
    offset = (page - 1) * page_size
    favorites = db.query(Favorite).filter(
        Favorite.owner_id == current_user.id
    ).options(
        joinedload(Favorite.tryon_record)  # 预加载关联数据
    ).order_by(Favorite.created_at.desc()).offset(offset).limit(page_size).all()
    
    return favorites
```

---

### 5. 改进刷新 Token 逻辑

**问题**: 刷新 token 时返回旧的 refresh_token，应该生成新的

**修复方案**: 在刷新时生成新的 refresh_token

**修复步骤**:

在 `backend/app/routers/auth.py` 中:
```python
@router.post("/refresh", response_model=TokenResponse)
def refresh_token(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """刷新访问令牌"""
    # 验证刷新令牌
    payload = verify_token(token, token_type="refresh")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="刷新令牌无效或已过期"
        )
    
    # 检查用户是否存在
    user = db.query(User).filter(User.id == payload.sub).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已禁用"
        )
    
    # 生成新的访问令牌和刷新令牌
    new_access_token = create_access_token(user.id)
    new_refresh_token = create_refresh_token(user.id)  # 生成新的刷新令牌
    
    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token  # 返回新的刷新令牌
    )
```

---

## ⚠️ 高优先级修复

### 6. 添加请求频率限制

**安装依赖**:
```bash
pip install slowapi
```

**在 `backend/app/main.py` 中添加**:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 在需要限制的路由上添加装饰器
from slowapi import Limiter, _rate_limit_exceeded_handler

@router.post("/login")
@limiter.limit("5/minute")  # 每分钟最多5次
def login(...):
    ...
```

---

### 7. 添加输入验证

**在 `backend/app/schemas.py` 中添加枚举**:
```python
from enum import Enum

class GarmentCategory(str, Enum):
    TOP = "上衣"
    BOTTOM = "裤子"
    OUTERWEAR = "外套"
    SHOES = "鞋子"
    ACCESSORIES = "配饰"

class Season(str, Enum):
    SPRING = "春"
    SUMMER = "夏"
    AUTUMN = "秋"
    WINTER = "冬"

# 在 GarmentCreate 中使用
class GarmentCreate(BaseModel):
    name: str
    category: GarmentCategory  # 使用枚举
    season: Optional[Season]  # 使用枚举
    ...
```

---

## 📝 其他建议

### 8. 创建 .gitignore 文件

在项目根目录创建 `.gitignore`:
```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
.venv

# 环境变量
.env
.env.local

# 数据库
*.db
*.sqlite
*.sqlite3

# 日志
*.log
logs/

# 上传文件
uploads/
data/

# IDE
.vscode/
.idea/
*.swp
*.swo

# 操作系统
.DS_Store
Thumbs.db

# 测试
.pytest_cache/
.coverage
htmlcov/
```

---

### 9. 添加单元测试

创建 `backend/tests/` 目录并添加基础测试:
```python
# backend/tests/test_auth.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_register():
    response = client.post("/auth/register", json={
        "phone": "13800138000",
        "password": "Test1234",
        "nickname": "测试用户"
    })
    assert response.status_code == 201
    assert "access_token" in response.json()
```

---

## 🚀 实施顺序建议

1. **立即修复** (今天):
   - 添加数据库事务回滚
   - 修复 datetime.utcnow()
   - 添加静态文件服务

2. **本周内**:
   - 修复 N+1 查询
   - 改进刷新 token 逻辑
   - 创建 .gitignore

3. **本月内**:
   - 添加请求频率限制
   - 添加输入验证
   - 添加单元测试







