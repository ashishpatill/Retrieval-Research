FROM python:3.14-slim AS base

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

FROM base AS api

EXPOSE 8000
CMD ["uvicorn", "retrieval_research.api:app", "--host", "0.0.0.0", "--port", "8000"]

FROM base as cli

ENTRYPOINT ["python", "-m", "retrieval_research.cli"]

FROM base as worker

CMD ["python", "-m", "retrieval_research.cli", "worker"]
