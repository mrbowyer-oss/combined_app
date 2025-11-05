# Optimized Dockerfile for Render deployment
# No Playwright - uses requests + BeautifulSoup instead
 
FROM python:3.11-slim
 
# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
 
# Set working directory
WORKDIR /app
 
# Install system dependencies (minimal - just what's needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
&& apt-get clean \
&& rm -rf /var/lib/apt/lists/*
 
# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
 
# Copy application code
COPY app.py .
 
# Render uses PORT environment variable
# Default to 8000 if not set
ENV PORT=8000
 
# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/ || exit 1
 
# Expose the port (Render will override this with PORT env var)
EXPOSE ${PORT}
 
# Run with gunicorn
# Render will provide PORT environment variable
CMD gunicorn --bind 0.0.0.0:${PORT} --workers 2 --timeout 30 --access-logfile - --error-logfile - app:app
