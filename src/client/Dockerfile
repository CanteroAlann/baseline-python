FROM python:3-alpine
WORKDIR /app
COPY src/common common
COPY src/client client
ENTRYPOINT ["python", "-m", "client.main"]
