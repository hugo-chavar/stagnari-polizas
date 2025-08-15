FROM selenium/standalone-chrome:latest

USER root
WORKDIR /app

# Clean up existing sources and use ONLY Ubuntu repositories
RUN rm -f /etc/apt/sources.list.d/* && \
    echo "deb http://archive.ubuntu.com/ubuntu noble main universe" > /etc/apt/sources.list && \
    echo "deb http://archive.ubuntu.com/ubuntu noble-updates main universe" >> /etc/apt/sources.list && \
    echo "deb http://security.ubuntu.com/ubuntu noble-security main universe" >> /etc/apt/sources.list

# Install system packages using Ubuntu packages
RUN apt-get update && \
    apt-get install -y \
    python3 \
    python3-pip \
    cron \
    libmagic1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create www-data user if it doesn't exist and set directory structure
RUN groupadd -g 33 www-data && \
    useradd -u 33 -g 33 -d /app www-data && \
    mkdir -p /srv/shared_files /tmp/pdf /tmp/scr

# Install packages globally (but isolated in container)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy files and set permissions before switching user
COPY . .

# Set ownership of /app to www-data but keep permissions open for installation
RUN chown -R www-data:www-data /app && \
    chmod -R 755 /app

COPY cronjob /etc/cron.d/cronjob
RUN chmod 0644 /etc/cron.d/cronjob && \
    crontab /etc/cron.d/cronjob && \
    touch /var/log/cron.log

EXPOSE 8001
EXPOSE 4444

# Verify uvicorn is installed
RUN which uvicorn && uvicorn --version

# Final permission fix - ensure www-data can write to needed directories
RUN chown -R www-data:www-data /tmp/pdf /tmp/scr && \
    chmod -R 777 /tmp/pdf /tmp/scr

# Switch to www-data and run (instead of seluser)
USER www-data
CMD ["bash", "-c", "cron && uvicorn main:app --host 0.0.0.0 --port 8001"]