FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖（编译时）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv
RUN pip install uv

# 复制依赖文件
COPY pyproject.toml ./
RUN uv sync --frozen --no-dev

# 复制源码
COPY . .

# 开发模式：uv run uvicorn ...
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
