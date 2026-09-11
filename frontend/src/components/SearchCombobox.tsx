/**
 * SearchCombobox — a mobile-friendly searchable picker.
 * Opens a full-screen search modal when tapped.
 */
import { useState, useRef, useEffect } from 'react';
import { Search, X, ChevronDown } from 'lucide-react';

export interface ComboboxOption {
  value: string | number;
  label: string;
  sublabel?: string;
}

interface Props {
  value: string | number | null;
  placeholder?: string;
  options: ComboboxOption[];
  onSearch?: (q: string) => void;  // called when user types, for async search
  onChange: (opt: ComboboxOption) => void;
  loading?: boolean;
  disabled?: boolean;
}

export function SearchCombobox({ value, placeholder = 'Select…', options, onSearch, onChange, loading, disabled }: Props) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const selected = options.find(o => o.value === value);

  const filtered = query
    ? options.filter(o =>
        o.label.toLowerCase().includes(query.toLowerCase()) ||
        (o.sublabel || '').toLowerCase().includes(query.toLowerCase())
      )
    : options;

  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 100);
    } else {
      setQuery('');
    }
  }, [open]);

  // When query changes, call async search if provided
  useEffect(() => {
    if (open && onSearch) onSearch(query);
  }, [query, open]);

  return (
    <>
      {/* Trigger button */}
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen(true)}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          width: '100%',
          padding: '12px 14px',
          background: 'var(--bg-input)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-md)',
          color: selected ? 'var(--text-primary)' : 'var(--text-muted)',
          fontFamily: 'inherit',
          fontSize: 15,
          cursor: 'pointer',
          textAlign: 'left',
        }}
      >
        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {selected ? selected.label : placeholder}
        </span>
        <ChevronDown size={16} style={{ flexShrink: 0, color: 'var(--text-muted)', marginLeft: 8 }} />
      </button>

      {/* Full-screen modal */}
      {open && (
        <div
          className="modal-overlay"
          style={{ alignItems: 'flex-start' }}
          onClick={() => setOpen(false)}
        >
          <div
            className="modal-sheet"
            style={{ height: '90vh', display: 'flex', flexDirection: 'column', borderRadius: '24px 24px 0 0' }}
            onClick={e => e.stopPropagation()}
          >
            <div className="modal-handle" />

            {/* Search input */}
            <div className="search-bar" style={{ margin: '0 0 16px' }}>
              <Search size={16} />
              <input
                ref={inputRef}
                placeholder={`Search${placeholder ? ` ${placeholder.replace('Select ', '').replace('…', '')}` : ''}…`}
                value={query}
                onChange={e => setQuery(e.target.value)}
              />
              {query && (
                <button onClick={() => setQuery('')} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
                  <X size={14} />
                </button>
              )}
            </div>

            {/* Results */}
            <div style={{ flex: 1, overflowY: 'auto' }}>
              {loading ? (
                <div style={{ display: 'flex', justifyContent: 'center', padding: 32 }}><div className="spinner" /></div>
              ) : filtered.length === 0 ? (
                <div className="empty-state" style={{ padding: '32px 20px' }}>
                  <Search size={36} />
                  <p>No results found</p>
                </div>
              ) : (
                filtered.map(opt => (
                  <div
                    key={opt.value}
                    onClick={() => { onChange(opt); setOpen(false); }}
                    style={{
                      padding: '14px 4px',
                      borderBottom: '1px solid var(--border)',
                      cursor: 'pointer',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 2,
                    }}
                  >
                    <span style={{
                      fontSize: 15,
                      fontWeight: opt.value === value ? 700 : 500,
                      color: opt.value === value ? 'var(--accent-light)' : 'var(--text-primary)',
                    }}>
                      {opt.label}
                    </span>
                    {opt.sublabel && (
                      <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{opt.sublabel}</span>
                    )}
                  </div>
                ))
              )}
            </div>

            <button className="btn btn-secondary" style={{ marginTop: 12 }} onClick={() => setOpen(false)}>
              Cancel
            </button>
          </div>
        </div>
      )}
    </>
  );
}
