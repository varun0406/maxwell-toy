/**
 * Mock API interceptor — intercepts every axios request and returns
 * dummy data instead of hitting the real backend.
 *
 * Activated when VITE_MOCK=true in .env
 */
import { api } from './client';
import {
  PARTIES, INVOICES, PAYMENTS, AGING,
} from './mockData';

// ── Address Book seed ─────────────────────────────────────────────────────
const ADDRESS_BOOK_SEED = [
  { id: 1, name: 'Sunrise Textiles Warehouse', phone: '9876543210', address_line1: '12, GIDC Estate', address_line2: 'Phase 2', city: 'Surat', created_at: '2026-01-01T00:00:00Z' },
  { id: 2, name: 'Kumar & Sons Store', phone: '9123456789', address_line1: 'Shop 4, Ring Road', address_line2: '', city: 'Ahmedabad', created_at: '2026-01-01T00:00:00Z' },
  { id: 3, name: 'City Depot', phone: '9988776655', address_line1: '88, Industrial Area', address_line2: 'Near Highway', city: 'Baroda', created_at: '2026-01-01T00:00:00Z' },
];

// ── Item Master seed ──────────────────────────────────────────────────────
const ITEM_MASTER_SEED = [
  { id: 1, item_name: 'Cotton Fabric', default_rate: 85 },
  { id: 2, item_name: 'Polyester Blend', default_rate: 65 },
  { id: 3, item_name: 'Silk Fabric', default_rate: 250 },
  { id: 4, item_name: 'Denim', default_rate: 120 },
  { id: 5, item_name: 'Linen', default_rate: 180 },
];

const delay = (ms = 300) => new Promise((r) => setTimeout(r, ms));

function ok(data: unknown, status = 200) {
  return { data, status, statusText: 'OK', headers: {} as any, config: {} as any };
}

// Store mock state (so creates/updates persist in session)
let parties = JSON.parse(JSON.stringify(PARTIES));
let invoices = JSON.parse(JSON.stringify(INVOICES));
let payments = JSON.parse(JSON.stringify(PAYMENTS));
let journalEntries: any[] = [];
let addressBook = [...ADDRESS_BOOK_SEED];
let itemMaster = [...ITEM_MASTER_SEED];
let nextPartyId = parties.length + 1;
let nextInvoiceId = invoices.length + 1;
let nextPaymentId = payments.length + 1;
let nextJournalId = 1;

// ── Ledger helper (moved here to access mutable memory) ──────────────────────
function buildLedger(partyId: number) {
  const invs = invoices.filter((i: any) => i.party_id === partyId);
  const pmts = payments.filter((p: any) => p.party_id === partyId);
  const jnls = journalEntries.filter((j: any) => j.party_id === partyId);

  const entries: any[] = [
    ...invs.map((i: any) => ({ type: 'invoice', date: i.invoice_date, reference: i.invoice_number, amount: i.amount, balance_due: i.balance_due })),
    ...pmts.map((p: any) => ({ type: 'payment', date: p.payment_date, reference: `PMT-${p.id}`, amount: -p.amount, balance_due: null })),
    ...jnls.map((j: any) => ({ type: 'journal', date: j.entry_date, reference: `JNL-${j.id}`, amount: j.amount, balance_due: null })),
  ].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

  let running = 0;
  return entries.map((e) => {
    running += e.amount;
    return { ...e, running_balance: running };
  });
}
let nextAddressId = addressBook.length + 1;
let nextItemId = itemMaster.length + 1;

