FROM redis:latest

# Install necessary tools
RUN apt-get update && apt-get install -y \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# Copy the initialization script
COPY setup-cluster.sh /setup-cluster.sh
RUN chmod +x /setup-cluster.sh

# Set the entrypoint to the setup script
ENTRYPOINT ["/setup-cluster.sh"]