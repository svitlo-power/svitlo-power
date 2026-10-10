FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared package
COPY ../shared/python/ ./shared/
RUN pip install --no-cache-dir -e ./shared/

# Copy app code
COPY app/ ./app/

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "-m", "app.main"]