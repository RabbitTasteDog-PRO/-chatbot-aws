import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError, apiRequest } from './api.js';
import Icon from './Icons.jsx';

const suggestions = [
  { label: '직무를 탐색하고 싶어요', query: '개발자와 데이터 분석가의 업무 차이와 필요한 역량을 알려 주세요.' },
  { label: '학습 순서가 궁금해요', query: 'Python을 배운 뒤 백엔드 개발자가 되려면 어떤 순서로 공부하면 좋을까요?' },
  { label: '프로젝트를 준비해요', query: 'AI 개발자 취업을 준비할 때 포트폴리오에 어떤 내용을 담으면 좋을까요?' },
  { label: '@@@@@@@@@ 자동화 @@@@@@@@@', query: 'AI 개발자 취업을 준비할 때 포트폴리오에 어떤 내용을 담으면 좋을까요?' },
  { label: '@@@@@@@ 된냐 @@@@@@@@@@@', query: 'AI 개발자 취업을 준비할 때 포트폴리오에 어떤 내용을 담으면 좋을까요?' },
];

function ModeNotice({ mode }) {
  if (mode !== 'demo') return null;
  return <p className="mode-notice"><span className="mode-dot" />Docker 실습 모드 · 실제 AI 응답이 아닙니다</p>;
}

function Brand({ compact = false }) {
  return <div className={`brand ${compact ? 'brand-compact' : ''}`}><span className="brand-mark"><Icon name="compass" size={26} /></span><span>길잡이<small>IT 커리어 상담</small></span></div>;
}

function fieldText(fields, name) {
  const value = fields[name];
  if (Array.isArray(value)) return value.filter((item) => typeof item === 'string').join(' ');
  return typeof value === 'string' ? value : '';
}

