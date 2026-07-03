# 统一 Web 网关（exhaustive-viz + nl-search 同域）
# 构建：在仓库根目录执行
#   docker build -f deploy/web/Dockerfile -t flight-monitor-web .
# 运行：
#   docker run -p 7860:7860 -e ROLLINGGO_API_KEY=xxx flight-monitor-web
FROM python:3.12-slim

WORKDIR /app

COPY scripts /app/scripts
COPY web/nl-search /app/web/nl-search
COPY web/exhaustive-viz /app/web/exhaustive-viz
COPY web/gateway /app/web/gateway
COPY .cursor/skills/flight-monitor-agent/scripts /app/.cursor/skills/flight-monitor-agent/scripts

RUN if [ -L /app/web/exhaustive-viz/data.json ]; then \
      target="$(readlink -f /app/web/exhaustive-viz/data.json)"; \
      rm /app/web/exhaustive-viz/data.json; \
      cp "$target" /app/web/exhaustive-viz/data.json; \
    fi

RUN pip install --no-cache-dir -r /app/web/nl-search/requirements.txt

ENV PYTHONPATH=/app
ENV WEB_ROOT=/nl-search
ENV ALLOWED_ORIGINS=*
ENV PYTHONUNBUFFERED=1

EXPOSE 7860

CMD sh -c "python -m uvicorn web.gateway.server:app --host 0.0.0.0 --port ${PORT:-7860}"
