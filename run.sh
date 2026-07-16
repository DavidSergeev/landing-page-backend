#!/bin/bash
# Startup command for the AWS Lambda Web Adapter (zip deployment).
# The adapter execs this script (see template.yaml Handler + AWS_LAMBDA_EXEC_WRAPPER)
# instead of invoking a Python handler directly, then proxies HTTP traffic to it.
PATH=$PATH:$LAMBDA_TASK_ROOT/bin \
PYTHONPATH=$PYTHONPATH:/opt/python:$LAMBDA_RUNTIME_DIR \
exec python -m uvicorn --port="$PORT" src.main:app
