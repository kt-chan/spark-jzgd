#!/usr/bin/env bash

#docker-compose down --rmi all --volumes 
sudo docker-compose down

if [[ -n $(sudo docker ps -a -q) ]]; then
	sudo docker rm -f $(sudo docker ps -a -q)
fi

if [[ -n $(sudo docker volume ls -q) ]]; then
	sudo docker volume rm $(sudo docker volume ls -q)
fi



