# backend/Dockerfile

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code & shared logic
COPY backend/app ./app
COPY common ./common

# Expose port
EXPOSE 8000

# Run uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
