import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../api/client';
import { formatCurrency, formatDateShort } from '../../utils/format';
import { ArrowLeft, Download } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function DayBook() {
  const navigate = useNavigate();
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);

  const { data: vouchers = [], isLoading } = useQuery({
    queryKey: ['day-book', date],
    queryFn: () => api.get('/vouchers/', { params: { limit: 1000 } }).then(r => {
      // Temporary client-side filter until backend supports date filtering for vouchers
      const all = r.data.items || [];
      return all.filter((v: any) => v.voucher_date.startsWith(date));
    }),
  });

  // Calculate totals
  let totalDebit = 0;
  let totalCredit = 0;

  vouchers.forEach((v: any) => {
    if (v.status !== 'POSTED') return;
    v.lines?.forEach((l: any) => {
      totalDebit += Number(l.debit) || 0;
      totalCredit += Number(l.credit) || 0;
    });
  });

  return (
    <div className="page-layout">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button onClick={() => navigate(-1)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)' }}>
            <ArrowLeft size={20} />
          </button>
          <h1 className="page-title" style={{ margin: 0 }}>Day Book</h1>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn-icon" style={{ color: 'var(--text-secondary)' }}>
            <Download size={20} />
          </button>
        </div>
      </div>

      <div className="search-bar-container" style={{ padding: '0 20px', marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <input 
            type="date" 
            className="form-input" 
            value={date} 
            onChange={e => setDate(e.target.value)}
            style={{ width: 160 }}
          />
          <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Showing transactions for {formatDateShort(date)}</span>
        </div>
      </div>

      <div className="content-area" style={{ padding: '0 20px' }}>
        <div className="stats-grid" style={{ marginBottom: 16 }}>
          <div className="stat-card" style={{ borderColor: 'var(--accent)' }}>
            <p className="stat-label">Total Debit Turnover</p>
            <p className="stat-value mono" style={{ fontSize: 16, color: 'var(--text)' }}>{formatCurrency(totalDebit)}</p>
          </div>
          <div className="stat-card" style={{ borderColor: 'var(--success)' }}>
            <p className="stat-label">Total Credit Turnover</p>
            <p className="stat-value mono" style={{ fontSize: 16, color: 'var(--text)' }}>{formatCurrency(totalCredit)}</p>
          </div>
        </div>

        <div className="card" style={{ overflowX: 'auto' }}>
          {isLoading ? (
            <div style={{ padding: 24, textAlign: 'center' }}>Loading day book...</div>
          ) : vouchers.length === 0 ? (
            <div className="empty-state"><p>No transactions found on this date.</p></div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: 'var(--surface)', borderBottom: '1px solid var(--border)', textAlign: 'left' }}>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>Type / Ref</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>Account / Particulars</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'right' }}>Debit (₹)</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'right' }}>Credit (₹)</th>
                </tr>
              </thead>
              <tbody>
                {vouchers.map((v: any) => (
                  <React.Fragment key={v.id}>
                    <tr style={{ background: 'var(--bg-body)' }}>
                      <td colSpan={4} style={{ padding: '8px 16px', fontSize: 11, fontWeight: 700, color: 'var(--text-secondary)', borderTop: '1px solid var(--border)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                          <span>{v.voucher_type} {v.series ? `${v.series}-` : ''}{v.number || `#${v.id}`}</span>
                          <span style={{ color: v.status === 'REVERSED' || v.status === 'CANCELLED' ? 'var(--danger)' : 'var(--text-muted)' }}>{v.status}</span>
                        </div>
                      </td>
                    </tr>
                    {v.lines?.map((line: any) => (
                      <tr key={line.id} style={{ borderBottom: '1px solid var(--border)', opacity: v.status === 'REVERSED' || v.status === 'CANCELLED' ? 0.5 : 1 }}>
                        <td style={{ padding: '8px 16px' }}></td>
                        <td style={{ padding: '8px 16px' }}>
                          <span style={{ fontWeight: 600 }}>{line.account?.name || `Account ${line.account_id}`}</span>
                          {line.party && <span style={{ marginLeft: 6, fontSize: 11, color: 'var(--accent)', background: 'var(--accent-glow)', padding: '2px 6px', borderRadius: 4 }}>{line.party.name}</span>}
                          {line.line_narration && <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{line.line_narration}</div>}
                        </td>
                        <td style={{ padding: '8px 16px', textAlign: 'right', fontWeight: parseFloat(line.debit) > 0 ? 600 : 400 }}>
                          {parseFloat(line.debit) > 0 ? formatCurrency(line.debit) : ''}
                        </td>
                        <td style={{ padding: '8px 16px', textAlign: 'right', fontWeight: parseFloat(line.credit) > 0 ? 600 : 400 }}>
                          {parseFloat(line.credit) > 0 ? formatCurrency(line.credit) : ''}
                        </td>
                      </tr>
                    ))}
                    {v.narration && (
                      <tr style={{ borderBottom: '1px solid var(--border)' }}>
                        <td></td>
                        <td colSpan={3} style={{ padding: '4px 16px 8px 16px', fontSize: 11, fontStyle: 'italic', color: 'var(--text-muted)' }}>
                          Narration: {v.narration}
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
