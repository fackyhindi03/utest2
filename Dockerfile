FROM python:3.10-slim

WORKDIR /app

# Install ffmpeg for remuxing HLS
RUN apt-get update \
  && apt-get install -y ffmpeg curl \
  && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY . .

CMD ["python3", "main.py"]
