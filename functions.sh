#!/bin/bash

function install-req (){
    node=$1; shift
    ssh root@fit$node \
        "apt update
         apt install docker-compose -y 
         git clone https://github.com/giovpantaleo/blueprint.git"
}



