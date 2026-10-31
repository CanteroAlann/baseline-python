import pika

from .middleware import (
    MessageMiddlewareQueue,
    MessageMiddlewareMessageError,
    MessageMiddlewareDisconnectedError,
    MessageMiddlewareCloseError,
)


class MessageMiddlewareQueueRabbitMQ(MessageMiddlewareQueue):
    def __init__(self, host, queue_name, connection=None, exclusive=False):
        self.host = host
        self.queue_name = queue_name
        self.exclusive = exclusive
        self.owns_connection = connection is None
        self.connection = connection
        self.channel = None
        try:
            if self.connection is None:
                self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=host))
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue=queue_name, exclusive=exclusive)
            self.channel.basic_qos(prefetch_count=1)
            self.channel.confirm_delivery()
        except pika.exceptions.AMQPError as exc:
            self.close()
            raise MessageMiddlewareDisconnectedError(str(exc)) from exc

    def create_queue(self, queue_name, exclusive=False):
        return MessageMiddlewareQueueRabbitMQ(
            self.host, queue_name, self.connection, exclusive=exclusive,
        )

    def create_exchange(self, exchange_name):
        return MessageMiddlewareExchangeRabbitMQ(self.connection, exchange_name)

    def bind_exchange(self, exchange_name, routing_key):
        try:
            self.channel.exchange_declare(exchange=exchange_name, exchange_type="topic")
            self.channel.queue_bind(
                queue=self.queue_name, exchange=exchange_name, routing_key=routing_key,
            )
        except pika.exceptions.AMQPError as exc:
            raise MessageMiddlewareDisconnectedError(str(exc)) from exc

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

    def start_consuming(self, on_message_callback, *, include_routing_key=False):
        def consume(channel, method, properties, body):
            def ack():
                channel.basic_ack(delivery_tag=method.delivery_tag)

            def nack():
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

            if include_routing_key:
                on_message_callback(body, ack, nack, method.routing_key)
            else:
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

    def process_events(self):
        try:
            self.connection.process_data_events(time_limit=0)
        except pika.exceptions.AMQPConnectionError as exc:
            raise MessageMiddlewareDisconnectedError(str(exc)) from exc
        except pika.exceptions.AMQPError as exc:
            raise MessageMiddlewareMessageError(str(exc)) from exc

    def close(self):
        try:
            if self.owns_connection and self.connection is not None:
                if self.connection.is_open:
                    self.connection.close()
            elif self.channel is not None and self.channel.is_open:
                if self.exclusive:
                    self.channel.queue_delete(queue=self.queue_name)
                self.channel.close()
        except pika.exceptions.AMQPError as exc:
            raise MessageMiddlewareCloseError(str(exc)) from exc


class MessageMiddlewareExchangeRabbitMQ:
    def __init__(self, connection, exchange_name):
        self.connection = connection
        self.exchange_name = exchange_name
        self.channel = None
        try:
            self.channel = connection.channel()
            self.channel.exchange_declare(exchange=exchange_name, exchange_type="topic")
            self.channel.confirm_delivery()
        except pika.exceptions.AMQPError as exc:
            self.close()
            raise MessageMiddlewareDisconnectedError(str(exc)) from exc

    def bind_queue(self, queue_name, routing_key):
        try:
            self.channel.queue_declare(queue=queue_name)
            self.channel.queue_bind(
                queue=queue_name, exchange=self.exchange_name, routing_key=routing_key,
            )
        except pika.exceptions.AMQPError as exc:
            raise MessageMiddlewareDisconnectedError(str(exc)) from exc

    def send(self, message, routing_key, mandatory=True):
        try:
            self.channel.basic_publish(
                exchange=self.exchange_name, routing_key=routing_key,
                body=message, mandatory=mandatory,
            )
        except pika.exceptions.AMQPConnectionError as exc:
            raise MessageMiddlewareDisconnectedError(str(exc)) from exc
        except pika.exceptions.AMQPError as exc:
            raise MessageMiddlewareMessageError(str(exc)) from exc

    def close(self):
        try:
            if self.channel is not None and self.channel.is_open:
                self.channel.close()
        except pika.exceptions.AMQPError as exc:
            raise MessageMiddlewareCloseError(str(exc)) from exc
