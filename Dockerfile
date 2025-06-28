FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y cron libmagic1 && rm -rf /var/lib/apt/lists/*

ENV PIP_ROOT_USER_ACTION=ignore
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . .

COPY cronjob /etc/cron.d/cronjob

RUN chmod 0644 /etc/cron.d/cronjob

RUN crontab /etc/cron.d/cronjob

RUN touch /var/log/cron.log

EXPOSE 8001

CMD bash -c "cron && uvicorn main:app --host 0.0.0.0 --port 8001"