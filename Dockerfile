FROM selenium/standalone-chrome:latest

WORKDIR /app

RUN sudo mkdir -p /srv/shared_files && \
    sudo chmod a+rwx /srv/shared_files && \
    mkdir -p /tmp/pdf && \
    chmod -R a+rwx /tmp/pdf && \
    mkdir /tmp/scr && \
    chmod -R a+rwx /tmp/scr

RUN sudo apt-get update && \
    sudo apt-get install -y \
    python3 \
    python3-pip \
    cron \
    libmagic1 \
    && sudo rm -rf /var/lib/apt/lists/*

# Create and activate a new virtual environment
RUN python3 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

COPY cronjob /etc/cron.d/cronjob
RUN sudo chmod 0644 /etc/cron.d/cronjob && \
    sudo crontab /etc/cron.d/cronjob && \
    sudo touch /var/log/cron.log

EXPOSE 8001
EXPOSE 4444

CMD bash -c "cron && uvicorn main:app --host 0.0.0.0 --port 8001"