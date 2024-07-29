#!/bin/bash

# Define container names
CONTAINER1="container1"
CONTAINER2="container2"

install_dependencies() {
    local container=$1
    echo "Installing dependencies in $container..."
    
    docker exec $container bash -c '
        apt-get update &&
        apt-get install -y python3 python3-pip nano &&
        pip3 install --upgrade pip &&
        pip3 install redis
    '
    
    if [ $? -eq 0 ]; then
        echo "Dependencies successfully installed in $container"
    else
        echo "Failed to install dependencies in $container"
    fi
}

# Install dependencies in both containers
install_dependencies $CONTAINER1
install_dependencies $CONTAINER2

# Verify installations
for container in $CONTAINER1 $CONTAINER2; do
    echo "Verifying installations in $container:"
    docker exec $container python3 --version
    docker exec $container pip3 --version
    docker exec $container python3 -c "import redis; print(f'Redis package version: {redis.__version__}')"
    docker exec $container nano --version
done


