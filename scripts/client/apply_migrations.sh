#!/bin/sh
if [ -e env/bin/alembic ]; then
    env/bin/alembic upgrade head
else
    env/Scripts/alembic upgrade head
fi