"""DB 대화를 UTF-8 TXT로 변환하고 비공개 S3 객체의 임시 다운로드 주소를 만든다."""
import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings
from django.db.models.functions import Length
from django.utils import timezone

MAX_EXPORT_BYTES = 1024 * 1024
MAX_EXPORT_MESSAGES = 500
DOWNLOAD_EXPIRES_IN = 600


class ExportUnavailable(Exception):
    def __init__(self, message, status=503):
        super().__init__(message)
        self.status = status


def conversation_text(conversation):
    """시간순 메시지를 읽으며 크기를 제한한다. 화면에서 받은 대화 내용은 사용하지 않는다."""
    # MySQL 드라이버는 iterator()도 결과를 버퍼링할 수 있다. 본문 대신 길이만
    # 최대 501개 조회하여 메시지 수와 최소 바이트 크기를 먼저 검사한다.
    messages = conversation.messages.order_by('created_at', 'pk')
    sizes = list(messages.annotate(content_length=Length('content'))
                 .values_list('pk', 'content_length')[:MAX_EXPORT_MESSAGES + 1])
    if len(sizes) > MAX_EXPORT_MESSAGES:
        raise ValueError('대화 내보내기는 최대 500개 메시지까지 가능하다.')
    if not sizes:
        raise ValueError('저장할 대화가 없다. 먼저 질문과 답변을 만든다.')
    if sum(length for _, length in sizes) > MAX_EXPORT_BYTES:
        raise ValueError('대화 파일은 1 MiB 이하만 저장할 수 있다.')
    # 기존 메시지는 수정하지 않는 앱이다. 검사 후 새로 추가된 메시지는 이번
    # 내보내기에 섞지 않고, 확인한 메시지 ID에 대해서만 본문을 조회한다.
    selected = messages.filter(pk__in=[pk for pk, _ in sizes])[:MAX_EXPORT_MESSAGES]
    output = bytearray(f'상담 기록: {conversation.pk}\n\n'.encode('utf-8'))
    for message in selected:
        role = {'human': '사용자', 'ai': '챗봇'}.get(message.message_type, '메시지')
        timestamp = timezone.localtime(message.created_at).isoformat(timespec='seconds')
        # 한 메시지가 이미 제한을 넘으면 UTF-8 복사본을 만들기 전에 거부한다.
        if len(message.content) > MAX_EXPORT_BYTES:
            raise ValueError('대화 파일은 1 MiB 이하만 저장할 수 있다.')
        block = f'[{timestamp}] {role}\n{message.content}\n\n'.encode('utf-8')
        if len(output) + len(block) > MAX_EXPORT_BYTES:
            raise ValueError('대화 파일은 1 MiB 이하만 저장할 수 있다.')
        output.extend(block)
    return bytes(output)


def export_conversation(conversation):
    if not settings.S3_EXPORT_BUCKET:
        raise ExportUnavailable('서버에 S3_EXPORT_BUCKET을 설정한다.')
    body = conversation_text(conversation)
    filename = f'conversation-{conversation.pk}.txt'
    key = f'day2/chat-exports/{conversation.owner_id}/{conversation.pk}.txt'
    try:
        # 키를 코드에 전달하지 않는다. EC2에서는 인스턴스 역할의 임시 자격증명을 사용한다.
        s3 = boto3.client('s3', region_name=settings.AWS_DEFAULT_REGION,
                          config=Config(signature_version='s3v4', connect_timeout=3,
                                        read_timeout=10, retries={'total_max_attempts': 2}))
        s3.put_object(Bucket=settings.S3_EXPORT_BUCKET, Key=key, Body=body,
                      ContentType='text/plain; charset=utf-8',
                      ContentDisposition=f'attachment; filename="{filename}"',
                      CacheControl='private, no-store')
        download_url = s3.generate_presigned_url(
            'get_object', Params={'Bucket': settings.S3_EXPORT_BUCKET, 'Key': key},
            ExpiresIn=DOWNLOAD_EXPIRES_IN)
    except (BotoCoreError, ClientError):
        # AWS 예외에는 내부 리소스 정보가 포함될 수 있으므로 원문을 응답하지 않는다.
        raise ExportUnavailable('S3 저장에 실패했다. 서버의 버킷·역할 권한·네트워크를 확인한다.', 502) from None
    return {'download_url': download_url, 'filename': filename, 'expires_in': DOWNLOAD_EXPIRES_IN}
