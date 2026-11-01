FROM python:3-alpine
RUN pip3 install pika
WORKDIR /app
COPY src/common common
COPY src/candidate candidate
ENTRYPOINT ["python", "-m", "candidate.main"]
