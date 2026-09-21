export class ApiError extends Error {
  constructor(message, status = 0, fields = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.fields = fields;
  }
}

async function fetchJson(path, options = {}) {
  let response;
  try {
    response = await fetch(path, {
      credentials: 'same-origin',
      cache: 'no-store',
      ...options,
    });
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new ApiError('서버에 연결하지 못했습니다. 연결을 확인하고 다시 시도해 주세요.');
  }

  if (response.status === 204) return null;

  let data;
  try {
    data = await response.json();
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new ApiError('서버 응답을 확인하지 못했습니다. 잠시 후 다시 시도해 주세요.', response.status);
  }

  if (!response.ok) {
    throw new ApiError(
      typeof data?.error === 'string' ? data.error : '요청을 처리하지 못했습니다. 다시 확인해 주세요.',
      response.status,
      data?.fields || {},
    );
  }
  return data;
}

export async function apiRequest(path, { method = 'GET', body, signal } = {}) {
  const headers = { Accept: 'application/json' };

  // Django는 로그인 시 CSRF 값을 회전시킨다. 변경 요청 직전에 새 값을 받는다.
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method.toUpperCase())) {
    const { csrfToken } = await fetchJson('/api/auth/csrf/', { signal });
    if (!csrfToken) throw new ApiError('보안 확인을 완료하지 못했습니다. 새로고침 후 다시 시도해 주세요.');
    headers['X-CSRFToken'] = csrfToken;
  }
  if (body !== undefined) headers['Content-Type'] = 'application/json';

  return fetchJson(path, {
    method,
    headers,
    signal,
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
}
