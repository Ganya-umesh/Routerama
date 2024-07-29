#!/bin/bash

setup_redis() {
    echo "Setting up Redis container..."
    docker run -d --name redis --network mynetwork redis:alpine
}

install_redis_tools() {
    for i in {1..2}; do
        echo "Installing Redis tools in container$i..."
        docker exec container$i bash -c "
            apt-get update && apt-get install -y redis-tools
        "
    done
}

setup_redis
install_redis_tools

echo "Redis setup complete."

