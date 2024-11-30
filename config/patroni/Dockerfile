FROM postgres:11-bullseye

# Install Python and dependencies
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends python3 python3-pip && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --upgrade pip setuptools && \
    pip3 install psycopg2-binary patroni[zookeeper]

# Set up Patroni directories
RUN mkdir -p /data/patroni && \
    chown postgres:postgres /data/patroni && \
    chmod 700 /data/patroni

# Copy configuration and entrypoint
COPY patroni.yml /etc/patroni.yml
COPY entrypoint.sh ./entrypoint.sh

# Switch to the postgres user
USER postgres

ENTRYPOINT ["/bin/sh", "/entrypoint.sh"]