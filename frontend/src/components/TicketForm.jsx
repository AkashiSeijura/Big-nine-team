import { useState } from 'react';
import SentimentBadge from './SentimentBadge';
import CategoryBadge from './CategoryBadge';
import { updateTicketStatus } from '../api/tickets';
import './TicketForm.css';

const SENTIMENT_EMOJI = { positive: '😊', neutral: '😐', negative: '😠' };
const STATUS_LABEL = {
  open: 'Открытые 👤',
  in_progress: 'В процессе ⏳',
  closed: 'Закрытые ✅',
};
const CATEGORY_LABEL = {
  malfunction: 'Неисправность',
  calibration: 'Калибровка',
  documentation: 'Документация',
  other: 'Прочее',
};

function fmt(dateStr) {
  return new Date(dateStr).toLocaleString('ru-RU');
}

export default function TicketForm({ ticket, onTicketUpdate }) {
  const [closing, setClosing] = useState(false);

  async function handleClose() {
    if (closing) return;
    setClosing(true);
    try {
      const updated = await updateTicketStatus(ticket.id, 'closed');
      if (onTicketUpdate) onTicketUpdate(updated);
    } finally {
      setClosing(false);
    }
  }

  async function handleStatusChange(e) {
    const newStatus = e.target.value;
    try {
      const updated = await updateTicketStatus(ticket.id, newStatus);
      if (onTicketUpdate) onTicketUpdate(updated);
    } catch (err) {
      console.error(err);
    }
  }

  if (!ticket) {
    return (
      <div className="ticket-form ticket-form--empty">
        <div className="ticket-form-placeholder">
          <span className="tf-placeholder-icon">📋</span>
          <span>Выберите обращение из списка слева</span>
        </div>
      </div>
    );
  }

  const statusSelect = (
    <select
      className="tf-status-select"
      value={ticket.status}
      onChange={handleStatusChange}
    >
      {Object.entries(STATUS_LABEL).map(([val, label]) => (
        <option key={val} value={val}>{label}</option>
      ))}
    </select>
  );

  const rows = [
    ['Дата поступления', fmt(ticket.date_received), 'Статус', statusSelect],
    ['ФИО отправителя', ticket.full_name, 'Email', ticket.email],
    ['Объект / предприятие', ticket.company, 'Телефон', ticket.phone],
    ['Заводские номера', (ticket.device_serials || []).join(', '), 'Тип приборов', ticket.device_type],
    [
      'Эмоциональный окрас',
      <span key="sent" className="tf-sent-cell">
        {SENTIMENT_EMOJI[ticket.sentiment]} <SentimentBadge value={ticket.sentiment} />
      </span>,
      'Категория запроса',
      <CategoryBadge key="cat" value={ticket.category} />,
    ],
    ['Суть вопроса', { value: ticket.summary, wide: true }],
    ['Оригинальное письмо', { value: ticket.original_email, wide: true }],
  ];

  return (
    <div className="ticket-form">
      <div className="ticket-form-header">
        <span className="ticket-form-id">Заявка #{ticket.id}</span>
        {ticket.status !== 'closed' && (
          <button className="tf-close-btn" onClick={handleClose} disabled={closing}>
            {closing ? 'Закрытие...' : '✓ Закрыть заявку'}
          </button>
        )}
        {ticket.status === 'closed' && (
          <span className="tf-closed-label">✅ Закрыта</span>
        )}
      </div>

      <div className="ticket-form-table-wrap">
        <table className="tf-table">
          <tbody>
            {rows.map((row, i) => {
              const [l1, v1, l2, v2] = row;
              if (v1 && typeof v1 === 'object' && v1.wide) {
                return (
                  <tr key={i}>
                    <td className="tf-label-cell">{l1}</td>
                    <td className="tf-value-cell tf-value-cell--wide" colSpan={3}>{v1.value}</td>
                  </tr>
                );
              }
              return (
                <tr key={i}>
                  <td className="tf-label-cell">{l1}</td>
                  <td className="tf-value-cell">{v1}</td>
                  <td className="tf-label-cell">{l2}</td>
                  <td className="tf-value-cell">{v2}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
