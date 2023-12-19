docker build -t telegram-notif --network=host .
docker run -it --rm --net=host --name telegram-notif-container -v "$PWD":/app -w /app telegram-notif python3 notifier.py