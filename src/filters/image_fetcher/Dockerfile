FROM python:3-alpine
RUN pip3 install pika
WORKDIR /app
COPY src/common common
COPY src/filters filters
ENTRYPOINT ["python", "-m", "filters.image_fetcher.main"]