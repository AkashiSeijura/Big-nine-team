import './TicketsList.css';

const STATUS_ICON = {
  open: { icon: '👤', label: 'Открытые' },
  in_progress: { icon: '⏳', label: 'В процессе' },
  closed: { icon: '✅', label: 'Закрыто' },
};

function fmt(dateStr) {
  return new Date(dateStr).toLocaleDateString('ru-RU', {
    day: '2-digit', month: '2-digit', year: 'numeric',
  });
}

export default function TicketsList({ tickets, selectedId, onSelect, filters, onFilterChange }) {
  const hasActiveFilter =
    (filters.status && filters.status !== 'active') || filters.sentiment || filters.category || filters.search;

  return (
    <aside className="tickets-list">
      <div className="tickets-list-header">
        <span className="tickets-list-title">Обращения</span>
        <span className="tickets-list-count">{tickets.length}</span>
      </div>

      <div className="tickets-filter-bar">
        <div className="tickets-filter-search-row">
          <input
            className="tickets-filter-search"
            placeholder="Поиск по имени, теме, email..."
            value={filters.search}
            onChange={(e) => onFilterChange('search', e.target.value)}
          />
          {hasActiveFilter && (
            <button
              className="tickets-filter-reset"
              onClick={() => {
                onFilterChange('status', 'active');
                onFilterChange('sentiment', '');
                onFilterChange('category', '');
                onFilterChange('search', '');
              }}
              title="Сбросить фильтры"
            >
              ✕
            </button>
          )}
        </div>
        <div className="tickets-filter-selects">
          <select
            className="tickets-filter-select"
            value={filters.status}
            onChange={(e) => onFilterChange('status', e.target.value)}
          >
            <option value="">Все статусы</option>
            <option value="active">Только активные</option>
            <option value="open">Новая</option>
            <option value="in_progress">В работе</option>
            <option value="closed">Закрыта</option>
          </select>
          <select
            className="tickets-filter-select"
            value={filters.sentiment}
            onChange={(e) => onFilterChange('sentiment', e.target.value)}
          >
            <option value="">Тональность</option>
            <option value="positive">Позитивная</option>
            <option value="neutral">Нейтральная</option>
            <option value="negative">Негативная</option>
          </select>
          <select
            className="tickets-filter-select"
            value={filters.category}
            onChange={(e) => onFilterChange('category', e.target.value)}
          >
            <option value="">Категория</option>
            <option value="malfunction">Неисправность</option>
            <option value="calibration">Калибровка</option>
            <option value="documentation">Документация</option>
            <option value="other">Прочее</option>
          </select>
        </div>
      </div>

      <div className="tickets-list-body">
        {tickets.length === 0 ? (
          <div className="tickets-empty">Нет обращений</div>
        ) : (
          tickets.map((ticket) => {
            const status = STATUS_ICON[ticket.status] || STATUS_ICON.open;

            let colorClass = '';
            if (ticket.status === 'closed') {
              colorClass = 'ticket-card--green';
            } else if (ticket.category === 'malfunction' && ticket.status !== 'closed') {
              colorClass = 'ticket-card--red';
            } else if (ticket.status === 'open') {
              colorClass = 'ticket-card--orange';
            }

            return (
              <div
                key={ticket.id}
                className={`ticket-card ${selectedId === ticket.id ? 'ticket-card--active' : ''} ${colorClass}`}
                onClick={() => onSelect(ticket)}
              >
                <div className="ticket-card-main">
                  <div className="ticket-card-meta">
                    <span className="ticket-card-date">{fmt(ticket.date_received)}</span>
                    <span className="ticket-card-status" title={status.label}>{status.icon}</span>
                  </div>
                  <div className="ticket-card-name">{ticket.full_name || ticket.email || '—'}</div>
                  <div className="ticket-card-summary">{ticket.summary}</div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
}
