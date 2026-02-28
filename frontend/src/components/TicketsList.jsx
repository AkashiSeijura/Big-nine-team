import './TicketsList.css';

const STATUS_ICON = {
  open: { icon: '👤', label: 'Открытые' },
  in_progress: { icon: '⏳', label: 'В процессе' },
  closed: { icon: '✅', label: 'Закрытые' },
};

function fmt(dateStr) {
  return new Date(dateStr).toLocaleDateString('ru-RU', {
    day: '2-digit', month: '2-digit', year: 'numeric',
  });
}

export default function TicketsList({ tickets, selectedId, onSelect }) {
  return (
    <aside className="tickets-list">
      <div className="tickets-list-header">
        <span className="tickets-list-title">Обращения</span>
        <span className="tickets-list-count">{tickets.length}</span>
      </div>
      <div className="tickets-list-body">
        {tickets.map((ticket) => {
          const status = STATUS_ICON[ticket.status] || STATUS_ICON.open;

          let colorClass = '';
          if (ticket.status === 'closed') {
            colorClass = 'ticket-card--green';
          } else if (ticket.category === 'malfunction' && ticket.status !== 'closed') {
            colorClass = 'ticket-card--red';
          } else if (ticket.status === 'open') {
            colorClass = 'ticket-card--orange';
          }

          const activeClass = selectedId === ticket.id ? 'ticket-card--active' : '';

          return (
            <div
              key={ticket.id}
              className={`ticket-card ${activeClass} ${colorClass}`}
              onClick={() => onSelect(ticket)}
            >
              <div className="ticket-card-main">
                <div className="ticket-card-meta">
                  <span className="ticket-card-date">{fmt(ticket.date_received)}</span>
                  <span className="ticket-card-status" title={status.label}>{status.icon}</span>
                </div>
                <div className="ticket-card-name">{ticket.full_name}</div>
                <div className="ticket-card-summary">{ticket.summary}</div>
              </div>
            </div>
          );
        })}
      </div>
    </aside>
  );
}
