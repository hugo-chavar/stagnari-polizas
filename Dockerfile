FROM selenium/standalone-chrome:latest

USER root
WORKDIR /app

# First clean up existing sources and install keyring
RUN rm -f /etc/apt/sources.list.d/* && \
    apt-get update -o Acquire::AllowInsecureRepositories=true && \
    apt-get install -y --allow-unauthenticated debian-archive-keyring ca-certificates

# Add all required Debian keys (main + security)
RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys \
    0E98404D386FA1D9 \
    6ED0E7B82643E131 \
    605C66F00D6C9793 \
    54404762BBB6E853 \
    BDE6D2B9216EC7A8

# Configure proper Debian sources (main + updates + security)
RUN echo "deb http://deb.debian.org/debian bullseye main" > /etc/apt/sources.list && \
    echo "deb http://deb.debian.org/debian bullseye-updates main" >> /etc/apt/sources.list && \
    echo "deb http://security.debian.org/debian-security bullseye-security main" >> /etc/apt/sources.list

# Install system dependencies
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