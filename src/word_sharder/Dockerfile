FROM python:3-alpine
RUN pip3 install pika
WORKDIR /app
COPY src/common common
COPY src/word_sharder word_sharder
ENTRYPOINT ["python", "-m", "word_sharder.main"]
