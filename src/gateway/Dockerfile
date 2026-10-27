FROM python:3-alpine
WORKDIR /app
ENV PYTHONUNBUFFERED=1
COPY src/common common
COPY src/gateway gateway
EXPOSE 5000
CMD ["python", "-m", "gateway.main"]
