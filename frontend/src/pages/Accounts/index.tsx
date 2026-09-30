import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { accountsApi } from '../../api/endpoints';
import { formatCurrency, formatDate } from '../../utils/format';
import { ChevronLeft, Search, BookOpen, ArrowUpRight, ArrowDownRight } from 'lucide-react';

interface AccountEntry {
  id: number;
  party_id: number;
  party_name: string;
  amount: number;
  entry_date: string;
  description: string;
}

export default function AccountsList() {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null);

  const { data: accounts, isLoading } = useQuery({
    queryKey: ['accounts', search],
    queryFn: () => accountsApi.list(search || undefined),
    select: (res) => res.data,
  });

  const { data: entriesData } = useQuery({
    queryKey: ['account-entries', selectedAccountId],
    queryFn: () => accountsApi.entries(selectedAccountId!, 0, 200),
    select: (res) => res.data,
    enabled: !!selectedAccountId,
  });

  const selectedAccount = accounts?.find((a: any) => a.id === selectedAccountId);

  return (
    <div className="page">
      {!selectedAccountId ? (
        <>
          <div className="page-header">
            <h1 className="page-title">
              <BookOpen size={22} style={{ marginRight: 8 }} />
              Master Accounts
            </h1>
          </div>

          <div className="search-bar">
            <Search size={18} />
            <input
              placeholder="Search accounts..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          {isLoading ? (
            <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>Loading...</div>
          ) : !accounts?.length ? (
            <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>No accounts found</div>
          ) : (
            <div className="list">
              {accounts.map((acct: any) => {
                const total = Number(acct.total_amount || 0);
                const isExpense = total < 0;
                return (
                  <div
                    key={acct.id}
                    className="list-item"
                    onClick={() => setSelectedAccountId(acct.id)}
                    style={{ cursor: 'pointer' }}
                  >
                    <div style={{ flex: 1 }}>
                      <p className="list-item-title" style={{ fontSize: 15, fontWeight: 600 }}>{acct.name}</p>
                      <p className="list-item-sub">
                        {acct.group_name || 'General'} · {acct.entry_count} entries
                      </p>
                    </div>
                    <div className="list-item-right" style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
                      <p style={{
                        fontWeight: 700,
                        fontSize: 15,
                        color: isExpense ? 'var(--danger)' : 'var(--success)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 4
                      }}>
                        {isExpense ? <ArrowDownRight size={14} /> : <ArrowUpRight size={14} />}
                        {formatCurrency(Math.abs(total))}
                      </p>
                      <span className="badge" style={{
                        marginTop: 4,
                        fontSize: 10,
                        background: isExpense ? 'rgba(239,68,68,0.12)' : 'rgba(34,197,94,0.12)',
                        color: isExpense ? 'var(--danger)' : 'var(--success)',
                      }}>
                        {isExpense ? 'Expense' : 'Income'}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </>
      ) : (
        /* Account Detail View */
        <>
          <div className="page-header">
            <button className="btn btn-sm btn-secondary" onClick={() => setSelectedAccountId(null)}>
              <ChevronLeft size={16} /> Back
            </button>
            <h1 className="page-title" style={{ fontSize: 18 }}>
              {selectedAccount?.name || 'Account'}
            </h1>
          </div>

          {/* Summary Card */}
          {selectedAccount && (
            <div style={{
              background: 'var(--surface)',
              borderRadius: 16,
              padding: '20px 24px',
              marginBottom: 20,
              border: '1px solid var(--border)',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
                <div>
                  <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>Group</p>
                  <p style={{ fontSize: 14, fontWeight: 600 }}>{selectedAccount.group_name || 'General'}</p>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>Total Entries</p>
                  <p style={{ fontSize: 14, fontWeight: 600 }}>{selectedAccount.entry_count}</p>
                </div>
              </div>
              <div style={{
                background: 'var(--background)',
                borderRadius: 12,
                padding: '16px 20px',
                textAlign: 'center',
              }}>
                <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>Net Amount</p>
                <p style={{
                  fontSize: 24,
                  fontWeight: 800,
                  color: Number(selectedAccount.total_amount) < 0 ? 'var(--danger)' : 'var(--success)',
                }}>
                  {formatCurrency(Math.abs(Number(selectedAccount.total_amount)))}
                </p>
              </div>
            </div>
          )}

          {/* Entry List */}
          <h2 style={{ fontSize: 15, fontWeight: 700, marginBottom: 12, color: 'var(--text-primary)' }}>
            Journal Entries
          </h2>
          <div className="list">
            {entriesData?.entries?.map((entry: AccountEntry) => {
              const isDebit = entry.amount > 0;
              return (
                <div
                  key={entry.id}
                  className="list-item"
                  onClick={() => navigate(`/parties/${entry.party_id}`)}
                  style={{ cursor: 'pointer' }}
                >
                  <div style={{ flex: 1 }}>
                    <p style={{ fontSize: 14, fontWeight: 600 }}>{entry.party_name}</p>
                    <p className="list-item-sub">{formatDate(entry.entry_date)}</p>
                    {entry.description && (
                      <p className="list-item-sub" style={{ fontSize: 11 }}>{entry.description}</p>
                    )}
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <p style={{
                      fontWeight: 700,
                      fontSize: 14,
                      color: isDebit ? 'var(--danger)' : 'var(--success)',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 4,
                    }}>
                      {isDebit ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                      {formatCurrency(Math.abs(entry.amount))}
                    </p>
                    <span className="badge" style={{
                      marginTop: 4,
                      fontSize: 10,
                      background: isDebit ? 'rgba(239,68,68,0.12)' : 'rgba(34,197,94,0.12)',
                      color: isDebit ? 'var(--danger)' : 'var(--success)',
                    }}>
                      {isDebit ? 'Dr' : 'Cr'}
                    </span>
                  </div>
                </div>
              );
            })}
            {(!entriesData?.entries || entriesData.entries.length === 0) && (
              <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
                No entries found
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
