#!/bin/bash
# start.sh
source .venv/bin/activate
export FLASK_ENV=production
export SECRET_KEY="AMTqS1YhniAkSB1jLr78S789wae3mS3CjcM4uFH92Uo="
gunicorn -c gunicorn_config.py app:app