FROM python:3.12-slim

# Quality-of-life defaults for Python in containers.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system packages and Claude Code in a single layer
RUN apt-get update && apt-get install -y \
    git \
    curl \
    lhasa \
    wget \
    bash-completion \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    # Install Claude Code
    && curl -fsSL https://claude.ai/install.sh | bash 

WORKDIR /workspaces
COPY requirements.txt /workspaces
RUN python -m pip install --upgrade pip && python -m pip install -r requirements.txt
RUN echo 'autoload bashcompinit && bashcompinit' >> ~/.bashrc && echo 'source /usr/share/bash-completion/completions/git' >> ~/.bashrc

    
ENV PATH="/root/.local/bin:$PATH"


