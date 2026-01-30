FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    openssh-client \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory
WORKDIR /repo-trust

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY repo_trust/ repo_trust/
COPY entrypoint.sh .

# Make entrypoint executable
RUN chmod +x /repo-trust/entrypoint.sh

# Set entrypoint
ENTRYPOINT ["/repo-trust/entrypoint.sh"]
