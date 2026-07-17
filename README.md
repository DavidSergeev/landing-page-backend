# agents

Personal AI assistant backend: a FastAPI app that streams a ReAct agent's
reasoning/answer tokens to the browser as Server-Sent Events (SSE).

## Architecture

Packaged as a Lambda **container image** running the standard
`AWS Lambda -> Lambda Web Adapter -> HTTP server` pattern:

- The app (`src/main.py`) is a plain FastAPI/uvicorn server — no Lambda-specific
  handler code.
- The [AWS Lambda Web Adapter](https://github.com/aws/aws-lambda-web-adapter)
  binary is baked into the image as a Lambda extension (see `Dockerfile`). It
  proxies Function URL invocations to the HTTP server, including
  `RESPONSE_STREAM` mode so Gemini tokens reach the browser as they're produced.
- Because there's nothing Lambda-specific baked into the app or image, the same
  image also runs unmodified on ECS/EKS/Fargate/EC2 or a laptop.

## Local development (no Docker)

```bash
pip install -r requirements.txt
python -m uvicorn src.main:app --reload --port 8000
```

Requires a `.env` file (loaded via `python-dotenv`) with `GOOGLE_API_KEY_PATH`,
`CONFIG_TABLE_NAME`, `MEETINGS_TABLE_NAME`, etc. — see `src/resources/constants.py`.

## Build & run with Docker

```bash
docker build -t landing-page-chat .
docker run --rm -p 8000:8000 --env-file .env landing-page-chat
curl -X POST localhost:8000/ -H 'content-type: application/json' -d '{"query": "hi"}'
```

This is the exact same image that gets deployed to Lambda — useful for
verifying the container before shipping it.

## Deploy to AWS (SAM)

Requires [Docker](https://www.docker.com/) and the
[AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html).

```bash
sam build          # runs `docker build` per template.yaml Metadata
sam deploy --guided # first time; writes samconfig.toml for subsequent `sam deploy`
```

`template.yaml` defines the Lambda (`PackageType: Image`), its Function URL
(streaming, CORS-restricted to the GitHub Pages frontend), and the two
DynamoDB tables (`landing-config`, `landing-meetings`) it reads/writes.
