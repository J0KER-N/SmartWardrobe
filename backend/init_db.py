"""简单脚本：初始化数据库（在 `backend` 目录运行此脚本）。

示例：
    cd backend
    python init_db.py
"""
from dotenv import load_dotenv

# 加载 .env
load_dotenv()

from app.database import init_db


def main():
    init_db()
    print("数据库初始化完成（已创建表）。")


if __name__ == "__main__":
    main()
