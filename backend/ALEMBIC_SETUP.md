# Alembic 迁移目录设置

## 问题

运行 `alembic revision --autogenerate` 时出现错误：
```
FileNotFoundError: [Errno 2] No such file or directory: '...\\alembic\\versions\\...'
```

## 原因

Alembic 需要在 `alembic/versions/` 目录中存储迁移脚本，但该目录不存在。

## 解决方案

已创建以下目录和文件：

1. **alembic/versions/** - 迁移脚本存储目录
2. **alembic/versions/__init__.py** - Python 包标识文件

## 现在可以运行

```bash
# 创建初始迁移
alembic revision --autogenerate -m "Initial migration"

# 执行迁移
alembic upgrade head
```

## 目录结构

```
alembic/
├── env.py              # Alembic 环境配置
├── script.py.mako      # 迁移脚本模板
└── versions/           # 迁移脚本目录
    ├── __init__.py
    └── [迁移文件].py   # 自动生成的迁移文件
```

## 注意事项

- `alembic/versions/` 目录应该被提交到版本控制系统
- 不要手动编辑已生成的迁移文件（除非必要）
- 每次数据库模型变更后，运行 `alembic revision --autogenerate` 生成新的迁移