function AuthForm({ mode, onAuthenticated, sessionNotice }) {
  const [view, setView] = useState('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [fields, setFields] = useState({});
  const [notice, setNotice] = useState('');
  const signingUp = view === 'signup';

  function changeView(next) {
    setView(next);
    setPassword('');
    setConfirmation('');
    setError('');
    setFields({});
    setNotice('');
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (busy) return;
    setError('');
    setFields({});
    setNotice('');
    if (signingUp && password !== confirmation) {
      setFields({ password2: ['비밀번호가 일치하지 않습니다.'] });
      return;
    }
    setBusy(true);
    try {
      if (signingUp) {
        await apiRequest('/api/auth/signup/', {
          method: 'POST',
          body: { username: username.trim(), password1: password, password2: confirmation },
        });
        setView('login');
        setPassword('');
        setConfirmation('');
        setNotice('회원가입이 완료되었습니다. 새 계정으로 로그인해 주세요.');
      } else {
        await apiRequest('/api/auth/login/', {
          method: 'POST',
          body: { username: username.trim(), password },
        });
        await onAuthenticated();
      }
    } catch (failure) {
      setError(failure.message);
      setFields(failure.fields || {});
    } finally {
      setBusy(false);
    }
  }

  const passwordField = signingUp ? 'password1' : 'password';
  return (
    <main className="auth-page">
      <section className="auth-story" aria-label="서비스 소개">
        <Brand />
        <div className="auth-intro">
          <p className="eyebrow">나의 다음 단계를 찾는 시간</p>
          <h1>어떤 일을 할지,<br />어떻게 준비할지.</h1>
          <p>막연했던 IT 진로 고민을<br />하나씩 구체적인 계획으로 정리해 보세요.</p>
          <div className="story-topics"><span>직무 탐색</span><span>학습 계획</span><span>취업 준비</span></div>
        </div>
        <p className="story-footnote">지금의 경험에서, 다음 가능성으로.</p>
      </section>
      <section className="auth-panel">
        <div className="auth-form-wrap">
          <p className="eyebrow">다시 이어가는 나의 상담</p>
          <h2>{signingUp ? '상담을 시작해 볼까요?' : '만나서 반갑습니다.'}</h2>
          <p className="muted auth-description">내 계정으로 대화를 저장하고 언제든 이어갈 수 있습니다.</p>
          <div className="auth-tabs" role="tablist" aria-label="계정 메뉴">
            <button type="button" id="login-tab" role="tab" aria-selected={!signingUp} aria-controls="auth-form" disabled={busy} onClick={() => changeView('login')}>로그인</button>
            <button type="button" id="signup-tab" role="tab" aria-selected={signingUp} aria-controls="auth-form" disabled={busy} onClick={() => changeView('signup')}>회원가입</button>
          </div>
          {sessionNotice && <p className="feedback feedback-error" role="alert">{sessionNotice}</p>}
          {notice && <p className="feedback feedback-success" role="status">{notice}</p>}
          {error && <p className="feedback feedback-error" role="alert">{error}</p>}
          <form id="auth-form" role="tabpanel" aria-labelledby={signingUp ? 'signup-tab' : 'login-tab'} onSubmit={handleSubmit}>
            <label htmlFor="username">아이디</label>
            <input id="username" name="username" autoComplete="username" placeholder="아이디를 입력해 주세요" value={username} onChange={(event) => setUsername(event.target.value)} maxLength={150} required disabled={busy} aria-invalid={Boolean(fieldText(fields, 'username'))} aria-describedby={fieldText(fields, 'username') ? 'username-error' : undefined} />
            {fieldText(fields, 'username') && <p className="field-error" id="username-error">{fieldText(fields, 'username')}</p>}
            <label htmlFor="password">비밀번호</label>
            <input id="password" name={passwordField} type="password" autoComplete={signingUp ? 'new-password' : 'current-password'} placeholder="비밀번호를 입력해 주세요" value={password} onChange={(event) => setPassword(event.target.value)} required disabled={busy} aria-invalid={Boolean(fieldText(fields, passwordField))} aria-describedby={fieldText(fields, passwordField) ? 'password-error' : undefined} />
            {fieldText(fields, passwordField) && <p className="field-error" id="password-error">{fieldText(fields, passwordField)}</p>}
            {signingUp && <><label htmlFor="confirmation">비밀번호 확인</label><input id="confirmation" name="password2" type="password" autoComplete="new-password" placeholder="비밀번호를 다시 입력해 주세요" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} required disabled={busy} aria-invalid={Boolean(fieldText(fields, 'password2'))} aria-describedby={fieldText(fields, 'password2') ? 'confirmation-error' : undefined} />{fieldText(fields, 'password2') && <p className="field-error" id="confirmation-error">{fieldText(fields, 'password2')}</p>}</>}
            <button className="button button-primary auth-submit" type="submit" disabled={busy}>{busy ? '확인하고 있습니다…' : signingUp ? '회원가입' : '로그인하고 상담하기'}{!busy && <Icon name="arrow" />}</button>
          </form>
          <ModeNotice mode={mode} />
        </div>
      </section>
    </main>
  );
}

function displayDate(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '' : new Intl.DateTimeFormat('ko-KR', { month: 'long', day: 'numeric' }).format(date);
}

function Message({ role, content, pending = false }) {
  const human = role === 'human';
  return (
    <article className={`message ${human ? 'message-human' : 'message-ai'} ${pending ? 'message-pending' : ''}`}>
      {!human && <span className="assistant-avatar"><Icon name="compass" size={21} /></span>}
      <div className="message-body"><p className="message-author">{human ? '나' : '길잡이'}</p><div className="message-content">{content}</div></div>
    </article>
  );
}

