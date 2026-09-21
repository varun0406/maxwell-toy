/**
 * ItemAutocomplete — autocomplete input for item names.
 * Shows dropdown suggestions from item master.
 * On blur, upserts the typed name to item master automatically.
 */
import { useState, useRef, useEffect } from 'react';
import { itemsApi } from '../api/endpoints';

interface Props {
  value: string;
  onChange: (name: string, rate?: number) => void;
  placeholder?: string;
}

export function ItemAutocomplete({ value, onChange, placeholder = 'e.g. Fabric' }: Props) {
  const [query, setQuery] = useState(value);
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [highlighted, setHighlighted] = useState(-1);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Keep local query in sync if value changes externally
  useEffect(() => { setQuery(value); }, [value]);

  const search = (q: string) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      if (q.length > 0) {
        const res = await itemsApi.search(q);
        setSuggestions(res.data);
        setShowDropdown(true);
      } else {
        setSuggestions([]);
        setShowDropdown(false);
      }
    }, 200);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = e.target.value;
    setQuery(v);
    onChange(v);
    search(v);
    setHighlighted(-1);
  };

  const selectSuggestion = (s: any) => {
    setQuery(s.item_name);
    onChange(s.item_name, s.default_rate);
    setShowDropdown(false);
    setSuggestions([]);
  };

  const handleBlur = async () => {
    setTimeout(() => setShowDropdown(false), 150);
    // Auto-upsert to item master if non-empty
    if (query.trim()) {
      try { await itemsApi.upsert({ item_name: query.trim() }); } catch {}
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!showDropdown || suggestions.length === 0) return;
    if (e.key === 'ArrowDown') { e.preventDefault(); setHighlighted(h => Math.min(h + 1, suggestions.length - 1)); }
    if (e.key === 'ArrowUp')   { e.preventDefault(); setHighlighted(h => Math.max(h - 1, 0)); }
    if (e.key === 'Enter' && highlighted >= 0) { e.preventDefault(); selectSuggestion(suggestions[highlighted]); }
    if (e.key === 'Escape') setShowDropdown(false);
  };

  return (
    <div style={{ position: 'relative' }}>
      <input
        className="form-input"
        placeholder={placeholder}
        value={query}
        onChange={handleChange}
        onBlur={handleBlur}
        onFocus={() => query.length > 0 && search(query)}
        onKeyDown={handleKeyDown}
        autoComplete="off"
      />
      {showDropdown && suggestions.length > 0 && (
        <div style={{
          position: 'absolute',
          top: '100%',
          left: 0,
          right: 0,
          zIndex: 500,
          background: 'var(--bg-elevated)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-md)',
          marginTop: 4,
          maxHeight: 200,
          overflowY: 'auto',
          boxShadow: 'var(--shadow-md)',
        }}>
          {(Array.isArray(suggestions) ? suggestions : []).map((s: any, i: number) => (
            <div
              key={s.id}
              onMouseDown={() => selectSuggestion(s)}
              style={{
                padding: '10px 14px',
                cursor: 'pointer',
                borderBottom: i < suggestions.length - 1 ? '1px solid var(--border)' : 'none',
                background: i === highlighted ? 'var(--accent-glow)' : 'transparent',
                display: 'flex',
                justifyContent: 'space-between',
              }}
            >
              <span style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>{s.item_name}</span>
              {s.default_rate > 0 && (
                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>₹{s.default_rate}</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
