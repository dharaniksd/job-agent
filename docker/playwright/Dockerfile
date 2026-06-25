FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /app
RUN pip install playwright httpx
RUN playwright install chromium

COPY . .
CMD ["python", "worker.py"]
