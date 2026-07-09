FROM python:3.11-slim

RUN pip install --no-cache-dir requests

WORKDIR /app
COPY gateway.py .

CMD ["python3", "-u", "gateway.py"]
