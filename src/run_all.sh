#!/bin/sh

celery -A tasks.celery_tasks worker -c 1 --loglevel=INFO > /dev/null 2>&1 &

# check if the process is running for 5 seconds every 1 second

if celery -A tasks.celery_tasks status
then
    echo "Celery is running"
else
    echo "Celery is not running"
fi

