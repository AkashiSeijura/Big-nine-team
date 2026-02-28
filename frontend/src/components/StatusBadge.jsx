import './StatusBadge.css';

const LABELS = {
  open: 'Новая',
  in_progress: 'В работе',
  needs_operator: 'Нужен оператор',
  closed: 'Закрыта',
};

export default function StatusBadge({ value }) {
  return (
    <span className={`status-badge status-badge--${value}`}>
      {LABELS[value] ?? value}
    </span>
  );
}
