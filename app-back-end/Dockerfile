# Build stage
FROM python:3.12-slim AS builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy shared package first
COPY shared/python/ ./shared/python/
RUN pip install --no-cache-dir -e ./shared/python/

# Copy requirements
COPY app-back-end/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY app-back-end/app/ ./app/
COPY app-back-end/run.py .

# Final stage
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy app code
COPY app-back-end/app/ ./app/
COPY app-back-end/run.py .

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "run.py"]