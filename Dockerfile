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

# Set directory structure and permissions
RUN mkdir -p /srv/shared_files /srv/db /tmp/pdf /tmp/scr

# Install packages globally (but isolated in container)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

COPY cronjob /etc/cron.d/cronjob
RUN chmod 0644 /etc/cron.d/cronjob && \
    crontab /etc/cron.d/cronjob && \
    touch /var/log/cron.log

EXPOSE 8001
EXPOSE 4444

# Verify uvicorn is installed
RUN which uvicorn && uvicorn --version

# Switch to seluser and run
USER seluser
CMD ["bash", "-c", "cron && uvicorn main:app --host 0.0.0.0 --port 8001"]