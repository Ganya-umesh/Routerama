#!/bin/bash

cleanup() {
    echo "Cleaning up existing containers and network..."
    docker stop $(docker ps -aq) 2>/dev/null
    docker rm $(docker ps -aq) 2>/dev/null
    docker network rm mynetwork 2>/dev/null
}

create_network() {
    echo "Creating Docker network..."
    docker network create --subnet=172.19.0.0/16 mynetwork
}

create_containers() {
    echo "Creating and starting containers..."
    for i in {1..2}; do
        docker run --cap-add=NET_ADMIN -d --name container$i --network mynetwork ubuntu:20.04 sleep infinity
    done
}

install_dependencies() {
    for i in {1..2}; do
        echo "Installing dependencies in container$i..."
        docker exec container$i bash -c "
            for attempt in {1..5}; do
                if apt-get update && \
                   apt-get install -y iputils-ping build-essential git autoconf libncurses5-dev libreadline-dev \
                   flex bison; then
                    break
                fi
                echo 'Attempt $attempt failed. Retrying in 5 seconds...'
                sleep 5
            done
        "
    done
}

cleanup
create_network
create_containers
install_dependencies

echo "Containers created and dependencies installed."
