FROM python:3.13-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev

COPY src/ ./src/

ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "src/bot.py"]
