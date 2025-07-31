FROM selenium/standalone-chrome:latest

USER root
WORKDIR /app

# 1. First establish basic connectivity with temporary insecure method
RUN echo "deb [allow-insecure=yes] http://deb.debian.org/debian bullseye main" > /etc/apt/sources.list && \
    echo "deb [allow-insecure=yes] http://security.debian.org/debian-security bullseye-security main" >> /etc/apt/sources.list

# 2. Install absolutely minimal requirements first
RUN apt-get update -o Acquire::AllowInsecureRepositories=true && \
    apt-get install -y --allow-unauthenticated \
    ca-certificates \
    gnupg \
    wget

# 3. Now properly setup Debian repositories with secure method
RUN wget -qO- https://ftp-master.debian.org/keys/archive-key-11.asc | gpg --dearmor > /usr/share/keyrings/debian-archive-keyring.gpg && \
    wget -qO- https://ftp-master.debian.org/keys/archive-key-11-security.asc | gpg --dearmor > /usr/share/keyrings/debian-security-archive-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] http://deb.debian.org/debian bullseye main" > /etc/apt/sources.list && \
    echo "deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] http://deb.debian.org/debian bullseye-updates main" >> /etc/apt/sources.list && \
    echo "deb [signed-by=/usr/share/keyrings/debian-security-archive-keyring.gpg] http://security.debian.org/debian-security bullseye-security main" >> /etc/apt/sources.list

# 4. Now install all required packages
RUN apt-get update && \
    apt-get install -y \
    python3 \
    python3-pip \
    cron \
    file \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set directory structure and permissions
RUN mkdir -p /srv/shared_files /tmp/pdf /tmp/scr

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