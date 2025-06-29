FROM selenium/standalone-chrome:latest

WORKDIR /app

RUN mkdir -p /srv/shared_files && chmod a+rwx /srv/shared_files
RUN mkdir -p /tmp/pdf && chmod -R a+rwx /tmp/pdf
RUN mkdir /tmp/scr && chmod -R a+rwx /tmp/scr

RUN sudo apt-get update && \
    sudo apt-get install -y \
    python3.13 \
    python3-pip \
    cron \
    libmagic1 \
    && sudo rm -rf /var/lib/apt/lists/*

ENV PIP_ROOT_USER_ACTION=ignore
COPY requirements.txt .
RUN python3.13 -m pip install --upgrade pip && \
    python3.13 -m pip install --no-cache-dir -r requirements.txt

COPY . .

COPY cronjob /etc/cron.d/cronjob
RUN sudo chmod 0644 /etc/cron.d/cronjob && \
    sudo crontab /etc/cron.d/cronjob && \
    sudo touch /var/log/cron.log

EXPOSE 8001
EXPOSE 4444

CMD bash -c "cron && uvicorn main:app --host 0.0.0.0 --port 8001"