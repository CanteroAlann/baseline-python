from collections import defaultdict
from common.article.clean_article import CleanArticle
from common.message_helper import MessageHelper
from common.message import Message
from common.enums import MsgType
from common.coordination import CoordinatorState
from common.message_protocol import internal

class WordSharderNode(MessageHelper):
    def __init__(self, incoming, outgoing_exchange, control):
        super().__init__(incoming, None)
        self.outgoing_exchange = outgoing_exchange
        self.control = control
        # Estado por sesión (cliente): { session_id: CoordinatorState }
        self.sessions = {}
        # Conteo por sesión: { session_id: defaultdict(int) }
        self.counts = {}
        
    def process_message(self, body, ack, nack):
        # Forzamos a deserializar como CleanArticle
        self.handle(internal.deserialize(body, CleanArticle))
        ack()


    def handle(self, message: Message):
        session = message.session_id
        if session not in self.sessions:
            self.sessions[session] = CoordinatorState(outputs={})
            self.counts[session] = defaultdict(int)

        state = self.sessions[session]

        if message.is_article():
            article = message.require_article()
            # article.abstract es un set, ya viene sin stopwords
            for word in article.abstract:
                self.counts[session][word] += 1
            
            # Avisamos al coordinador que terminamos este artículo
            self.control.send(internal.serialize(Message(MsgType.DONE, session, output="output")))
            
        elif message.is_eof():
            state.set_expected_count(message.expected_messages)

        # Si ya recibimos todos los artículos de este cliente
        if state.is_complete():
            # Top 20 global
            top_20 = sorted(self.counts[session].items(), key=lambda x: x[1], reverse=True)[:20]
            
            # Mandamos el resultado al Gateway (query_id=4)
            result_msg = Message(MsgType.QUERY_RESULT, session_id=session, query_id=4, article_id=0, result=top_20)
            self.outgoing_exchange.send(internal.serialize(result_msg), routing_key=session)
            
            # Limpiamos la memoria
            del self.sessions[session]
            del self.counts[session]