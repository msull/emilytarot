source prod.env.sh
echo $DOMAIN
git pull && docker build . -t emilytarot:latest && docker stack deploy -c docker-compose.yaml emilytarot
