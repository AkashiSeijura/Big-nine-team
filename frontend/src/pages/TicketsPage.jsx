import { useEffect, useState, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchTickets, fetchMe, updateProfile } from '../api/tickets';
import TicketsList from '../components/TicketsList';
import TicketForm from '../components/TicketForm';
import ChatWindow from '../components/ChatWindow';
import ExportButton from '../components/ExportButton';
import KnowledgeBasePage from './KnowledgeBasePage';
import StatsPage from './StatsPage';
import './TicketsPage.css';

const NAV_TABS = ['Запросы', 'База знаний', 'Статистика'];
const SIDEBAR_MIN = 180;
const SIDEBAR_MAX = 520;

export default function TicketsPage() {
  const navigate = useNavigate();
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [activeTab, setActiveTab] = useState('Запросы');
  const [sidebarWidth, setSidebarWidth] = useState(280);
  const [showProfile, setShowProfile] = useState(false);
  const [profileData, setProfileData] = useState(null);
  const [tgIds, setTgIds] = useState([]);
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileMsg, setProfileMsg] = useState('');
  const dragging = useRef(false);
  const startX = useRef(0);
  const startW = useRef(0);

  useEffect(() => {
    if (!localStorage.getItem('auth')) navigate('/');
  }, [navigate]);

  useEffect(() => {
    fetchTickets()
      .then((data) => {
        setTickets(data);
        setSelected(data[0] || null);
        setLoading(false);
      })
      .catch(() => {
        localStorage.removeItem('token');
        localStorage.removeItem('auth');
        navigate('/');
      });
  }, [navigate]);

  const onMouseDown = useCallback((e) => {
    dragging.current = true;
    startX.current = e.clientX;
    startW.current = sidebarWidth;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }, [sidebarWidth]);

  useEffect(() => {
    function onMove(e) {
      if (!dragging.current) return;
      const delta = e.clientX - startX.current;
      const next = Math.max(SIDEBAR_MIN, Math.min(SIDEBAR_MAX, startW.current + delta));
      setSidebarWidth(next);
    }
    function onUp() {
      dragging.current = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    }
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, []);

  function handleLogout() {
    localStorage.removeItem('auth');
    localStorage.removeItem('token');
    navigate('/');
  }

  async function handleOpenProfile() {
    const data = await fetchMe();
    setProfileData(data);
    setTgIds((data.telegram_ids || []).map(String));
    setProfileMsg('');
    setShowProfile(true);
  }

  async function handleSaveProfile() {
    setProfileSaving(true);
    try {
      const ids = tgIds.map((v) => parseInt(v.trim(), 10)).filter((v) => !isNaN(v) && v > 0);
      const updated = await updateProfile(ids);
      setProfileData(updated);
      setTgIds((updated.telegram_ids || []).map(String));
      setProfileMsg('Сохранено');
      setTimeout(() => setProfileMsg(''), 2000);
    } catch {
      setProfileMsg('Ошибка сохранения');
    } finally {
      setProfileSaving(false);
    }
  }

  function handleTgIdChange(index, value) {
    setTgIds((prev) => prev.map((v, i) => (i === index ? value : v)));
  }

  function handleTgIdRemove(index) {
    setTgIds((prev) => prev.filter((_, i) => i !== index));
  }

  function handleTgIdAdd() {
    setTgIds((prev) => [...prev, '']);
  }

  return (
    <div className="crm-layout">
      <header className="crm-header">
        <div className="crm-header-left">
          <span className="crm-logo">ЭРИС</span>
          <nav className="crm-nav">
            {NAV_TABS.map((tab) => (
              <button
                key={tab}
                className={`crm-nav-tab ${activeTab === tab ? 'crm-nav-tab--active' : ''}`}
                onClick={() => setActiveTab(tab)}
              >
                {tab}
              </button>
            ))}
          </nav>
        </div>
        <div className="crm-header-right">
          {activeTab === 'Запросы' && <ExportButton tickets={tickets} />}
          <button className="crm-profile-btn" onClick={handleOpenProfile}>Профиль</button>
          <button className="crm-logout-btn" onClick={handleLogout}>Выйти</button>
        </div>
      </header>

      {showProfile && (
        <div className="crm-modal-overlay" onClick={() => setShowProfile(false)}>
          <div className="crm-modal" onClick={(e) => e.stopPropagation()}>
            <div className="crm-modal-header">
              <span className="crm-modal-title">Профиль</span>
              <button className="crm-modal-close" onClick={() => setShowProfile(false)}>✕</button>
            </div>
            {profileData && (
              <div className="crm-modal-body">
                <div className="crm-profile-row">
                  <span className="crm-profile-label">Имя</span>
                  <span className="crm-profile-value">{profileData.full_name}</span>
                </div>
                <div className="crm-profile-row">
                  <span className="crm-profile-label">Email</span>
                  <span className="crm-profile-value">{profileData.email}</span>
                </div>
                <div className="crm-profile-row">
                  <span className="crm-profile-label">Роль</span>
                  <span className="crm-profile-value">{profileData.role}</span>
                </div>
                <div className="crm-profile-field">
                  <label className="crm-profile-label">Telegram ID</label>
                  {tgIds.map((val, idx) => (
                    <div key={idx} className="crm-profile-tg-row">
                      <input
                        className="crm-profile-input"
                        type="number"
                        placeholder="Числовой Telegram ID"
                        value={val}
                        onChange={(e) => handleTgIdChange(idx, e.target.value)}
                      />
                      <button
                        className="crm-profile-tg-remove"
                        onClick={() => handleTgIdRemove(idx)}
                        title="Удалить"
                      >✕</button>
                    </div>
                  ))}
                  <button className="crm-profile-tg-add" onClick={handleTgIdAdd}>+ Добавить ID</button>
                  <span className="crm-profile-hint">Узнать ID можно через @userinfobot в Telegram</span>
                </div>
                <div className="crm-profile-actions">
                  <button className="crm-profile-save" onClick={handleSaveProfile} disabled={profileSaving}>
                    {profileSaving ? 'Сохранение...' : 'Сохранить'}
                  </button>
                  {profileMsg && <span className="crm-profile-msg">{profileMsg}</span>}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'База знаний' && <KnowledgeBasePage />}

      {activeTab === 'Статистика' && <StatsPage tickets={tickets} />}

      {activeTab === 'Запросы' && (
        loading ? (
          <div className="crm-loading">
            <span className="crm-loading-dot" />
            Загрузка заявок...
          </div>
        ) : (
          <div className="crm-body">
            <div className="crm-sidebar" style={{ width: sidebarWidth }}>
              <TicketsList tickets={tickets} selectedId={selected?.id} onSelect={setSelected} />
            </div>
            <div className="crm-resize-handle" onMouseDown={onMouseDown} />
            <div className="crm-detail">
              <TicketForm ticket={selected} />
              <ChatWindow ticket={selected} />
            </div>
          </div>
        )
      )}
    </div>
  );
}
