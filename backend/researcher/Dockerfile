FROM python:3.12-slim

# Install curl, nodejs, npm, and other basic dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright dependencies and Chromium browser
RUN playwright install --with-deps chromium

COPY . .

EXPOSE 8000

CMD ["python", "server.py"]
