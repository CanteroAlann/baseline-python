FROM python:3-alpine
RUN pip3 install pika
WORKDIR /app
COPY src/common common
COPY src/gateway gateway
EXPOSE 5000
CMD ["python", "-m", "gateway.main"]
