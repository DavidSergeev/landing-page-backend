# Standard AWS Lambda container image pattern: a plain HTTP server (FastAPI/
# uvicorn) fronted by the AWS Lambda Web Adapter extension. Any base image
# works — the Lambda Runtime Interface Client ships inside the adapter binary
# below, so this image also runs unmodified on ECS/EKS/Fargate/EC2 or a
# laptop (see README for `docker run` instructions).
FROM public.ecr.aws/docker/library/python:3.12-slim

# https://github.com/aws/aws-lambda-web-adapter — proxies Lambda Function URL
# invocations (including RESPONSE_STREAM) to the HTTP server started by CMD.
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:1.0.1 /lambda-adapter /opt/extensions/lambda-adapter

WORKDIR /var/task

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src

ENV PORT=8000 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
