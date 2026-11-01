from common.article import CleanArticle
from common.coordination import non_negative
from common.enums import MsgType
from common.message import Message
from common.message_protocol import internal


def shard_for(article_id, shard_count):
    non_negative(article_id, "article_id")
    return article_id % shard_count


class WordCountNode:
    def __init__(self, incoming, outgoing, control, *, branch, shard_count):
        if branch not in ("historical", "candidate") or shard_count < 1:
            raise ValueError("Expected a Q5 branch and a positive shard count")
        self.input_queue = incoming
        self.output_queue = outgoing
        self.control_queue = control
        self.branch = branch
        self.shard_count = shard_count

    def process_message(self, body, ack, nack):
        message = internal.deserialize(body, CleanArticle)
        if message.is_article():
            output = self.process_article(message)
            control = Message(MsgType.DONE, message.session_id, output=output)
        elif message.is_eof():
            control = Message(MsgType.INPUT_EOF, message.session_id,
                              expected_messages=message.expected_messages)
        else:
            raise ValueError("Expected ARTICLE_RECORD or EOF_RECORDS")
        self.control_queue.send(internal.serialize(control))
        ack()

    def process_article(self, message: Message) -> str:
        article = message.require_article()
        if not isinstance(article, CleanArticle):
            raise ValueError("Q5 word count expects a preprocessed article")
        shard_id = shard_for(message.article_id, self.shard_count)
        output = f"q5.{self.branch}.{shard_id}"
        data = Message(MsgType.WORD_COUNT, message.session_id, article_id=message.article_id,
                       shard_id=shard_id,
                       word_count=article.abstract_word_count,
                       url=article.url if self.branch == "candidate" else None)
        self.output_queue.send(internal.serialize(data), routing_key=output)
        return output

    def start(self):
        self.input_queue.start_consuming(self.process_message)
