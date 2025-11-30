FROM python:3.11-slim
WORKDIR /app

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    wget \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
# Install Playwright browsers
RUN playwright install chromium
RUN playwright install-deps

COPY app ./app
COPY .env.example ./
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
