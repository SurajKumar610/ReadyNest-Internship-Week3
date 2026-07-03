# Use a lightweight Python base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV PORT=8000
ENV RELOAD=false

# Set working directory
WORKDIR /app

# Copy backend requirements first to leverage Docker cache
COPY backend/requirements.txt /app/backend/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy backend application files
COPY backend/ /app/backend/

# Copy frontend static files
COPY frontend/ /app/frontend/

# Set working directory to the backend so relative paths (data/ and config/) are created inside backend/
WORKDIR /app/backend

# Expose port
EXPOSE 8000

# Run the FastAPI server
CMD ["python", "main.py"]
