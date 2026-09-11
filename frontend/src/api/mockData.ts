// Mock data for offline demo mode (VITE_MOCK=true)

// ── Dummy Parties ────────────────────────────────────────────────────────────
export const PARTIES = [
  {
    id: 1, name: 'Sharma Traders', phone: '+91 98765 43210',
    email: 'sharma@traders.in', agent_name: 'Agent Ramesh',
    billing_address_line1: '12, Nehru Market', billing_address_line2: 'Block C', billing_address_line3: '', billing_city: 'Delhi',
    shipping_address_line1: 'Warehouse 4', shipping_address_line2: 'Okhla Phase 1', shipping_address_line3: '', shipping_city: 'Delhi',
    gstin: '07AABCS1429B1ZB', notes: 'Regular buyer, credit 30 days',
    is_active: true, created_at: '2026-01-05T08:00:00Z',
    total_invoiced: 145000, total_paid: 95000, outstanding: 50000,
  },
  {
    id: 2, name: 'Mehta Electronics', phone: '+91 91234 56789',
    email: 'mehta@electronics.com', agent_name: 'Agent Suresh',
    billing_address_line1: '5, MG Road', billing_address_line2: '', billing_address_line3: '', billing_city: 'Bangalore',
    shipping_address_line1: '5, MG Road', shipping_address_line2: '', shipping_address_line3: '', shipping_city: 'Bangalore',
    gstin: '29AAECM4207J1ZR', notes: 'Large orders, net 45',
    is_active: true, created_at: '2026-01-12T09:30:00Z',
    total_invoiced: 320000, total_paid: 280000, outstanding: 40000,
  },
  {
    id: 3, name: 'Kapoor Textiles', phone: '+91 99887 76655',
    email: 'kapoor@textiles.co', agent_name: '',
    billing_address_line1: '88, Sadar Bazaar', billing_address_line2: '', billing_address_line3: '', billing_city: 'Jaipur',
    shipping_address_line1: '88, Sadar Bazaar', shipping_address_line2: '', shipping_address_line3: '', shipping_city: 'Jaipur',
    gstin: '08AAHCK2310P1ZS', notes: '',
    is_active: true, created_at: '2026-02-03T10:00:00Z',
    total_invoiced: 87500, total_paid: 87500, outstanding: 0,
  },
  {
    id: 4, name: 'Singh Hardware', phone: '+91 87654 32109',
    email: null, agent_name: 'Agent Ramesh',
    billing_address_line1: '3, Industrial Area', billing_address_line2: '', billing_address_line3: '', billing_city: 'Ludhiana',
    shipping_address_line1: '3, Industrial Area', shipping_address_line2: '', shipping_address_line3: '', shipping_city: 'Ludhiana',
    gstin: null, notes: 'Cash preferred',
    is_active: true, created_at: '2026-03-01T11:00:00Z',
    total_invoiced: 56000, total_paid: 12000, outstanding: 44000,
  },
];

// ── Dummy Invoices ────────────────────────────────────────────────────────────
export const INVOICES = [
  { id: 1, invoice_number: 'INV-00001', party_id: 1, amount: 45000, balance_due: 0,       description: 'Office stationery supplies Q1', invoice_date: '2026-01-10T00:00:00Z', due_date: '2026-02-10T00:00:00Z', is_paid: true,  created_at: '2026-01-10T08:00:00Z', items: [{id:1, invoice_id:1, item_name:'Pens', meter: 100, rate: 450, total: 45000}], billing_address: '12, Nehru Market, Delhi', shipping_address: 'Warehouse 4, Delhi' },
  { id: 2, invoice_number: 'INV-00002', party_id: 1, amount: 50000, balance_due: 20000,    description: 'Paper reams & toner cartridges', invoice_date: '2026-02-15T00:00:00Z', due_date: '2026-03-15T00:00:00Z', is_paid: false, created_at: '2026-02-15T08:00:00Z', items: [{id:2, invoice_id:2, item_name:'Paper Reams', meter: 250, rate: 200, total: 50000}], billing_address: '12, Nehru Market, Delhi', shipping_address: 'Warehouse 4, Delhi' },
  { id: 3, invoice_number: 'INV-00003', party_id: 1, amount: 50000, balance_due: 30000,    description: 'Printer consumables March', invoice_date: '2026-03-20T00:00:00Z', due_date: '2026-04-20T00:00:00Z', is_paid: false, created_at: '2026-03-20T08:00:00Z', items: [{id:3, invoice_id:3, item_name:'Toner Cartridges', meter: 10, rate: 5000, total: 50000}], billing_address: '12, Nehru Market, Delhi', shipping_address: 'Warehouse 4, Delhi' },
  { id: 4, invoice_number: 'INV-00004', party_id: 2, amount: 180000, balance_due: 0,       description: 'LED TV 55" x6 units', invoice_date: '2026-01-18T00:00:00Z', due_date: '2026-03-18T00:00:00Z', is_paid: true,  created_at: '2026-01-18T08:00:00Z', items: [{id:4, invoice_id:4, item_name:'LED TV 55"', meter: 6, rate: 30000, total: 180000}], billing_address: '5, MG Road, Bangalore', shipping_address: '5, MG Road, Bangalore' },
  { id: 5, invoice_number: 'INV-00005', party_id: 2, amount: 140000, balance_due: 40000,   description: 'Laptops & accessories batch 2', invoice_date: '2026-03-05T00:00:00Z', due_date: '2026-05-05T00:00:00Z', is_paid: false, created_at: '2026-03-05T08:00:00Z', items: [{id:5, invoice_id:5, item_name:'Laptops', meter: 4, rate: 35000, total: 140000}], billing_address: '5, MG Road, Bangalore', shipping_address: '5, MG Road, Bangalore' },
  { id: 6, invoice_number: 'INV-00006', party_id: 3, amount: 87500, balance_due: 0,        description: 'Cotton fabric 500m order', invoice_date: '2026-02-08T00:00:00Z', due_date: '2026-03-08T00:00:00Z', is_paid: true,  created_at: '2026-02-08T08:00:00Z', items: [{id:6, invoice_id:6, item_name:'Cotton Fabric', meter: 500, rate: 175, total: 87500}], billing_address: '88, Sadar Bazaar, Jaipur', shipping_address: '88, Sadar Bazaar, Jaipur' },
  { id: 7, invoice_number: 'INV-00007', party_id: 4, amount: 32000, balance_due: 32000,    description: 'Bolts, nuts & fasteners bulk', invoice_date: '2026-04-01T00:00:00Z', due_date: '2026-05-01T00:00:00Z', is_paid: false, created_at: '2026-04-01T08:00:00Z', items: [{id:7, invoice_id:7, item_name:'Fasteners', meter: 160, rate: 200, total: 32000}], billing_address: '3, Industrial Area, Ludhiana', shipping_address: '3, Industrial Area, Ludhiana' },
  { id: 8, invoice_number: 'INV-00008', party_id: 4, amount: 24000, balance_due: 12000,    description: 'Power tools & equipment', invoice_date: '2026-04-20T00:00:00Z', due_date: '2026-05-20T00:00:00Z', is_paid: false, created_at: '2026-04-20T08:00:00Z', items: [{id:8, invoice_id:8, item_name:'Power Tools', meter: 12, rate: 2000, total: 24000}], billing_address: '3, Industrial Area, Ludhiana', shipping_address: '3, Industrial Area, Ludhiana' },
];

