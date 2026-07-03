# nl-search 云端部署（Hugging Face Spaces / Render / Fly.io）
# 构建：在仓库根目录执行
#   docker build -f deploy/nl-search/Dockerfile -t nl-flight-search .
FROM python:3.12-slim

WORKDIR /app

COPY scripts /app/scripts
COPY web/nl-search /app/web/nl-search
COPY .cursor/skills/flight-monitor-agent/scripts /app/.cursor/skills/flight-monitor-agent/scripts

RUN pip install --no-cache-dir -r /app/web/nl-search/requirements.txt

ENV NL_SEARCH_HOST=0.0.0.0
ENV NL_SEARCH_PORT=7860
ENV ALLOWED_ORIGINS=*
ENV PYTHONUNBUFFERED=1

EXPOSE 7860

WORKDIR /app/web/nl-search
CMD ["python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7860"]
