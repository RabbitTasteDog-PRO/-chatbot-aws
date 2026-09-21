"""DB 행을 LangChain 메시지로 변환한다. 인증된 사용자의 대화만 다룬다."""
from django.db import transaction
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import AIMessage, HumanMessage
from .models import ChatMessage, ChatSession


class DatabaseChatMessageHistory(BaseChatMessageHistory):
    def __init__(self, conversation, owner):
        # View의 검사 외에도 저장소 경계에서 소유권을 다시 확인한다.
        self.conversation = ChatSession.objects.get(pk=conversation.pk, owner=owner)
        self.owner = owner

    @property
    def messages(self):
        # @property이므로 history.messages로 접근하지만, 내부에서 실제 SELECT가 실행된다.
        # 최근 메시지 20개를 읽은 뒤 시간순으로 바꾼다. 토큰 20개 또는 대화 20쌍이 아니다.
        rows = list(ChatMessage.objects.filter(
            conversation=self.conversation, conversation__owner=self.owner,
        ).order_by('-created_at', '-pk')[:20])
        # 최신순 [마지막 답변, 마지막 질문, ...]을 뒤집어 원래 대화 순서로 모델에 전달한다.
        # DB 행은 Django 객체이므로 LangChain이 받는 역할별 메시지 객체로 바꾼다.
        return [HumanMessage(content=row.content) if row.message_type == 'human'
                else AIMessage(content=row.content) for row in reversed(rows)]

    def add_messages(self, messages):
        rows = []
        for message in messages:
            if not isinstance(message, (HumanMessage, AIMessage)) or not isinstance(message.content, str):
                raise ValueError('텍스트 human/ai 메시지만 저장한다.')
            rows.append(ChatMessage(
                conversation=self.conversation, session_id=str(self.conversation.pk),
                message_type='human' if isinstance(message, HumanMessage) else 'ai',
                content=message.content,
            ))
        # 위 ChatMessage(...)는 아직 메모리 객체이다. bulk_create가 DB의 실제 행으로 저장한다.
        # 사람·AI 두 메시지가 함께 저장되거나 함께 취소되도록 처리한다.
        with transaction.atomic():
            ChatSession.objects.get(pk=self.conversation.pk, owner=self.owner)
            ChatMessage.objects.bulk_create(rows)

    def clear(self):
        # 이 상담의 메시지만 삭제한다. 상담 자체의 삭제는 View의 conversation.delete()가 맡는다.
        ChatMessage.objects.filter(conversation=self.conversation,
                                   conversation__owner=self.owner).delete()
