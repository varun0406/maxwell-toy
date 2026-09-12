import { api } from './client';

// ── Auth ────────────────────────────────────────────────────────────────────
export const authApi = {
  register: (data: { username: string; email?: string; password: string }) =>
    api.post('/auth/register', data),
  login: (data: { username: string; password: string }) =>
    api.post('/auth/login', data),
  me: () => api.get('/auth/me'),
  logout: () => api.post('/auth/logout'),
};

// ── Users ───────────────────────────────────────────────────────────────────
export const usersApi = {
  list: () => api.get('/users/'),
  updateStatus: (id: number, is_active: boolean) => api.put(`/users/${id}?is_active=${is_active}`),
};

// ── Parties ─────────────────────────────────────────────────────────────────
export const partiesApi = {
  list: (search?: string) =>
    api.get('/parties/', { params: search ? { search } : {} }),
  create: (data: unknown) => api.post('/parties/', data),
  get: (id: number) => api.get(`/parties/${id}`),
  update: (id: number, data: unknown) => api.put(`/parties/${id}`, data),
  delete: (id: number) => api.delete(`/parties/${id}`),
  ledger: (id: number) => api.get(`/parties/${id}/ledger`),
  addJournalEntry: (id: number, data: { amount: number; entry_date: string; description: string }) =>
    api.post(`/parties/${id}/journal`, data),
  deleteJournalEntry: (journalId: number) => api.delete(`/journal/${journalId}`),
};

// ── Invoices ─────────────────────────────────────────────────────────────────
export const invoicesApi = {
  list: (partyId?: number, unpaidOnly?: boolean) =>
    api.get('/invoices/', { params: { ...(partyId && { party_id: partyId }), ...(unpaidOnly && { unpaid_only: true }) } }),
  create: (data: unknown) => api.post('/invoices/', data),
  get: (id: number) => api.get(`/invoices/${id}`),
  update: (id: number, data: unknown) => api.put(`/invoices/${id}`, data),
  delete: (id: number) => api.delete(`/invoices/${id}`),
  upload: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/invoices/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};

// ── Payments ─────────────────────────────────────────────────────────────────
export const paymentsApi = {
  list: (partyId?: number) =>
    api.get('/payments/', { params: partyId ? { party_id: partyId } : {} }),
  create: (data: unknown) => api.post('/payments/', data),
  get: (id: number) => api.get(`/payments/${id}`),
  allocate: (id: number, data: unknown) => api.post(`/payments/${id}/allocate`, data),
  delete: (id: number) => api.delete(`/payments/${id}`),
};

// ── Analytics ─────────────────────────────────────────────────────────────────
export const analyticsApi = {
  summary: () => api.get('/analytics/summary'),
  parties: () => api.get('/analytics/parties'),
  party: (id: number) => api.get(`/analytics/party/${id}`),
  aging: () => api.get('/analytics/aging'),
};

// ── Address Book ─────────────────────────────────────────────────────────────
export const addressBookApi = {
  list: (search?: string) => api.get('/address-book/', { params: search ? { search } : {} }),
  create: (data: unknown) => api.post('/address-book/', data),
  update: (id: number, data: unknown) => api.put(`/address-book/${id}`, data),
  delete: (id: number) => api.delete(`/address-book/${id}`),
};

// ── Item Master ───────────────────────────────────────────────────────────────
export const itemsApi = {
  search: (q: string) => api.get('/items/', { params: { search: q } }),
  upsert: (data: { item_name: string; default_rate?: number }) => api.post('/items/upsert', data),
  delete: (id: number) => api.delete(`/items/${id}`),
};
