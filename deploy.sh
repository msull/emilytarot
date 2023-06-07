source prod.env.sh
echo $DOMAIN
git pull && docker build . -t emilytarot:latest && docker stack deploy -c docker-compose.prod.yaml emilytarot && docker service update emilytarot_emilytarot --force

docker ps
