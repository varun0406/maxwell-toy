/**
 * SearchCombobox — a mobile-friendly searchable picker.
 * Opens a full-screen search modal when tapped.
 */
import { useState, useRef, useEffect } from 'react';
import { useInView } from 'react-intersection-observer';
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
  hasMore?: boolean;
  onLoadMore?: () => void;
  loadingMore?: boolean;
  selectedOption?: ComboboxOption | null;
  onOpenChange?: (open: boolean) => void;
}

export function SearchCombobox({
  value,
  placeholder = 'Select…',
  options,
  onSearch,
  onChange,
  loading,
  disabled,
  hasMore,
  onLoadMore,
  loadingMore,
  selectedOption,
  onOpenChange,
}: Props) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const { ref: loadMoreRef, inView } = useInView({ rootMargin: '80px' });

  const selected = options.find(o => o.value === value)
    || (selectedOption && selectedOption.value === value ? selectedOption : undefined);

  const filtered = onSearch
    ? options
    : query
      ? options.filter(o =>
          o.label.toLowerCase().includes(query.toLowerCase()) ||
          (o.sublabel || '').toLowerCase().includes(query.toLowerCase())
        )
      : options;

  const setOpenState = (next: boolean) => {
    setOpen(next);
    onOpenChange?.(next);
  };

  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 100);
    } else {
      setQuery('');
    }
  }, [open]);

  useEffect(() => {
    if (!open || !onSearch) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => onSearch(query), query ? 280 : 0);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, open, onSearch]);

  useEffect(() => {
    if (open && inView && hasMore && !loadingMore && !loading) {
      onLoadMore?.();
    }
  }, [open, inView, hasMore, loadingMore, loading, onLoadMore]);

  return (
    <>
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpenState(true)}
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

      {open && (
        <div
          className="modal-overlay"
          style={{ alignItems: 'flex-start' }}
          onClick={() => setOpenState(false)}
        >
          <div
            className="modal-sheet"
            style={{ height: '90vh', display: 'flex', flexDirection: 'column', borderRadius: '24px 24px 0 0' }}
            onClick={e => e.stopPropagation()}
          >
            <div className="modal-handle" />

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

            <div style={{ flex: 1, overflowY: 'auto' }}>
              {loading && filtered.length === 0 ? (
                <div style={{ display: 'flex', justifyContent: 'center', padding: 32 }}><div className="spinner" /></div>
              ) : filtered.length === 0 ? (
                <div className="empty-state" style={{ padding: '32px 20px' }}>
                  <Search size={36} />
                  <p>No results found</p>
                </div>
              ) : (
                (Array.isArray(filtered) ? filtered : []).map(opt => (
                  <div
                    key={opt.value}
                    onClick={() => { onChange(opt); setOpenState(false); }}
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
              {hasMore && (
                <div ref={loadMoreRef} style={{ padding: '16px 0', display: 'flex', justifyContent: 'center' }}>
                  {(loadingMore || loading) && <div className="spinner" style={{ width: 20, height: 20, borderWidth: 2 }} />}
                </div>
              )}
            </div>

            <button className="btn btn-secondary" style={{ marginTop: 12 }} onClick={() => setOpenState(false)}>
              Cancel
            </button>
          </div>
        </div>
      )}
    </>
  );
}