export function setupMockInterceptors() {
  // Remove all real request adapters and intercept at response level
  api.interceptors.request.use(async (config) => {
    // Mark that we intercepted this
    (config as any)._mock = true;
    return config;
  });

  api.interceptors.response.use(
    undefined,
    async (error) => {
      // Fall through to real errors (network, etc) — but we intercept before sending
      return Promise.reject(error);
    }
  );

  // Override the adapter entirely
  api.defaults.adapter = async (config: any): Promise<any> => {
    await delay(250); // realistic loading feel

    const url: string = config.url || '';
    const method: string = (config.method || 'get').toLowerCase();
    const params = config.params || {};
    const body = config.data ? JSON.parse(config.data) : {};

    // ── Auth ─────────────────────────────────────────────────────────────
    if (url === '/auth/login' && method === 'post')
      return ok({ access_token: 'mock-access-token', refresh_token: 'mock-refresh-token', token_type: 'bearer' });
    if (url === '/auth/register' && method === 'post')
      return ok({ id: 1, username: body.username, email: body.email, is_active: true, created_at: new Date().toISOString() }, 201);
    if (url === '/auth/me')
      return ok({ id: 1, username: 'demo_user', email: 'demo@maxwell.app', is_active: true, created_at: '2026-01-01T00:00:00Z' });
    if (url === '/auth/logout') return ok(null, 204);
    if (url === '/auth/refresh')
      return ok({ access_token: 'mock-access-token', refresh_token: 'mock-refresh-token', token_type: 'bearer' });

    // ── Parties ───────────────────────────────────────────────────────────
    if (url === '/parties/' && method === 'get') {
      const search = (params.search || '').toLowerCase();
      const result = search ? parties.filter((p) => p.name.toLowerCase().includes(search)) : parties;
      return ok(result.filter((p) => p.is_active));
    }
    if (url === '/parties/' && method === 'post') {
      const p = { id: nextPartyId++, ...body, is_active: true, created_at: new Date().toISOString(), total_invoiced: 0, total_paid: 0, outstanding: 0 };
      parties.push(p);
      return ok(p, 201);
    }
    if (url.match(/^\/parties\/(\d+)$/) && method === 'get') {
      const id = Number(url.split('/')[2]);
      const p = parties.find((x) => x.id === id);
      return p ? ok(p) : ok({ detail: 'Not found' }, 404);
    }
    if (url.match(/^\/parties\/(\d+)$/) && method === 'put') {
      const id = Number(url.split('/')[2]);
      parties = parties.map((p) => p.id === id ? { ...p, ...body } : p);
      return ok(parties.find((p) => p.id === id));
    }
    if (url.match(/^\/parties\/(\d+)$/) && method === 'delete') {
      const id = Number(url.split('/')[2]);
      parties = parties.map((p) => p.id === id ? { ...p, is_active: false } : p);
      return ok(null, 204);
    }
    if (url.match(/^\/parties\/(\d+)\/ledger$/)) {
      const id = Number(url.split('/')[2]);
      return ok(buildLedger(id));
    }
    if (url.match(/^\/parties\/(\d+)\/journal$/) && method === 'post') {
      const partyId = Number(url.split('/')[2]);
      const entry = {
        id: nextJournalId++,
        party_id: partyId,
        amount: Number(body.amount),
        entry_date: body.entry_date,
        description: body.description || '',
        created_at: new Date().toISOString()
      };
      journalEntries.push(entry);
      parties = parties.map((p) => p.id === partyId ? { ...p, outstanding: p.outstanding + entry.amount } : p);
      return ok(entry, 201);
    }

    // ── Invoices ──────────────────────────────────────────────────────────
    if (url === '/invoices/' && method === 'get') {
      let result = [...invoices];
      if (params.party_id) result = result.filter((i) => i.party_id === Number(params.party_id));
      if (params.unpaid_only) result = result.filter((i) => !i.is_paid);
      return ok(result.sort((a, b) => new Date(b.invoice_date).getTime() - new Date(a.invoice_date).getTime()));
    }
    if (url === '/invoices/' && method === 'post') {
      const items = body.items || [];
      const totalAmount = items.reduce((sum: number, item: any) => sum + (item.meter * item.rate), 0);

      const inv = {
        id: nextInvoiceId++,
        invoice_number: body.invoice_number || `INV-${String(nextInvoiceId).padStart(5, '0')}`,
        party_id: body.party_id, amount: totalAmount, balance_due: totalAmount,
        billing_address: body.billing_address || '', shipping_address: body.shipping_address || '',
        description: body.description || '', invoice_date: body.invoice_date,
        due_date: body.due_date || null, is_paid: false, created_at: new Date().toISOString(),
        items: items.map((item: any, i: number) => ({ ...item, id: i + 1, invoice_id: nextInvoiceId - 1, total: item.meter * item.rate }))
      };
      invoices.push(inv);
      parties = parties.map((p) =>
        p.id === inv.party_id
          ? { ...p, total_invoiced: p.total_invoiced + inv.amount, outstanding: p.outstanding + inv.amount }
          : p
      );
      return ok(inv, 201);
    }
    if (url.match(/^\/invoices\/(\d+)$/) && method === 'get') {
      const id = Number(url.split('/')[2]);
      return ok(invoices.find((i) => i.id === id));
    }

    // ── Payments ──────────────────────────────────────────────────────────
    if (url === '/payments/' && method === 'get') {
      let result = [...payments];
      if (params.party_id) result = result.filter((p) => p.party_id === Number(params.party_id));
      return ok(result.sort((a, b) => new Date(b.payment_date).getTime() - new Date(a.payment_date).getTime()));
    }
    if (url === '/payments/' && method === 'post') {
      let unallocated = body.amount;
      const allocations: any[] = [];
      if (body.allocations && Array.isArray(body.allocations)) {
        for (const alloc of body.allocations) {
           unallocated -= alloc.allocated_amount;
           const inv = invoices.find(i => i.id === alloc.invoice_id);
           if (inv) {
             allocations.push({ invoice_id: inv.id, invoice_number: inv.invoice_number, allocated_amount: alloc.allocated_amount });
             inv.balance_due -= alloc.allocated_amount;
             if (inv.balance_due <= 0) inv.is_paid = true;
           }
        }
      }

      const pmt = {
        id: nextPaymentId++, party_id: body.party_id, amount: body.amount, unallocated: unallocated,
        payment_date: body.payment_date, note: body.note || '', mode: body.mode || 'cash',
        created_at: new Date().toISOString(), allocations,
      };
      payments.push(pmt);
      parties = parties.map((p) =>
        p.id === pmt.party_id
          ? { ...p, total_paid: p.total_paid + pmt.amount, outstanding: Math.max(0, p.outstanding - pmt.amount) }
          : p
      );
      return ok(pmt, 201);
    }
    
    if (url.match(/^\/payments\/(\d+)\/allocate$/) && method === 'post') {
      const id = Number(url.split('/')[2]);
      const payment = payments.find(p => p.id === id);
      if (!payment) return ok({ detail: 'Not found' }, 404);
      
      for (const alloc of body) {
         payment.unallocated -= alloc.allocated_amount;
         const inv = invoices.find(i => i.id === alloc.invoice_id);
         if (inv) {
           payment.allocations.push({ invoice_id: inv.id, invoice_number: inv.invoice_number, allocated_amount: alloc.allocated_amount });
           inv.balance_due -= alloc.allocated_amount;
           if (inv.balance_due <= 0) inv.is_paid = true;
         }
      }
      return ok(payment);
    }
    if (url.match(/^\/payments\/(\d+)$/) && method === 'get') {
      const id = Number(url.split('/')[2]);
      return ok(payments.find((p) => p.id === id));
    }
    if (url.match(/^\/payments\/(\d+)\/allocations$/)) {
      const id = Number(url.split('/')[2]);
      return ok(payments.find((p) => p.id === id)?.allocations || []);
    }

    // ── Address Book ───────────────────────────────────────────────────────
    if (url === '/address-book/' && method === 'get') {
      const search = (params.search || '').toLowerCase();
      const result = search
        ? addressBook.filter(a => a.name.toLowerCase().includes(search) || a.phone.includes(search) || a.city.toLowerCase().includes(search))
        : addressBook;
      return ok(result);
    }
    if (url === '/address-book/' && method === 'post') {
      const entry = { id: nextAddressId++, ...body, created_at: new Date().toISOString() };
      addressBook.push(entry);
      return ok(entry, 201);
    }
    if (url.match(/^\/address-book\/(\d+)$/) && method === 'put') {
      const id = Number(url.split('/')[2]);
      addressBook = addressBook.map(a => a.id === id ? { ...a, ...body } : a);
      return ok(addressBook.find(a => a.id === id));
    }
    if (url.match(/^\/address-book\/(\d+)$/) && method === 'delete') {
      const id = Number(url.split('/')[2]);
      addressBook = addressBook.filter(a => a.id !== id);
      return ok(null, 204);
    }

    // ── Item Master ────────────────────────────────────────────────────────
    if (url === '/items/' && method === 'get') {
      const search = (params.search || '').toLowerCase();
      const result = search
        ? itemMaster.filter(i => i.item_name.toLowerCase().includes(search))
        : itemMaster;
      return ok(result);
    }
    if (url === '/items/upsert' && method === 'post') {
      // Find existing by name (case-insensitive)
      const existing = itemMaster.find(i => i.item_name.toLowerCase() === (body.item_name || '').toLowerCase());
      if (existing) {
        // Update rate if provided
        if (body.default_rate) itemMaster = itemMaster.map(i => i.id === existing.id ? { ...i, default_rate: body.default_rate } : i);
        return ok(itemMaster.find(i => i.id === existing.id));
      }
      const entry = { id: nextItemId++, item_name: body.item_name, default_rate: body.default_rate || 0 };
      itemMaster.push(entry);
      return ok(entry, 201);
    }
    if (url.match(/^\/items\/(\d+)$/) && method === 'delete') {
      const id = Number(url.split('/')[2]);
      itemMaster = itemMaster.filter(i => i.id !== id);
      return ok(null, 204);
    }

    // ── Analytics ─────────────────────────────────────────────────────────
    if (url === '/analytics/summary') {
      return ok({
        total_parties: parties.filter((p) => p.is_active).length,
        total_invoiced: invoices.reduce((s, i) => s + i.amount, 0),
        total_collected: payments.reduce((s, p) => s + p.amount, 0),
        total_outstanding: parties.reduce((s, p) => s + p.outstanding, 0),
        invoices_count: invoices.length,
        overdue_count: invoices.filter((i) => !i.is_paid && i.due_date && new Date(i.due_date) < new Date()).length,
        recent_payments: payments.slice(-5).reverse(),
      });
    }
    if (url === '/analytics/parties') {
      return ok(parties.filter((p) => p.is_active).map((p) => ({
        party_id: p.id, party_name: p.name,
        total_invoiced: p.total_invoiced, total_paid: p.total_paid, outstanding: p.outstanding,
        invoice_count: invoices.filter((i) => i.party_id === p.id).length,
        payment_count: payments.filter((pmt) => pmt.party_id === p.id).length,
      })).sort((a, b) => b.outstanding - a.outstanding));
    }
    if (url.match(/^\/analytics\/party\/(\d+)$/)) {
      const id = Number(url.split('/')[3]);
      const p = parties.find((x) => x.id === id);
      if (!p) return ok({ detail: 'Not found' }, 404);
      return ok({ party_id: p.id, party_name: p.name, total_invoiced: p.total_invoiced, total_paid: p.total_paid, outstanding: p.outstanding, invoice_count: invoices.filter((i) => i.party_id === id).length, payment_count: payments.filter((pmt) => pmt.party_id === id).length });
    }
    if (url === '/analytics/aging') return ok(AGING);
    // ── Settings ───────────────────────────────────────────────────────────
    if (url === '/settings/unlock-code') return ok({ code: import.meta.env.VITE_UNLOCK_CODE || '2809' });
    if (url === '/settings/app-name')   return ok({ name: import.meta.env.VITE_APP_DISPLAY_NAME || 'My Business' });

    if (url === '/health') return ok({ status: 'ok (mock)', app: 'Maxwell Accounting' });

    // Fallback
    console.warn('[Mock] Unhandled:', method.toUpperCase(), url);
    return ok({ detail: 'Not found (mock)' }, 404);
  };

  console.log('%c[Maxwell Mock] Running in offline demo mode 🎭', 'color: #6c63ff; font-weight: bold;');
}
