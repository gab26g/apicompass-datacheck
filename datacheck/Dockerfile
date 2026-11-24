FROM python:3.14-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY api.py inventory.py schemas.py operations.py storage.py ./datacheck/
COPY data ./datacheck/data
USER 65534
CMD ["python", "-m", "uvicorn", "datacheck.api:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
