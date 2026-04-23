# AII上下文助手 - Docker镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PYTHONUTF8=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY core/ ./core/
COPY scripts/ ./scripts/
COPY config/ ./config/
COPY .claude/ ./.claude/
COPY demo/ ./demo/
COPY tests/ ./tests/

# 创建必要目录
RUN mkdir -p workflows artifacts

# 设置权限
RUN chmod +x demo/*.py tests/*.py

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from core import StateDB; print('healthy')" || exit 1

# 默认命令
CMD ["python", "demo/demo_phase3.py"]
