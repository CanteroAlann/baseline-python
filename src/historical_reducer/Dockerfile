FROM python:3-alpine
RUN pip3 install pika
WORKDIR /app
COPY src/common common
COPY src/historical_reducer historical_reducer
ENTRYPOINT ["python", "-m", "historical_reducer.main"]
