import { useState, useEffect } from 'react';
import { useInfiniteQuery } from '@tanstack/react-query';
import { useInView } from 'react-intersection-observer';
import { useNavigate } from 'react-router-dom';
import { partiesApi } from '../../api/endpoints';
import { formatCurrency, formatDate } from '../../utils/format';
import { Search, CalendarClock, PhoneCall, User, X } from 'lucide-react';

import CalculationEvidence from '../../components/CalculationEvidence';

export default function PendingDues() {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  
  const { ref, inView } = useInView();

  const {
    data,
    isLoading,
    fetchNextPage,
    hasNextPage,
  } = useInfiniteQuery({
    queryKey: ['pending_dues', search],
    queryFn: ({ pageParam = 0 }) => partiesApi.list(search, pageParam, 20, true).then(r => r.data),
    getNextPageParam: (lastPage) => {
      if (lastPage.skip + lastPage.limit < lastPage.total) {
        return lastPage.skip + lastPage.limit;
      }
      return undefined;
    },
    initialPageParam: 0,
  });

  useEffect(() => {
    if (inView && hasNextPage) {
      fetchNextPage();
    }
  }, [inView, hasNextPage, fetchNextPage]);

  const pendingParties = data ? data.pages.flatMap((page) => page.items) : [];

  // Sort by reminder date (earliest first), then by outstanding amount (highest first)
  const sortedParties = [...pendingParties].sort((a: any, b: any) => {
    if (a.reminder_date && b.reminder_date) {
      return new Date(a.reminder_date).getTime() - new Date(b.reminder_date).getTime();
    }
    if (a.reminder_date) return -1;
    if (b.reminder_date) return 1;
    return b.outstanding - a.outstanding;
  });

  const isReminderOverdue = (dateString?: string) => {
    if (!dateString) return false;
    return new Date(dateString).getTime() < new Date().getTime();
  };

  return (
    <div className="page-container pop-in">
      <div className="page-header" style={{ marginBottom: 16 }}>
        <h1 className="page-title">Pending Dues</h1>
        <p className="page-subtitle">Outstanding balances to collect</p>
      </div>

      <div className="search-bar" style={{ marginBottom: 24 }}>
        <Search size={16} />
        <input
          placeholder="Search by name…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        {search && <button onClick={() => setSearch('')} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}><X size={14} /></button>}
      </div>

      {isLoading ? (
        <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>Loading...</div>
      ) : sortedParties.length === 0 ? (
        <div className="empty-state">
          <CalendarClock size={48} style={{ color: 'var(--success)' }} />
          <h3>All caught up!</h3>
          <p>There are no pending dues to collect.</p>
        </div>
      ) : (
        <div className="list-container">
          {sortedParties.map((p: any) => {
            const overdue = isReminderOverdue(p.reminder_date);
            return (
              <div 
                key={p.id} 
                className="list-item" 
                onClick={() => navigate(`/parties/${p.id}`)}
                style={{ 
                  borderLeft: overdue ? '4px solid var(--danger)' : p.reminder_date ? '4px solid var(--warning)' : 'none',
                  paddingLeft: (overdue || p.reminder_date) ? 12 : 16
                }}
              >
                <div className="list-item-icon" style={{ background: 'var(--bg-elevated)', color: 'var(--text-primary)' }}>
                  <User size={20} />
                </div>
                <div className="list-item-body">
                  <p className="list-item-title" style={{ fontSize: 16 }}>{p.name}</p>
                  <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginTop: 4 }}>
                    {p.area && <span style={{ fontSize: 12, color: 'var(--text-muted)', background: 'var(--bg-base)', padding: '2px 6px', borderRadius: 4 }}>{p.area}</span>}
                    {p.reminder_date && (
                      <span style={{ fontSize: 12, color: overdue ? 'var(--danger)' : 'var(--warning)', display: 'flex', alignItems: 'center', gap: 4, fontWeight: 600 }}>
                        <CalendarClock size={12} /> {formatDate(p.reminder_date)} {overdue && '(Overdue)'}
                      </span>
                    )}
                  </div>
                </div>
                <div className="list-item-right" style={{ textAlign: 'right' }}>
                  <CalculationEvidence
                    title={`${p.name} Outstanding`}
                    items={[
                      { label: 'Total Invoiced', value: p.total_invoiced || 0, operator: '+' },
                      { label: 'Journal Adjustments', value: p.total_journal || 0, operator: p.total_journal >= 0 ? '+' : '-' },
                      { label: 'Total Paid', value: p.total_paid || 0, operator: '-' },
                      { label: 'Outstanding Due', value: p.outstanding || 0, operator: '=' }
                    ]}
                  >
                    <p style={{ color: 'var(--danger)', fontWeight: 700, fontSize: 16 }}>
                      {formatCurrency(p.outstanding)}
                    </p>
                  </CalculationEvidence>
                  {/* F18: Collection % */}
                  {(p.total_invoiced || 0) > 0 && (
                    <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                      Collected{' '}
                      <span style={{ color: 'var(--success)', fontWeight: 600 }}>
                        {Math.round(((p.total_paid || 0) / (p.total_invoiced || 1)) * 100)}%
                      </span>
                    </p>
                  )}
                  {p.phone && (
                    <a href={`tel:${p.phone}`} onClick={(e) => e.stopPropagation()} style={{ color: 'var(--accent)', display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 13, marginTop: 4, textDecoration: 'none', fontWeight: 500 }}>
                      <PhoneCall size={12} /> Call
                    </a>
                  )}
                </div>
              </div>
            );
          })}
          {hasNextPage && (
            <div ref={ref} style={{ padding: '20px 0', textAlign: 'center' }}>
              <div className="spinner" style={{ width: 24, height: 24, borderWidth: 3 }} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
