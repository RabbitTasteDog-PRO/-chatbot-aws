"""React → JSON 검증 → 사용자 소유권 검사 → DB 저장 순서로 요청을 처리한다."""
import json
from functools import wraps
from django.conf import settings
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.core.exceptions import RequestDataTooBig
from django.db import connection, transaction, IntegrityError, DatabaseError
from django.http import HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.cache import never_cache
from .chat import invoke, ModelNotConfigured
from .forms import SignupForm
from .models import ChatSession, ChatMessage
from .exports import export_conversation, ExportUnavailable


def error(message, status=400, **extra):
    return JsonResponse({'error': message, **extra}, status=status)


def endpoint(methods, authenticated=False):
    """HTTP 메서드와 세션 인증 실패도 HTML 대신 JSON으로 응답한다."""
    def decorate(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if request.method not in methods:
                response = error('허용되지 않은 요청 방식이다.', 405)
                response['Allow'] = ', '.join(methods)
                return response
            if authenticated and not request.user.is_authenticated:
                return error('로그인이 필요하다.', 401)
            return view(request, *args, **kwargs)
        return wrapped
    return decorate


def json_body(request, fields):
    """JSON 객체의 필수 문자열과 길이를 검사한다. 암호는 공백을 제거하지 않는다."""
    if request.content_type != 'application/json':
        raise ValueError('application/json 형식으로 전달한다.')
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError, RequestDataTooBig):
        raise ValueError('올바른 JSON 객체를 전달한다.') from None
    if not isinstance(data, dict):
        raise ValueError('JSON 객체를 전달한다.')
    for field, limit in fields.items():
        value = data.get(field)
        if not isinstance(value, str) or not value or len(value) > limit:
            raise ValueError(f'{field}는 1~{limit}자의 문자열이어야 한다.')
    return data


def optional_json_body(request):
    """본문이 없는 명령도 허용하되, 본문을 보냈다면 JSON 객체인지 검사한다."""
    # CSRF 검사에서 multipart 본문을 이미 읽을 수 있으므로 형식을 먼저 확인한다.
    if request.content_type != 'application/json':
        if request.META.get('CONTENT_LENGTH') not in (None, '', '0'):
            raise ValueError('application/json 형식으로 전달한다.')
        return
    try:
        if request.body:
            json_body(request, {})
    except RequestDataTooBig:
        raise ValueError('요청 본문이 너무 크다.') from None


def user_data(user):
    return {'id': user.pk, 'username': user.username}


def conversation_data(conversation):
    first = conversation.messages.filter(message_type='human').first()
    return {'id': str(conversation.pk), 'title': first.content[:40] if first else '새 상담',
            'created_at': conversation.created_at.isoformat()}


def message_data(message):
    return {'id': message.pk, 'role': message.message_type, 'content': message.content,
            'created_at': message.created_at.isoformat()}


def csrf_failure(request, reason=''):
    return error('보안 토큰이 만료되었거나 없다. 새로고침 후 다시 시도한다.', 403)


def bad_request(request, exception=None):
    return error('올바르지 않은 요청이다.', 400)


def forbidden(request, exception=None):
    return error('접근할 수 없다.', 403)


def not_found(request, exception=None):
    return error('상담 또는 주소를 찾을 수 없다.', 404)


def server_error(request):
    return error('서버가 요청을 처리하지 못했다.', 500)


@endpoint(['GET'])
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
    except DatabaseError:
        return error('DB 연결을 확인한다.', 503)
    return JsonResponse({'status': 'ok', 'database': 'ok'})


@endpoint(['GET'])
def csrf(request):
    return JsonResponse({'csrfToken': get_token(request)})


@endpoint(['GET'])
def me(request):
    return JsonResponse({'user': user_data(request.user) if request.user.is_authenticated else None,
                         'chat_mode': settings.CHATBOT_MODE,
                         's3_export_enabled': bool(settings.S3_EXPORT_BUCKET)})


@endpoint(['POST'])
def signup(request):
    try:
        data = json_body(request, {'username': 150, 'password1': 128, 'password2': 128})
    except ValueError as exc:
        return error(str(exc))
    form = SignupForm(data)
    if not form.is_valid():
        return error('회원가입 입력값을 확인한다.', fields={key: list(values) for key, values in form.errors.items()})
    try:
        # 같은 아이디의 동시 가입은 DB의 UNIQUE 제약으로 마지막에 다시 검사한다.
        with transaction.atomic():
            form.save()
    except IntegrityError:
        return error('이미 사용 중인 아이디이다.', fields={'username': ['다른 아이디를 입력한다.']})
    return JsonResponse({'message': '회원가입을 완료했다. 로그인한다.'}, status=201)


