FROM python:3.13-slim

WORKDIR /app

# Install cron
RUN apt-get update && apt-get install -y cron libmagic1 && rm -rf /var/lib/apt/lists/*

ENV PIP_ROOT_USER_ACTION=ignore
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . .

# Copy the cron file to the cron.d directory
COPY cronjob /etc/cron.d/cronjob

# Give execution rights on the cron job
RUN chmod 0644 /etc/cron.d/cronjob

# Apply cron job
RUN crontab /etc/cron.d/cronjob

# Create the log file to be able to run tail
RUN touch /var/log/cron.log

EXPOSE 8001

# Run the command on container startup
CMD bash -c "cron && uvicorn main:app --host 0.0.0.0 --port 8001"