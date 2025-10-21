#!/bin/sh

if [ "$1" == "init" ]; then
    python -m pronotepy.create_login
else
    exec "$@"
fi