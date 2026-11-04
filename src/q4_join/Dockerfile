FROM python:3-alpine

RUN pip3 install pika
WORKDIR /app
COPY src/common common
COPY src/q4_join q4_join

ENTRYPOINT ["python", "-m", "q4_join.main"]