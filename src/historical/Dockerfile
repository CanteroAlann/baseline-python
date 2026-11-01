FROM python:3-alpine
RUN pip3 install pika
WORKDIR /app
COPY src/common common
COPY src/historical historical
ENTRYPOINT ["python", "-m", "historical.main"]
