import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { ChevronLeft, Search, X, Tag, TrendingDown, TrendingUp, Minus } from 'lucide-react';
import { partiesApi } from '../../api/endpoints';
import { formatCurrency, formatDateShort } from '../../utils/format';
import { SearchCombobox } from '../../components/SearchCombobox';
import type { ComboboxOption } from '../../components/SearchCombobox';
import { useDebouncedValue } from '../../hooks/useDebouncedValue';

export default function RateBook() {
  const navigate = useNavigate();
  const [partySearch, setPartySearch] = useState('');
  const [partyId, setPartyId] = useState<number | null>(null);
  const [partyName, setPartyName] = useState('');
  const [itemSearch, setItemSearch] = useState('');
  const [selectedItem, setSelectedItem] = useState<string | null>(null);

  const debouncedItemSearch = useDebouncedValue(itemSearch, 300);

  const { data: parties = [] } = useQuery({
    queryKey: ['ratebook-parties', partySearch],
    queryFn: () => partiesApi.list(partySearch, 0, 100).then(r => r.data.items || []),
  });

  const partyOptions: ComboboxOption[] = parties.map((p: any) => ({
    value: p.id,
    label: p.name,
    sublabel: p.billing_city || '',
  }));

  const { data: itemRates = [], isLoading: ratesLoading } = useQuery({
    queryKey: ['item-rates', partyId],
    queryFn: () => partiesApi.itemRates(partyId!).then(r => r.data),
    enabled: !!partyId,
  });

  const { data: itemHistory = [], isLoading: histLoading } = useQuery({
    queryKey: ['item-history', partyId, selectedItem],
    queryFn: () => partiesApi.itemHistory(partyId!, selectedItem!).then(r => r.data),
    enabled: !!partyId && !!selectedItem,
  });

  const filteredRates = (itemRates as any[]).filter((item: any) =>
    !debouncedItemSearch || item.item_name.toLowerCase().includes(debouncedItemSearch.toLowerCase())
  );

  // Rate trend indicator compared to previous entries
  const getRateTrend = (item: any) => {
    // We'll get trend from history if selected
    if (selectedItem === item.item_name && itemHistory.length >= 2) {
      const latest = Number((itemHistory as any[])[0].rate);
      const prev = Number((itemHistory as any[])[1].rate);
      if (latest > prev) return 'up';
      if (latest < prev) return 'down';
      return 'same';
    }
    return null;
  };

  return (
    <div className="page-content">
      <div className="page-header" style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <button className="btn-icon btn" onClick={() => navigate(-1)} title="Back">
          <ChevronLeft size={20} />
        </button>
        <div>
          <h1 className="page-title">Rate Book</h1>
          <p className="page-subtitle">Party × Item last rate & history</p>
        </div>
      </div>

      {/* Party Selector */}
      <div style={{ padding: '0 20px', marginBottom: 16 }}>
        <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6, display: 'block' }}>
          SELECT PARTY
        </label>
        <SearchCombobox
          value={partyId}
          placeholder="Search and select party…"
          options={partyOptions}
          onChange={opt => {
            setPartyId(Number(opt.value));
            setPartyName(opt.label);
            setSelectedItem(null);
            setItemSearch('');
          }}
          onSearch={setPartySearch}
        />
      </div>

      {!partyId && (
        <div className="empty-state" style={{ marginTop: 32 }}>
          <Tag size={48} style={{ color: 'var(--accent)' }} />
          <h3>Choose a Party</h3>
          <p>Select a party above to see all items sold and their last rates</p>
        </div>
      )}

      {partyId && (
        <>
          {/* Search items */}
          <div style={{ padding: '0 20px', marginBottom: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', background: 'var(--surface)', padding: '10px 16px', borderRadius: 14, border: '1px solid var(--border)', gap: 8 }}>
              <Search size={15} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
              <input
                placeholder="Search items…"
                value={itemSearch}
                onChange={e => setItemSearch(e.target.value)}
                style={{ border: 'none', background: 'transparent', flex: 1, outline: 'none', fontSize: 14 }}
              />
              {itemSearch && (
                <button onClick={() => setItemSearch('')} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
                  <X size={14} />
                </button>
              )}
            </div>
          </div>

          <div style={{ display: 'flex', gap: 0, height: 'calc(100vh - 280px)', padding: '0 20px' }}>
            {/* Item List */}
            <div style={{ flex: '0 0 auto', width: selectedItem ? '45%' : '100%', overflowY: 'auto', transition: 'width 0.2s' }}>
              {ratesLoading ? (
                <div style={{ textAlign: 'center', padding: 24 }}><div className="spinner" /></div>
              ) : filteredRates.length === 0 ? (
                <div className="empty-state">
                  <Tag size={36} />
                  <p>{itemSearch ? 'No items match your search' : 'No items found for this party'}</p>
                </div>
              ) : (
                <div>
                  <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8, fontWeight: 600 }}>
                    {filteredRates.length} ITEMS — {partyName}
                  </p>
                  {filteredRates.map((item: any) => {
                    const isSelected = selectedItem === item.item_name;
                    const trend = getRateTrend(item);
                    return (
                      <div
                        key={item.item_name}
                        onClick={() => setSelectedItem(isSelected ? null : item.item_name)}
                        style={{
                          padding: '12px 14px',
                          borderRadius: 12,
                          marginBottom: 8,
                          cursor: 'pointer',
                          border: `1.5px solid ${isSelected ? 'var(--accent)' : 'var(--border)'}`,
                          background: isSelected ? 'var(--accent-glow)' : 'var(--bg-card)',
                          transition: 'all 0.15s',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                          <div style={{ flex: 1, minWidth: 0, marginRight: 8 }}>
                            <p style={{
                              fontWeight: 600,
                              fontSize: 13,
                              color: isSelected ? 'var(--accent-dark)' : 'var(--text)',
                              whiteSpace: 'nowrap',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                            }}>
                              {item.item_name}
                            </p>
                            <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 3 }}>
                              {item.invoice_count} {item.invoice_count === 1 ? 'invoice' : 'invoices'} · Last: {formatDateShort(item.last_date)}
                            </p>
                          </div>
                          <div style={{ textAlign: 'right', flexShrink: 0 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 4, justifyContent: 'flex-end' }}>
                              {trend === 'up' && <TrendingUp size={12} style={{ color: 'var(--warning)' }} />}
                              {trend === 'down' && <TrendingDown size={12} style={{ color: 'var(--success)' }} />}
                              {trend === 'same' && <Minus size={12} style={{ color: 'var(--text-muted)' }} />}
                              <span style={{ fontWeight: 700, fontSize: 14, color: isSelected ? 'var(--accent-dark)' : 'var(--accent)' }}>
                                ₹{Number(item.last_rate).toFixed(2)}
                              </span>
                            </div>
                            <p style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>last rate / metre</p>
                          </div>
                        </div>
                        {/* Total sold to this party */}
                        <div style={{ display: 'flex', gap: 12, marginTop: 8, fontSize: 11, color: 'var(--text-muted)' }}>
                          <span>Total: {Number(item.total_meter).toFixed(2)} m</span>
                          <span>Value: {formatCurrency(item.total_amount)}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Item History Panel */}
            {selectedItem && (
              <div style={{
                flex: 1,
                marginLeft: 12,
                overflowY: 'auto',
                background: 'var(--bg-card)',
                borderRadius: 16,
                border: '1px solid var(--border)',
                padding: '14px 14px',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                  <div>
                    <p style={{ fontWeight: 700, fontSize: 13, color: 'var(--accent-dark)' }}>{selectedItem}</p>
                    <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>Rate history</p>
                  </div>
                  <button
                    onClick={() => setSelectedItem(null)}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 4 }}
                  >
                    <X size={16} />
                  </button>
                </div>

                {histLoading ? (
                  <div style={{ textAlign: 'center', padding: 16 }}><div className="spinner" /></div>
                ) : (itemHistory as any[]).length === 0 ? (
                  <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>No history found.</p>
                ) : (
                  <div>
                    {(itemHistory as any[]).map((entry: any, i: number) => {
                      const prevRate = i < (itemHistory as any[]).length - 1 ? Number((itemHistory as any[])[i + 1].rate) : null;
                      const rateChange = prevRate !== null ? Number(entry.rate) - prevRate : null;
                      return (
                        <div
                          key={`${entry.invoice_number}-${i}`}
                          style={{
                            padding: '10px 0',
                            borderBottom: i < (itemHistory as any[]).length - 1 ? '1px solid var(--border)' : 'none',
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <div>
                              <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)' }}>{entry.invoice_number}</p>
                              <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>{formatDateShort(entry.invoice_date)}</p>
                            </div>
                            <div style={{ textAlign: 'right' }}>
                              <p style={{ fontWeight: 700, fontSize: 14, color: i === 0 ? 'var(--accent)' : 'var(--text)' }}>
                                ₹{Number(entry.rate).toFixed(2)}
                              </p>
                              {rateChange !== null && (
                                <p style={{ fontSize: 11, color: rateChange > 0 ? 'var(--warning)' : rateChange < 0 ? 'var(--success)' : 'var(--text-muted)' }}>
                                  {rateChange > 0 ? `+${rateChange.toFixed(2)}` : rateChange < 0 ? rateChange.toFixed(2) : '—'}
                                </p>
                              )}
                            </div>
                          </div>
                          <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                            {Number(entry.meter).toFixed(2)} m · {formatCurrency(entry.total)}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
