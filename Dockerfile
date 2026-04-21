FROM python:3.13-slim

WORKDIR /app

COPY . /app

RUN pip install --upgrade pip \
    && pip install uv \
    && uv sync

EXPOSE 8000

CMD ["uv", "run", "--directory", "/app", "-m", "mcp_redmine.server", \
     "--transport", "streamable-http", \
     "--host", "0.0.0.0", \
     "--port", "8000"]
