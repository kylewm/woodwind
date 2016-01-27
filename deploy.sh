#!/bin/bash

REMOTE_USER=kmahan
HOST=orin.kylewm.com
REMOTE_PATH=/srv/www/kylewm.com/woodwind

ssh $REMOTE_USER@$HOST bash -c "'

set -x
cd $REMOTE_PATH

git pull origin master \
&& source venv/bin/activate \
&& pip install --upgrade -r requirements.txt \
&& sudo restart woodwind

'"
