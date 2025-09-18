# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Install system dependencies for UPnP
RUN apt-get update && apt-get install -y \
    libminiupnpc-dev \
    && rm -rf /var/lib/apt/lists/*

# Create directories for logs and data
RUN mkdir -p /usr/src/app/logs /usr/src/app/ports_data

# Copy requirements first for better caching
COPY requirements.txt ./

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /usr/src/app
COPY app.py wsgi.py ./
COPY templates templates/
COPY static static/

# Create non-root user for security
RUN useradd -r -s /bin/false upnpuser && \
    chown -R upnpuser:upnpuser /usr/src/app

# Switch to non-root user
USER upnpuser

# Make port available to the world outside this container
EXPOSE $PORT

# Define environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV FLASK_RUN_HOST=0.0.0.0
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:$PORT/health')" || exit 1

# Run app using gunicorn for production
CMD gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 60 --access-logfile - --error-logfile - wsgi:app