#!/usr/bin/env bash
sudo -- sh -c  'docker-compose build'
sudo -- sh -c  'docker-compose up jupyter-notebook -d'

