#! /usr/bin/env bash

cd /app

: ${DEVELOPMENT:=false}
: ${DEBUG:=false}

if [ "$DEBUG" = true ]
then
  LOG_LEVEL=debug
else
  LOG_LEVEL=info
fi
if [ "$DEVELOPMENT" = true ]
then
  export PIP_ROOT_USER_ACTION=ignore
  export WATCHFILES_FORCE_POLLING=true
  echo "DEVELOPMENT MODE"
  echo "Remove CyCAx Server installed at container build time."
  pip uninstall -y cycax_server
  echo "Install CyCAx Server in editable mode"
  pip install -e .
  echo "Start uvicorn"
  /usr/local/bin/uvicorn cycax_server.main:app --reload --host 0.0.0.0 --port 8765 --log-level ${LOG_LEVEL}
else
  /usr/local/bin/uvicorn cycax_server.main:app --host 0.0.0.0 --port 8765 --log-level ${LOG_LEVEL}
fi
