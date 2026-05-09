FROM python:3.12-slim

# Chromium system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download Chromium at build time so it's baked into the image
RUN python -c "import asyncio; from pyppeteer.chromium_downloader import download_chromium; asyncio.run(download_chromium())"

COPY . .

# Mount your data volume here; defaults to /mtn-proj-data inside the container
ENV MTN_DATA_DIR=/mtn-proj-data

CMD ["python", "main.py"]
