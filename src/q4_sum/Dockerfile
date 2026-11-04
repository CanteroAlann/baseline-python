FROM python:3-alpine

RUN pip3 install pika
WORKDIR /app
COPY src/common common
COPY src/q4_sum q4_sum

ENTRYPOINT ["python", "-m", "q4_sum.main"]