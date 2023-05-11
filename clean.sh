#!/usr/bin/env bash

#docker-compose down --rmi all --volumes 
sudo docker-compose down

if [[ -n $(docker ps -a -q) ]]; then
	sudo docker rm -f $(docker ps -a -q)
fi

if [[ -n $(docker volume ls -q) ]]; then
	sudo docker volume rm $(docker volume ls -q)
fi



