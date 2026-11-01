FROM python:3-alpine
RUN pip3 install pika
WORKDIR /app
COPY src/common common
COPY src/word_count word_count
ENTRYPOINT ["python", "-m", "word_count.main"]
