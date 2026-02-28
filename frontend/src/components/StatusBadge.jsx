import './StatusBadge.css';

const LABELS = {
  open: 'Открытые',
  in_progress: 'В процессе',
  closed: 'Закрытые',
};

export default function StatusBadge({ value }) {
  return (
    <span className={`status-badge status-badge--${value}`}>
      {LABELS[value] ?? value}
    </span>
  );
}
