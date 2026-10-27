FROM python:3-alpine
WORKDIR /app
ENV PYTHONUNBUFFERED=1
COPY src/common common
COPY src/client client
ENTRYPOINT ["python", "-m", "client.main"]