function DeleteDialog({ conversation, busy, onCancel, onConfirm }) {
  const ref = useRef(null);
  useEffect(() => {
    const dialog = ref.current;
    dialog.showModal();
    return () => dialog.close();
  }, []);
  return (
    <dialog ref={ref} className="delete-dialog" aria-labelledby="delete-title" aria-describedby="delete-description" onCancel={(event) => { event.preventDefault(); if (!busy) onCancel(); }}>
      <span className="dialog-icon"><Icon name="trash" size={26} /></span>
      <h2 id="delete-title">상담 기록을 삭제할까요?</h2>
      <p className="delete-conversation-title">{conversation.title || '새 상담'}</p>
      <p className="muted" id="delete-description">이 상담의 모든 메시지가 삭제됩니다.<br />삭제한 기록은 복구할 수 없습니다.</p>
      <div className="dialog-actions"><button className="button button-secondary" type="button" onClick={onCancel} disabled={busy} autoFocus>취소</button><button className="button button-danger" type="button" onClick={onConfirm} disabled={busy}>{busy ? '삭제하고 있습니다…' : '삭제하기'}</button></div>
    </dialog>
  );
}

function Workspace({ user, mode, exportEnabled, onLogout, onSessionExpired }) {
  const [conversations, setConversations] = useState([]);
  const [listLoading, setListLoading] = useState(true);
  const [listError, setListError] = useState('');
  const [listAttempt, setListAttempt] = useState(0);
  const [active, setActive] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [error, setError] = useState('');
  const [draft, setDraft] = useState('');
  const [pendingQuestion, setPendingQuestion] = useState('');
  const [action, setAction] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [exportResult, setExportResult] = useState(null);
  const activeId = useRef(null);
  const loadController = useRef(null);
  const textarea = useRef(null);
  const endOfMessages = useRef(null);
  const busy = Boolean(action);

  const reportError = useCallback((failure, setter = setError) => {
    if (failure.name === 'AbortError') return;
    if (failure.status === 401) { onSessionExpired(); return; }
    setter(failure.message);
  }, [onSessionExpired]);

  useEffect(() => {
    const controller = new AbortController();
    setListLoading(true);
    setListError('');
    apiRequest('/api/conversations/', { signal: controller.signal })
      .then((data) => { if (!controller.signal.aborted) setConversations(data.conversations); })
      .catch((failure) => reportError(failure, setListError))
      .finally(() => { if (!controller.signal.aborted) setListLoading(false); });
    return () => controller.abort();
  }, [listAttempt, reportError]);

  useEffect(() => () => loadController.current?.abort(), []);
  useEffect(() => { endOfMessages.current?.scrollIntoView({ block: 'end' }); }, [messages, pendingQuestion]);
  useEffect(() => {
    if (!exportResult) return;
    const timer = setTimeout(() => setExportResult(null), exportResult.expires_in * 1000);
    return () => clearTimeout(timer);
  }, [exportResult]);

  function resetSelection(conversation = null) {
    loadController.current?.abort();
    activeId.current = conversation?.id || null;
    setActive(conversation);
    setMessages([]);
    setDraft('');
    setLoadError('');
    setError('');
    setLoading(false);
    setExportResult(null);
    setSidebarOpen(false);
  }

  async function openConversation(conversation) {
    if (busy) return;
    resetSelection(conversation);
    const controller = new AbortController();
    loadController.current = controller;
    setLoading(true);
    try {
      const data = await apiRequest(`/api/conversations/${conversation.id}/`, { signal: controller.signal });
      if (controller.signal.aborted || activeId.current !== conversation.id) return;
      setActive(data.conversation);
      setMessages(data.messages);
    } catch (failure) {
      if (!controller.signal.aborted) reportError(failure, setLoadError);
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }

  async function createConversation() {
    if (busy || listLoading) return;
    setAction('create');
    setError('');
    try {
      const { conversation } = await apiRequest('/api/conversations/', { method: 'POST' });
      setConversations((items) => [conversation, ...items]);
      resetSelection(conversation);
      textarea.current?.focus();
    } catch (failure) {
      reportError(failure);
    } finally {
      setAction('');
    }
  }

  async function sendMessage(event) {
    event.preventDefault();
    const query = draft.trim();
    if (!query || busy || listLoading || loading || loadError) return;
    setAction('send');
    setError('');
    setExportResult(null);
    setDraft('');
    setPendingQuestion(query);
    let conversation = active;
    try {
      if (!conversation) {
        const created = await apiRequest('/api/conversations/', { method: 'POST' });
        conversation = created.conversation;
        activeId.current = conversation.id;
        setActive(conversation);
        setConversations((items) => [conversation, ...items]);
      }
      const data = await apiRequest(`/api/conversations/${conversation.id}/messages/`, { method: 'POST', body: { query } });
      setMessages((items) => [...items, ...data.messages]);
      setPendingQuestion('');
      // 첫 질문 후 서버에서 정한 제목을 목록과 현재 상담에 반영한다.
      try {
        const updated = await apiRequest('/api/conversations/');
        setConversations(updated.conversations);
        const current = updated.conversations.find((item) => item.id === conversation.id);
        if (current) setActive(current);
      } catch (failure) {
        reportError(failure, setListError);
      }
    } catch (failure) {
      setDraft(query);
      reportError(failure);
    } finally {
      setPendingQuestion('');
      setAction('');
      textarea.current?.focus();
    }
  }

  async function exportConversation() {
    if (!active || !messages.length || !exportEnabled || busy || loading || loadError) return;
    const conversationId = active.id;
    setAction('export');
    setError('');
    setExportResult(null);
    try {
      const result = await apiRequest(`/api/conversations/${conversationId}/export/`, { method: 'POST' });
      if (typeof result?.download_url !== 'string' || !result.download_url.startsWith('https://') ||
          !Number.isInteger(result.expires_in) || result.expires_in < 1 || result.expires_in > 600) {
        throw new ApiError('다운로드 링크를 확인하지 못했습니다. 다시 시도해 주세요.');
      }
      if (activeId.current === conversationId) setExportResult(result);
    } catch (failure) {
      reportError(failure);
    } finally {
      setAction('');
    }
  }

  async function deleteConversation() {
    if (!deleteTarget || busy) return;
    setAction('delete');
    setError('');
    try {
      await apiRequest(`/api/conversations/${deleteTarget.id}/`, { method: 'DELETE' });
      setConversations((items) => items.filter((item) => item.id !== deleteTarget.id));
      if (activeId.current === deleteTarget.id) resetSelection();
      setDeleteTarget(null);
    } catch (failure) {
      setDeleteTarget(null);
      reportError(failure);
    } finally {
      setAction('');
    }
  }

  async function logout() {
    if (busy) return;
    setAction('logout');
    try { await onLogout(); } catch (failure) { reportError(failure); setAction(''); }
  }

  function chooseSuggestion(query) {
    setDraft(query);
    textarea.current?.focus();
  }

  return (
    <div className="workspace">
      {sidebarOpen && <button className="sidebar-backdrop" aria-label="상담 목록 닫기" onClick={() => setSidebarOpen(false)} />}
      <aside className={`sidebar ${sidebarOpen ? 'is-open' : ''}`} id="conversation-sidebar" aria-label="상담 목록">
        <div className="sidebar-brand"><Brand compact /><button className="icon-button mobile-only" aria-label="상담 목록 닫기" onClick={() => setSidebarOpen(false)}><Icon name="close" /></button></div>
        <button className="button new-conversation" onClick={createConversation} disabled={busy || listLoading}><Icon name="plus" />{action === 'create' ? '준비하고 있습니다…' : '새 상담 시작하기'}</button>
        <div className="sidebar-section-heading"><h2>내 상담 기록</h2><span>{conversations.length}</span></div>
        <nav className="conversation-list" aria-label="저장한 상담">
          {listLoading && <p className="sidebar-note" role="status">상담 기록을 불러오고 있습니다…</p>}
          {listError && <div className="sidebar-error" role="alert"><p>{listError}</p><button onClick={() => setListAttempt((value) => value + 1)} disabled={busy}>다시 불러오기</button></div>}
          {!listLoading && !listError && conversations.length === 0 && <p className="sidebar-note">첫 상담을 시작해 보세요.<br />대화가 여기에 차곡차곡 저장됩니다.</p>}
          {conversations.map((conversation) => <div key={conversation.id} className={`conversation-item ${active?.id === conversation.id ? 'is-active' : ''}`}><button className="conversation-select" onClick={() => openConversation(conversation)} disabled={busy} aria-current={active?.id === conversation.id ? 'page' : undefined}><Icon name="chat" size={18} /><span><strong>{conversation.title || '새 상담'}</strong><small>{displayDate(conversation.created_at)}</small></span></button><button className="icon-button conversation-delete" aria-label={`${conversation.title || '새 상담'} 삭제`} disabled={busy} onClick={() => setDeleteTarget(conversation)}><Icon name="trash" size={17} /></button></div>)}
        </nav>
        <div className="sidebar-account"><span className="user-avatar">{user.username.slice(0, 1).toUpperCase()}</span><span className="account-name"><strong>{user.username}</strong><small>나의 커리어 노트</small></span><button className="icon-button" aria-label="로그아웃" title="로그아웃" onClick={logout} disabled={busy}><Icon name="logout" size={19} /></button></div>
      </aside>
      <main className="chat-main">
        <header className="chat-header">
          <div className="chat-heading"><button className="icon-button mobile-only" aria-label="상담 목록 열기" aria-expanded={sidebarOpen} aria-controls="conversation-sidebar" onClick={() => setSidebarOpen(true)}><Icon name="menu" /></button><div><p className="eyebrow">IT 커리어 상담</p><h1>{active?.title || '나에게 맞는 다음 단계'}</h1></div></div>
          {exportEnabled ? <button type="button" className="button button-secondary export-button" onClick={exportConversation} disabled={!active || !messages.length || busy || loading || Boolean(loadError)}><Icon name="download" size={17} />{action === 'export' ? '준비 중…' : '대화 내보내기'}</button> : <span className="header-caption"><span />함께 정리해 보세요</span>}
        </header>
        <div className="chat-scroll" aria-busy={loading}>
          {loading ? <div className="loading-conversation" role="status"><span className="spinner" />상담 내용을 불러오고 있습니다…</div> : loadError ? <div className="load-error" role="alert"><p>{loadError}</p><button className="button button-secondary" onClick={() => openConversation(active)}>다시 불러오기</button></div> : <>
            {messages.length === 0 && !pendingQuestion && <section className="welcome"><span className="welcome-mark"><Icon name="compass" size={34} /></span><p className="eyebrow">생각을 꺼내는 것부터 시작해요</p><h2>지금, 어떤 고민이 있으세요?</h2><p>관심 있는 분야와 지금까지의 경험을 알려 주세요.<br />직무 선택부터 학습 계획까지 함께 정리해 드릴게요.</p><div className="suggestions">{suggestions.map((suggestion, index) => <button key={suggestion.label} onClick={() => chooseSuggestion(suggestion.query)} disabled={busy}><span className="suggestion-number">0{index + 1}</span><span>{suggestion.label}</span><Icon name="arrow" size={18} /></button>)}</div></section>}
            <div className="messages" aria-label="상담 메시지"><>{messages.map((message) => <Message key={message.id} role={message.role} content={message.content} />)}</>{pendingQuestion && <><Message role="human" content={pendingQuestion} pending /><div className="waiting-reply" role="status"><span className="assistant-avatar"><Icon name="compass" size={21} /></span><span className="typing-dots"><i /><i /><i /></span><span>답변을 준비하고 있습니다…</span></div></>}<div ref={endOfMessages} /></div>
          </>}
        </div>
        <footer className="composer-area">
          {exportResult && <div className="feedback feedback-success export-feedback" role="status"><span>TXT 파일이 준비되었습니다. 10분 이내에 다운로드해 주세요.</span><a href={exportResult.download_url} target="_blank" rel="noopener noreferrer" referrerPolicy="no-referrer">TXT 다운로드<Icon name="download" size={16} /></a></div>}
          {error && <div className="feedback feedback-error composer-error" role="alert"><span>{error}</span><button className="icon-button" aria-label="오류 안내 닫기" onClick={() => setError('')}><Icon name="close" size={18} /></button></div>}
          <form className="composer" onSubmit={sendMessage}>
            <label htmlFor="question" className="visually-hidden">상담할 질문</label>
            <textarea ref={textarea} id="question" name="query" rows={2} placeholder="궁금한 직무나 준비 중인 목표를 편하게 말씀해 주세요." value={draft} onChange={(event) => setDraft(event.target.value)} disabled={busy || listLoading || loading || Boolean(loadError)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); event.currentTarget.form.requestSubmit(); } }} />
            <div className="composer-bottom"><span>Enter로 전송 · Shift+Enter로 줄바꿈</span><button type="submit" className="send-button" disabled={!draft.trim() || busy || listLoading || loading || Boolean(loadError)} aria-label="질문 보내기"><span>{action === 'send' ? '답변 대기 중' : '보내기'}</span><Icon name="arrow" size={19} /></button></div>
          </form>
          <ModeNotice mode={mode} />
          {mode === 'openai' && <p className="composer-footnote">현재 상황을 구체적으로 알려 주시면 상담에 도움이 됩니다.</p>}
        </footer>
      </main>
      {deleteTarget && <DeleteDialog conversation={deleteTarget} busy={action === 'delete'} onCancel={() => setDeleteTarget(null)} onConfirm={deleteConversation} />}
    </div>
  );
}

