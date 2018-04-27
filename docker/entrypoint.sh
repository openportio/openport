#!/usr/bin/env bash
set -ex

openport --register-key $REGISTER_TOKEN
bash -c "$EXTRA_COMMAND"

openport $PORT -R
