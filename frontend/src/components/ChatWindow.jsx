import { useState, useEffect, useRef } from 'react';
import { fetchChat, postChatMessage, getAiChatReply } from '../api/tickets';
import './ChatWindow.css';

export default function ChatWindow({ ticket, onTicketUpdate }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    if (!ticket) { setMessages([]); return; }
    fetchChat(ticket.id)
      .then(setMessages)
      .catch(() => setMessages([]));
    setInput('');
  }, [ticket?.id]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  async function handleSend() {
    const text = input.trim();
    if (!text || sending) return;
    setSending(true);
    setInput('');

    try {
      const saved = await postChatMessage(ticket.id, 'user', text);
      setMessages((prev) => [...prev, saved]);

      // Если оператор запрашивает человека — обновляем статус в UI
      if (text.toLowerCase().includes('вызвать оператора') && onTicketUpdate) {
        onTicketUpdate({ ...ticket, status: 'needs_operator' });
      }

      // Реальный AI-ответ
      const botMsg = await getAiChatReply(ticket.id);
      setMessages((prev) => [...prev, botMsg]);
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
      </div>

      <div className="chat-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`chat-bubble chat-bubble--${msg.role}`}>
            {msg.role === 'bot' && <span className="chat-avatar">🤖</span>}
            <div className="chat-text">{msg.text}</div>
            {msg.role === 'user' && <span className="chat-avatar">👤</span>}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="chat-input-row">
        <textarea
          className="chat-input"
          placeholder="Введите сообщение..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKey}
          rows={1}
          disabled={sending}
        />
        <button className="chat-send-btn" onClick={handleSend} disabled={!input.trim() || sending}>
          {sending ? '...' : 'Отправить'}
        </button>
      </div>
    </div>
  );
}
