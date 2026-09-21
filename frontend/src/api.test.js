import test from 'node:test';
import assert from 'node:assert/strict';
import { ApiError, apiRequest } from './api.js';

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

test('조회 요청은 같은 출처의 세션 쿠키를 사용한다', async (t) => {
  const fetch = t.mock.method(globalThis, 'fetch', async () => jsonResponse({ user: null, chat_mode: 'demo' }));
  const result = await apiRequest('/api/auth/me/');
  assert.equal(result.chat_mode, 'demo');
  assert.equal(fetch.mock.callCount(), 1);
  assert.equal(fetch.mock.calls[0].arguments[0], '/api/auth/me/');
  assert.equal(fetch.mock.calls[0].arguments[1].credentials, 'same-origin');
});

test('로그인 이후 변경 요청은 회전된 CSRF 값을 새로 받아 보낸다', async (t) => {
  let csrfCalls = 0;
  const requests = [];
  t.mock.method(globalThis, 'fetch', async (path, options) => {
    requests.push({ path, options });
    if (path === '/api/auth/csrf/') return jsonResponse({ csrfToken: `test-csrf-${++csrfCalls}` });
    if (path === '/api/auth/login/') return jsonResponse({ user: { id: 1, username: 'student' } });
    return jsonResponse({ conversation: { id: 'test-conversation' } }, 201);
  });
  await apiRequest('/api/auth/login/', { method: 'POST', body: { username: 'student', password: 'test-password' } });
  await apiRequest('/api/conversations/', { method: 'POST' });
  assert.equal(csrfCalls, 2);
  assert.equal(requests[1].options.headers['X-CSRFToken'], 'test-csrf-1');
  assert.equal(requests[3].options.headers['X-CSRFToken'], 'test-csrf-2');
  assert.equal(requests[1].options.headers['Content-Type'], 'application/json');
  assert.deepEqual(JSON.parse(requests[1].options.body), { username: 'student', password: 'test-password' });
});

test('입력 오류의 상태 코드와 필드별 설명을 유지한다', async (t) => {
  t.mock.method(globalThis, 'fetch', async (path) => path.endsWith('/csrf/')
    ? jsonResponse({ csrfToken: 'test-csrf' })
    : jsonResponse({ error: '입력값을 확인해 주세요.', fields: { username: ['이미 사용 중인 아이디입니다.'] } }, 400));
  await assert.rejects(apiRequest('/api/auth/signup/', { method: 'POST', body: {} }), (error) => {
    assert.ok(error instanceof ApiError);
    assert.equal(error.status, 400);
    assert.deepEqual(error.fields.username, ['이미 사용 중인 아이디입니다.']);
    return true;
  });
});

test('삭제 성공의 빈 204 응답을 JSON으로 해석하지 않는다', async (t) => {
  t.mock.method(globalThis, 'fetch', async (path) => path.endsWith('/csrf/')
    ? jsonResponse({ csrfToken: 'test-csrf' })
    : new Response(null, { status: 204 }));
  assert.equal(await apiRequest('/api/conversations/test-id/', { method: 'DELETE' }), null);
});

test('프록시 HTML 오류 본문을 사용자에게 노출하지 않는다', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => new Response('<html>internal proxy detail</html>', { status: 502 }));
  await assert.rejects(apiRequest('/api/auth/me/'), (error) => {
    assert.equal(error.status, 502);
    assert.equal(error.message.includes('internal proxy'), false);
    assert.match(error.message, /서버 응답/);
    return true;
  });
});

test('CSRF 토큰이 없으면 변경 요청을 전송하지 않는다', async (t) => {
  const fetch = t.mock.method(globalThis, 'fetch', async () => jsonResponse({}));
  await assert.rejects(apiRequest('/api/auth/logout/', { method: 'POST' }), /보안 확인/);
  assert.equal(fetch.mock.callCount(), 1);
});
