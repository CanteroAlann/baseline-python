FROM python:3.11-slim

WORKDIR /app
COPY src/common common
COPY src/q3_shared_words q3_shared_words
RUN pip install pika

ENV PYTHONPATH=/app
ENTRYPOINT ["python", "-m", "q3_shared_words.main"]
