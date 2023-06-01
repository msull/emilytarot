git pull && docker build . -t etapp:latest && DOMAIN=emilytarot.com docker stack deploy -c docker-compose.yaml emilytarot
