import pika

from .middleware import (
    MessageMiddlewareQueue,
    MessageMiddlewareMessageError,
    MessageMiddlewareDisconnectedError,
    MessageMiddlewareCloseError,
)


class MessageMiddlewareQueueRabbitMQ(MessageMiddlewareQueue):
    def __init__(self, host, queue_name, connection=None):
        self.host = host
        self.queue_name = queue_name
        self.owns_connection = connection is None
        self.connection = connection
        self.channel = None
        try:
            if self.connection is None:
                self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=host))
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue=queue_name)
            self.channel.basic_qos(prefetch_count=1)
            self.channel.confirm_delivery()
        except pika.exceptions.AMQPError as exc:
            self.close()
            raise MessageMiddlewareDisconnectedError(str(exc)) from exc

    def create_queue(self, queue_name):
        return MessageMiddlewareQueueRabbitMQ(self.host, queue_name, self.connection)

    def send(self, message):
        try:
            self.channel.basic_publish(
                exchange="",
                routing_key=self.queue_name,
                body=message,
                mandatory=True,
            )
        except pika.exceptions.AMQPConnectionError as exc:
            raise MessageMiddlewareDisconnectedError(str(exc)) from exc
        except pika.exceptions.AMQPError as exc:
            raise MessageMiddlewareMessageError(str(exc)) from exc

    def start_consuming(self, on_message_callback):
        def consume(channel, method, properties, body):
            def ack():
                channel.basic_ack(delivery_tag=method.delivery_tag)

            def nack():
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

            on_message_callback(body, ack, nack)

        try:
            self.channel.basic_consume(
                queue=self.queue_name, on_message_callback=consume, auto_ack=False
            )
            self.channel.start_consuming()
        except pika.exceptions.AMQPConnectionError as exc:
            raise MessageMiddlewareDisconnectedError(str(exc)) from exc
        except pika.exceptions.AMQPError as exc:
            raise MessageMiddlewareMessageError(str(exc)) from exc

    def stop_consuming(self):
        try:
            if self.channel.is_open:
                self.channel.stop_consuming()
        except pika.exceptions.AMQPError as exc:
            raise MessageMiddlewareDisconnectedError(str(exc)) from exc

    def close(self):
        try:
            if self.owns_connection and self.connection is not None:
                if self.connection.is_open:
                    self.connection.close()
            elif self.channel is not None and self.channel.is_open:
                self.channel.close()
        except pika.exceptions.AMQPError as exc:
            raise MessageMiddlewareCloseError(str(exc)) from exc