@endpoint(['POST'])
def login(request):
    try:
        data = json_body(request, {'username': 150, 'password': 128})
    except ValueError as exc:
        return error(str(exc))
    user = authenticate(request, username=data['username'], password=data['password'])
    if user is None:
        return error('아이디 또는 비밀번호를 확인한다.', 401)
    auth_login(request, user)
    return JsonResponse({'user': user_data(user)})


@endpoint(['POST'], authenticated=True)
def logout(request):
    try:
        optional_json_body(request)
    except ValueError as exc:
        return error(str(exc))
    auth_logout(request)
    return HttpResponse(status=204)


@endpoint(['GET', 'POST'], authenticated=True)
def conversations(request):
    if request.method == 'POST':
        try:
            optional_json_body(request)
        except ValueError as exc:
            return error(str(exc))
        conversation = ChatSession.objects.create(owner=request.user)
        return JsonResponse({'conversation': conversation_data(conversation)}, status=201)
    return JsonResponse({'conversations': [conversation_data(row) for row in
                                          ChatSession.objects.filter(owner=request.user)]})


@endpoint(['GET', 'DELETE'], authenticated=True)
def conversation_detail(request, conversation_id):
    conversation = ChatSession.objects.filter(pk=conversation_id, owner=request.user).first()
    if conversation is None:
        return not_found(request)
    if request.method == 'DELETE':
        conversation.delete()
        return HttpResponse(status=204)
    return JsonResponse({'conversation': conversation_data(conversation),
                         'messages': [message_data(row) for row in conversation.messages.all()]})


@never_cache
@endpoint(['POST'], authenticated=True)
def conversation_export(request, conversation_id):
    conversation = ChatSession.objects.filter(pk=conversation_id, owner=request.user).first()
    if conversation is None:
        return not_found(request)
    try:
        optional_json_body(request)
        result = export_conversation(conversation)
    except ValueError as exc:
        return error(str(exc))
    except ExportUnavailable as exc:
        return error(str(exc), exc.status)
    return JsonResponse(result)


@endpoint(['POST'], authenticated=True)
def messages(request, conversation_id):
    conversation = ChatSession.objects.filter(pk=conversation_id, owner=request.user).first()
    if conversation is None:
        return not_found(request)
    try:
        data = json_body(request, {'query': 2000})
        query = data['query'].strip()
        if not query:
            raise ValueError('질문을 입력한다.')
    except ValueError as exc:
        return error(str(exc))
    try:
        if settings.CHATBOT_MODE == 'demo':
            answer = ('[Docker 실습 응답] 질문을 받았습니다. 이 답변은 외부 AI를 호출하지 않는 '
                      '고정 응답입니다. 대화가 MySQL에 저장되고 새로고침 후 복원되는지 확인하세요.')
        else:
            answer = invoke(query, conversation, request.user).content
            if not isinstance(answer, str) or not answer.strip():
                raise ValueError('답변이 비어 있다.')
        # API 호출 중 삭제된 대화는 다시 생성하지 않는다. 두 메시지는 함께 저장한다.
        with transaction.atomic():
            locked = ChatSession.objects.select_for_update().get(pk=conversation_id, owner=request.user)
            human = ChatMessage.objects.create(conversation=locked, session_id=str(locked.pk),
                                               message_type='human', content=query)
            ai = ChatMessage.objects.create(conversation=locked, session_id=str(locked.pk),
                                            message_type='ai', content=answer)
    except ChatSession.DoesNotExist:
        return not_found(request)
    except ModelNotConfigured:
        return error('서버에 OPENAI_API_KEY를 설정한다.', 503)
    except Exception:
        # 외부 예외에는 API 키 또는 질문이 포함될 수 있으므로 로깅하거나 반환하지 않는다.
        return error('답변을 받지 못했다. 잠시 후 다시 시도한다.', 502)
    return JsonResponse({'messages': [message_data(human), message_data(ai)],
                         'mode': settings.CHATBOT_MODE}, status=201)
