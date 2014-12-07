#!/bin/sh
env/bin/alembic revision --autogenerate
git add alembic/versions/*.py
