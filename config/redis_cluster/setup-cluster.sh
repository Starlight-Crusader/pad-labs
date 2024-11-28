#!/bin/bash
set -e

# Wait for all Redis nodes to be ready
wait_for_redis_nodes() {
    local nodes=("ud-redis-node-1" "ud-redis-node-2" "ud-redis-node-3" 
                 "ud-redis-node-4" "ud-redis-node-5" "ud-redis-node-6")
    
    for node in "${nodes[@]}"; do
        echo "Waiting for $node to be ready..."
        while ! redis-cli -h "$node" ping &> /dev/null; do
            echo "Waiting for $node to respond..."
            sleep 2
        done
        echo "$node is ready."
    done
}

# Check if cluster is already initialized
is_cluster_initialized() {
    redis-cli --cluster check ud-redis-node-1:6379 2>&1 | grep -q "All 16384 slots covered"
}

# Main cluster initialization function
initialize_cluster() {
    echo "Initializing Redis Cluster..."
    
    redis-cli --cluster create \
        ud-redis-node-1:6379 \
        ud-redis-node-2:6379 \
        ud-redis-node-3:6379 \
        ud-redis-node-4:6379 \
        ud-redis-node-5:6379 \
        ud-redis-node-6:6379 \
        --cluster-replicas 1 \
        --cluster-yes
}

# Main execution
main() {
    # Wait for all nodes to be ready
    wait_for_redis_nodes

    # Check if cluster is already initialized
    # if is_cluster_initialized; then
    #     echo "Redis Cluster is already initialized. Exiting."
    #     exit 0
    # fi

    # Initialize the cluster
    initialize_cluster

    # Verify cluster initialization
    if is_cluster_initialized; then
        echo "Redis Cluster successfully initialized!"
        exit 0
    else
        echo "Redis Cluster initialization failed!"
        exit 1
    fi
}

# Run the main function
main