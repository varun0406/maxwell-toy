import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { partiesApi } from '../../api/endpoints';
import { formatCurrency, formatDate } from '../../utils/format';
import { Filter, CalendarClock, PhoneCall, User } from 'lucide-react';

export default function PendingDues() {
  const navigate = useNavigate();
  const [areaFilter, setAreaFilter] = useState<string>('');

  const { data: parties = [], isLoading } = useQuery({
    queryKey: ['parties'],
    queryFn: () => partiesApi.list().then((res) => res.data),
  });

  // Get all parties with outstanding > 0
  const pendingParties = parties.filter((p: any) => p.outstanding > 0);

  // Get unique areas
  const areas = Array.from(new Set(pendingParties.map((p: any) => p.area).filter(Boolean))) as string[];

  // Apply filters
  const filteredParties = pendingParties.filter((p: any) => 
    areaFilter ? p.area === areaFilter : true
  );

  // Sort by reminder date (earliest first), then by outstanding amount (highest first)
  const sortedParties = [...filteredParties].sort((a: any, b: any) => {
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

      {areas.length > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24, overflowX: 'auto', paddingBottom: 4 }}>
          <Filter size={18} style={{ color: 'var(--text-muted)' }} />
          <button 
            className="btn" 
            style={{ 
              borderRadius: 20, 
              padding: '6px 16px', 
              fontSize: 13, 
              background: areaFilter === '' ? 'var(--accent)' : 'var(--bg-elevated)',
              color: areaFilter === '' ? '#fff' : 'var(--text-primary)',
              border: areaFilter === '' ? 'none' : '1px solid var(--border)',
            }}
            onClick={() => setAreaFilter('')}
          >
            All Areas
          </button>
          {areas.map(area => (
            <button 
              key={area}
              className="btn" 
              style={{ 
                borderRadius: 20, 
                padding: '6px 16px', 
                fontSize: 13, 
                background: areaFilter === area ? 'var(--accent)' : 'var(--bg-elevated)',
                color: areaFilter === area ? '#fff' : 'var(--text-primary)',
                border: areaFilter === area ? 'none' : '1px solid var(--border)',
                whiteSpace: 'nowrap'
              }}
              onClick={() => setAreaFilter(area)}
            >
              {area}
            </button>
          ))}
        </div>
      )}

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
                  <p style={{ color: 'var(--danger)', fontWeight: 700, fontSize: 16 }}>
                    {formatCurrency(p.outstanding)}
                  </p>
                  {p.phone && (
                    <a href={`tel:${p.phone}`} onClick={(e) => e.stopPropagation()} style={{ color: 'var(--accent)', display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 13, marginTop: 4, textDecoration: 'none', fontWeight: 500 }}>
                      <PhoneCall size={12} /> Call
                    </a>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
