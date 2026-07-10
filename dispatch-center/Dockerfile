FROM python:3.11-slim
RUN pip install --no-cache-dir requests
WORKDIR /app
COPY dispatch_center.py .
EXPOSE 2404
CMD ["python3", "-u", "dispatch_center.py"]
