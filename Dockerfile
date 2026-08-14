# ============================================================================
# 多阶段 Dockerfile —— 生产镜像。
#   builder: 装依赖(含构建工具), 产出 .venv
#   runtime: 只拷 .venv + 源码, 不含 uv/构建工具/缓存 -> 体积小、攻击面小
# ============================================================================

# ---------- Stage 1: builder ----------
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# 依赖层: 只拷描述文件, 命中缓存则跳过重装
COPY pyproject.toml uv.lock ./

# --frozen 锁死版本; --no-dev 不装 dev 依赖; --no-install-project 只装依赖不装本项目
# (本项目源码稍后拷贝, 分开可让"改源码"不触发"重装依赖")
RUN uv sync --frozen --no-dev --no-install-project

# ---------- Stage 2: runtime ----------
FROM python:3.12-slim AS runtime

# 非 root 用户运行 —— 容器安全基线, 即使被攻破也不是 root
RUN useradd --create-home --uid 1000 appuser

WORKDIR /app

# 只从 builder 拷过来两样: 装好的 venv + (下面单独拷)源码。
# 构建工具、uv、apt 缓存全留在 builder, 不进最终镜像。
COPY --from=builder /app/.venv /app/.venv

# 源码放 runtime 拷, 保证改源码不必重跑 builder 的依赖层
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

USER appuser

EXPOSE 8000

# liveness: /health 不碰 DB。DB 抖动不应触发容器重启(重启修不了 DB, 只会雪上加霜)
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]