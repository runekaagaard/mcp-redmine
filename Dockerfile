FROM python:3.13-slim

WORKDIR /app

COPY . /app

RUN pip install --upgrade pip \
    && pip install uv \
    && uv sync

CMD ["uv", "run", "--directory", "/app", "-m", "mcp_redmine.server", "main"]