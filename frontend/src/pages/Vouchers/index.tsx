import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Plus } from 'lucide-react';
import { vouchersApi } from '../../api/endpoints';
import { formatCurrency, formatDateShort } from '../../utils/format';

export default function VouchersList() {
  const navigate = useNavigate();
  const [voucherType, setVoucherType] = useState('');
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 50;

  const { data, isLoading } = useQuery({
    queryKey: ['vouchers', voucherType, page],
    queryFn: () => vouchersApi.list(voucherType, page * PAGE_SIZE, PAGE_SIZE).then(r => r.data),
  });

  const vouchers = data?.items || [];
  const total = data?.total || 0;

  return (
    <div className="page-content">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 className="page-title">Vouchers</h1>
          <p className="page-subtitle">{total} total entries</p>
        </div>
      </div>

      <div className="search-bar" style={{ display: 'flex', gap: 8, background: 'none', padding: 0 }}>
        <select 
          value={voucherType} 
          onChange={e => { setVoucherType(e.target.value); setPage(0); }}
          style={{ flex: 1, background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 16, padding: '12px 16px', outline: 'none', cursor: 'pointer' }}
        >
          <option value="">All Voucher Types</option>
          <option value="JOURNAL">Journal (JV)</option>
          <option value="CREDIT_NOTE">Credit Note (Sales Return)</option>
          <option value="DEBIT_NOTE">Debit Note (Purchase Return)</option>
          <option value="CONTRA">Contra</option>
          <option value="SALE">Sale</option>
          <option value="RECEIPT">Receipt</option>
          <option value="PURCHASE">Purchase</option>
          <option value="PAYMENT">Payment</option>
        </select>
        
        <button 
          className="btn btn-primary" 
          onClick={() => navigate('/vouchers/journal')}
          style={{ borderRadius: 16, padding: '0 16px' }}
        >
          <Plus size={18} /> New
        </button>
      </div>

      <div className="content-area" style={{ padding: '0 20px', marginTop: 16 }}>
        {isLoading ? (
          <div style={{ textAlign: 'center', padding: 24 }}><div className="spinner" /></div>
        ) : vouchers.length === 0 ? (
          <div className="empty-state">
            <p>No vouchers found.</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {vouchers.map((v: any) => {
              // Calculate total debit
              const amount = v.lines?.reduce((sum: number, line: any) => sum + (Number(line.debit) || 0), 0) || 0;
              


              return (
                <div key={v.id} className="card" style={{ padding: 16 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ 
                          fontSize: 10, 
                          fontWeight: 700, 
                          background: v.voucher_type === 'JOURNAL' ? 'rgba(99,102,241,0.1)' : 'rgba(255,138,138,0.1)', 
                          color: v.voucher_type === 'JOURNAL' ? 'var(--accent)' : 'var(--danger)',
                          padding: '2px 6px', 
                          borderRadius: 4 
                        }}>
                          {v.voucher_type}
                        </span>
                        <p style={{ fontWeight: 600, fontSize: 13 }}>{v.series ? `${v.series}-` : ''}{v.number || `#${v.id}`}</p>
                      </div>
                      <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>{formatDateShort(v.voucher_date)}</p>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <p style={{ fontWeight: 700, fontSize: 15, color: 'var(--text)' }}>
                        {formatCurrency(amount)}
                      </p>
                      <p style={{ fontSize: 11, color: 'var(--success)', marginTop: 2, fontWeight: 600 }}>{v.status}</p>
                    </div>
                  </div>
                  
                  {v.narration && (
                    <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 12, fontStyle: 'italic', background: 'var(--bg-body)', padding: '6px 8px', borderRadius: 6 }}>
                      {v.narration}
                    </p>
                  )}
                  
                  {/* Quick view of lines */}
                  <div style={{ marginTop: 8, fontSize: 11, color: 'var(--text-muted)' }}>
                    {v.lines?.length} lines recorded.
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
      
      {/* Spacer for bottom nav */}
      <div style={{ height: 100 }} />
    </div>
  );
}
