import { useState, useEffect, useRef } from 'react';
import { fetchChat, postChatMessage } from '../api/tickets';
import './ChatWindow.css';

const ROLE_AVATAR = { user: '👤', bot: '🤖', operator: '👨‍💼' };

export default function ChatWindow({ ticket, onTicketUpdate }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const bottomRef = useRef(null);

  const canRespond = ticket?.status === 'needs_operator';

  useEffect(() => {
    if (!ticket) { setMessages([]); return; }
    fetchChat(ticket.id)
      .then(setMessages)
      .catch(() => setMessages([]));
    setInput('');
  }, [ticket?.id]);

  // Re-check canRespond when ticket status changes (e.g. from parent update)
  useEffect(() => {
    if (ticket?.status === 'needs_operator') {
      // refresh messages to show any new ones
      if (ticket?.id) {
        fetchChat(ticket.id).then(setMessages).catch(() => {});
      }
    }
  }, [ticket?.status]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  async function handleSend() {
    const text = input.trim();
    if (!text || sending || !canRespond) return;
    setSending(true);
    setInput('');

    try {
      // Save as operator message — backend will email client
      const saved = await postChatMessage(ticket.id, 'operator', text);
      setMessages((prev) => [...prev, saved]);
    } catch {
      // ignore
    } finally {
      setSending(false);
    }
  }

  function handleKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  if (!ticket) {
    return (
      <div className="chat-window chat-window--empty">
        <span className="chat-empty-text">Выберите обращение для просмотра чата</span>
      </div>
    );
  }

  return (
    <div className="chat-window">
      <div className="chat-header">
        <span className="chat-title">Чат с AI-ассистентом</span>
        {canRespond && <span className="chat-status-badge">🟢 Оператор подключён</span>}
      </div>

      <div className="chat-messages">
        {messages.map((msg, i) => {
          const isOutgoing = msg.role === 'bot' || msg.role === 'operator';
          return (
            <div key={i} className={`chat-bubble chat-bubble--${msg.role}`}>
              {!isOutgoing && (
                <span className="chat-avatar">{ROLE_AVATAR[msg.role] ?? '👤'}</span>
              )}
              <div className="chat-text">{msg.text}</div>
              {isOutgoing && (
                <span className="chat-avatar">{ROLE_AVATAR[msg.role] ?? '🤖'}</span>
              )}
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>

      {canRespond ? (
        <div className="chat-input-row">
          <textarea
            className="chat-input"
            placeholder="Введите ответ клиенту..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKey}
            rows={1}
            disabled={sending}
          />
          <button
            className="chat-send-btn"
            onClick={handleSend}
            disabled={!input.trim() || sending}
          >
            {sending ? '...' : 'Отправить'}
          </button>
        </div>
      ) : (
        <div className="chat-locked">
          🔒 Ввод заблокирован — оператор подключится после того, как клиент напишет «вызвать оператора»
        </div>
      )}
    </div>
  );
}
