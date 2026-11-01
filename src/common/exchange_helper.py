from common.message_protocol import internal


def bind_shards(exchange, routing_prefix, shard_count):
    for shard_id in range(shard_count):
        route = f"{routing_prefix}.{shard_id}"
        exchange.bind_queue(route, route)


def bind_broadcast_queues(exchange, queue_prefix, queue_count):
    for queue_id in range(queue_count):
        exchange.bind_queue(f"{queue_prefix}.{queue_id}", "")


def publisher(exchange, *, mandatory=True):
    def emit(message, route):
        exchange.send(internal.serialize(message), routing_key=route, mandatory=mandatory)
    return emit