// ── Dummy Payments ────────────────────────────────────────────────────────────
export const PAYMENTS = [
  {
    id: 1, party_id: 1, amount: 75000, unallocated: 0,
    payment_date: '2026-02-05T00:00:00Z', note: 'NEFT transfer', mode: 'bank',
    created_at: '2026-02-05T09:00:00Z',
    allocations: [
      { invoice_id: 1, invoice_number: 'INV-00001', allocated_amount: 45000 },
      { invoice_id: 2, invoice_number: 'INV-00002', allocated_amount: 30000 },
    ],
  },
  {
    id: 2, party_id: 2, amount: 180000, unallocated: 0,
    payment_date: '2026-03-10T00:00:00Z', note: 'Cheque #0045321', mode: 'cheque',
    created_at: '2026-03-10T09:00:00Z',
    allocations: [
      { invoice_id: 4, invoice_number: 'INV-00004', allocated_amount: 180000 },
    ],
  },
  {
    id: 3, party_id: 3, amount: 87500, unallocated: 0,
    payment_date: '2026-03-01T00:00:00Z', note: 'Cash payment', mode: 'cash',
    created_at: '2026-03-01T09:00:00Z',
    allocations: [
      { invoice_id: 6, invoice_number: 'INV-00006', allocated_amount: 87500 },
    ],
  },
  {
    id: 4, party_id: 4, amount: 12000, unallocated: 0,
    payment_date: '2026-04-25T00:00:00Z', note: 'Partial advance UPI', mode: 'upi',
    created_at: '2026-04-25T09:00:00Z',
    allocations: [
      { invoice_id: 7, invoice_number: 'INV-00007', allocated_amount: 12000 },
    ],
  },
  {
    id: 5, party_id: 2, amount: 100000, unallocated: 0,
    payment_date: '2026-04-15T00:00:00Z', note: 'Partial payment for laptops', mode: 'bank',
    created_at: '2026-04-15T09:00:00Z',
    allocations: [
      { invoice_id: 5, invoice_number: 'INV-00005', allocated_amount: 100000 },
    ],
  },
];

// ── Ledger helper ────────────────────────────────────────────────────────────
export function buildLedger(partyId: number) {
  const invoices = INVOICES.filter((i) => i.party_id === partyId);
  const payments = PAYMENTS.filter((p) => p.party_id === partyId);

  const entries: any[] = [
    ...invoices.map((i) => ({ type: 'invoice', date: i.invoice_date, reference: i.invoice_number, amount: i.amount, balance_due: i.balance_due })),
    ...payments.map((p) => ({ type: 'payment', date: p.payment_date, reference: `PMT-${p.id}`, amount: -p.amount, balance_due: null })),
  ].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

  let running = 0;
  return entries.map((e) => {
    running += e.amount;
    return { ...e, running_balance: running };
  });
}

// ── Analytics helpers ─────────────────────────────────────────────────────────
export const DASHBOARD_SUMMARY = {
  total_parties: PARTIES.length,
  total_invoiced: INVOICES.reduce((s, i) => s + i.amount, 0),
  total_collected: PAYMENTS.reduce((s, p) => s + p.amount, 0),
  total_outstanding: PARTIES.reduce((s, p) => s + p.outstanding, 0),
  invoices_count: INVOICES.length,
  overdue_count: 3,
  recent_payments: PAYMENTS.slice(0, 5),
};

export const AGING = [
  { party_id: 4, party_name: 'Singh Hardware', current: 12000, days_31_60: 32000, days_61_90: 0, over_90: 0, total: 44000 },
  { party_id: 1, party_name: 'Sharma Traders',  current: 30000, days_31_60: 20000, days_61_90: 0, over_90: 0, total: 50000 },
  { party_id: 2, party_name: 'Mehta Electronics', current: 40000, days_31_60: 0,   days_61_90: 0, over_90: 0, total: 40000 },
];
