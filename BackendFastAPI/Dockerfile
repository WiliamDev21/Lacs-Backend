FROM python:3.11-slim

WORKDIR /app

COPY BackendFastAPI/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY BackendFastAPI /app

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
