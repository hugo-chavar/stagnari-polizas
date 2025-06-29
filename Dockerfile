FROM selenium/standalone-chrome:latest

USER root
WORKDIR /app

# Clean up duplicate apt sources
RUN sudo rm -f /etc/apt/sources.list.d/ubuntu.sources && \
    sudo apt-get update -o Acquire::Check-Valid-Until=false -o Acquire::Check-Date=false

# Install system dependencies
RUN apt-get update && \
    apt-get install -y \
    python3 \
    python3-pip \
    cron \
    libmagic1

# Clean up apt cache
RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create directories with correct permissions
RUN mkdir -p /srv/shared_files /tmp/pdf /tmp/scr && \
    chmod -R 777 /srv/shared_files /tmp/pdf /tmp/scr && \
    chown -R seluser:seluser /app

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