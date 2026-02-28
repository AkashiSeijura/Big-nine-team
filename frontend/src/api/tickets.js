const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function authHeaders() {
  const token = localStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function fetchTickets() {
  const res = await fetch(`${API_BASE}/api/tickets`, { headers: authHeaders() });
  if (!res.ok) throw new Error('Server error');
  return await res.json();
}

export async function fetchTicket(id) {
  const res = await fetch(`${API_BASE}/api/tickets/${id}`, { headers: authHeaders() });
  if (!res.ok) throw new Error('Server error');
  return await res.json();
}

export async function updateTicketResponse(id, text) {
  const res = await fetch(`${API_BASE}/api/tickets/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ ai_response: text }),
  });
  if (!res.ok) throw new Error('Server error');
  return await res.json();
}

export async function sendResponse(id) {
  const res = await fetch(`${API_BASE}/api/tickets/${id}/send`, {
    method: 'POST',
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error('Server error');
  return await res.json();
}

export async function fetchChat(ticketId) {
  const res = await fetch(`${API_BASE}/api/tickets/${ticketId}/chat`, { headers: authHeaders() });
  if (!res.ok) throw new Error('Server error');
  return await res.json();
}

export async function postChatMessage(ticketId, role, text) {
  const res = await fetch(`${API_BASE}/api/tickets/${ticketId}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ role, text }),
  });
  if (!res.ok) throw new Error('Server error');
  return await res.json();
}

export async function fetchMe() {
  const res = await fetch(`${API_BASE}/api/auth/me`, { headers: authHeaders() });
  if (!res.ok) throw new Error('Server error');
  return await res.json();
}

export async function updateProfile(telegram_ids) {
  const res = await fetch(`${API_BASE}/api/auth/me`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ telegram_ids }),
  });
  if (!res.ok) throw new Error('Server error');
  return await res.json();
}
