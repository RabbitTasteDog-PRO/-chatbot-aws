"""로그인 사용자 → 상담 세션 → 메시지 관계를 DB에 저장한다."""
import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class ChatSession(models.Model):
    # UUID 기본값에 함수 자체를 넘겨 상담을 생성할 때마다 새 식별자를 만든다.
    # 식별자와 소유권은 별개이므로 View는 id와 owner를 함께 조건으로 조회한다.
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at', '-pk']


class ChatMessage(models.Model):
    # 이전 예제의 식별자는 데이터 보존용이다. 접근 권한은 conversation.owner로 판단한다.
    session_id = models.CharField(max_length=255, db_index=True, blank=True, default='')
    # 기존 메시지의 소유자를 추측해 연결하지 않는다. 신규 메시지는 반드시 대화에 연결한다.
    conversation = models.ForeignKey(ChatSession, on_delete=models.CASCADE,
                                     related_name='messages', null=True)
    # DB의 human/ai 문자열은 history.py에서 HumanMessage/AIMessage로 변환된다.
    # 같은 content라도 역할이 달라야 모델이 이전 질문과 답변을 구분할 수 있다.
    message_type = models.CharField(max_length=10, choices=[('human', 'Human'), ('ai', 'AI')])
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        # 화면 복원은 전체 기록을 과거→현재 순으로 읽는다. 모델 입력의 20개 제한은 history.py에 있다.
        ordering = ['created_at', 'pk']

    def __str__(self):
        return f'{self.message_type}: {self.content[:30]}'
