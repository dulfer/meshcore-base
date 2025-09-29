FROM python:3.9-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=3000

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY src/ /app/src/
COPY pyproject.toml .

# Create volume for SQLite database
VOLUME /app/data

# Expose port
EXPOSE ${PORT}

# Run the application
CMD ["gunicorn", "--bind", "0.0.0.0:3000", "src.app:app"]