#!/bin/bash

CONTAINER1="container1"
CONTAINER2="container2"

clone_and_prepare_bird() {
    for i in {1..2}; do
        echo "Cloning and preparing BIRD in container$i..."
        docker exec container$i git clone https://gitlab.nic.cz/labs/bird.git
        docker exec container$i bash -c "cd bird && autoreconf"
    done
}

compile_and_install_bird() {
    for i in {1..2}; do
        echo "Compiling and installing BIRD in container$i..."
        docker exec container$i bash -c "
            cd bird &&
            ./configure &&
            make &&
            make install
        "
    done
}

setup_bird_directories() {
    for container in $CONTAINER1 $CONTAINER2; do
        echo "Setting up BIRD directories in $container..."
        docker exec $container mkdir -p /etc/bird /run/bird
    done
}

copy_bird_configs() {
    echo "Copying BIRD configuration files to containers..."
    docker cp bird1.conf $CONTAINER1:/etc/bird/bird.conf
    docker cp bird2.conf $CONTAINER2:/etc/bird/bird.conf
}

start_bird() {
    for container in $CONTAINER1 $CONTAINER2; do
        echo "Starting BIRD daemon in $container..."
        docker exec $container bird -c /etc/bird/bird.conf -d
    done
}

clone_and_prepare_bird
compile_and_install_bird
setup_bird_directories
copy_bird_configs
start_bird

echo "BIRD setup completed on $CONTAINER1 and $CONTAINER2"
