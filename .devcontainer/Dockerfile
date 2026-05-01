FROM python:3.12-slim

# Quality-of-life defaults for Python in containers.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system packages and Claude Code in a single layer
RUN apt-get update && apt-get install -y \
    curl \
    fonts-ipaexfont \
    libopencv-dev \
    sqlite3 \
    lhasa \
    wget \
    locales \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL https://claude.ai/install.sh | bash

    
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /workspaces
