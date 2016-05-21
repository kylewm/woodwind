#!/bin/bash

REMOTE_USER=kmahan
HOST=orin.kylewm.com

ssh -t $REMOTE_USER@$HOST bash -c "'

set -x

sudo tail -n 60 -f /var/log/upstart/woodwind.log
'"