function validateSession(data) {
  if (!data || !['demo', 'openai'].includes(data.chat_mode)) throw new ApiError('상담 모드 정보를 확인하지 못했습니다. 잠시 후 다시 시도해 주세요.');
  return data;
}

export default function App() {
  const [session, setSession] = useState({ loading: true, user: null, mode: null, exportEnabled: false, error: '', notice: '' });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setSession((value) => ({ ...value, loading: true, error: '' }));
    apiRequest('/api/auth/me/', { signal: controller.signal })
      .then(validateSession)
      .then((data) => { if (!controller.signal.aborted) setSession({ loading: false, user: data.user, mode: data.chat_mode, exportEnabled: data.s3_export_enabled === true, error: '', notice: '' }); })
      .catch((failure) => { if (!controller.signal.aborted) setSession((value) => ({ ...value, loading: false, error: failure.message })); });
    return () => controller.abort();
  }, [attempt]);

  const sessionExpired = useCallback(() => {
    setSession((value) => ({ ...value, user: null, notice: '로그인이 만료되었습니다. 다시 로그인해 주세요.' }));
  }, []);

  async function authenticated() {
    const data = validateSession(await apiRequest('/api/auth/me/'));
    if (!data.user) throw new ApiError('로그인 상태를 확인하지 못했습니다. 다시 로그인해 주세요.');
    setSession({ loading: false, user: data.user, mode: data.chat_mode, exportEnabled: data.s3_export_enabled === true, error: '', notice: '' });
  }

  async function logout() {
    await apiRequest('/api/auth/logout/', { method: 'POST' });
    setSession((value) => ({ ...value, user: null, notice: '' }));
  }

  if (session.loading || session.error) return <main className="connection-page"><Brand /><div className="connection-content">{session.loading ? <><span className="spinner" /><h1>상담 공간을 준비하고 있습니다.</h1><p>잠시만 기다려 주세요.</p></> : <><h1>잠시 연결을 확인해 주세요.</h1><p role="alert">{session.error}</p><button className="button button-primary" onClick={() => setAttempt((value) => value + 1)}>다시 연결하기<Icon name="arrow" /></button></>}</div></main>;
  if (!session.user) return <AuthForm mode={session.mode} onAuthenticated={authenticated} sessionNotice={session.notice} />;
  return <Workspace key={session.user.id} user={session.user} mode={session.mode} exportEnabled={session.exportEnabled} onLogout={logout} onSessionExpired={sessionExpired} />;
}
