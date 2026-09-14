import { useState } from 'react';
import { Info, X } from 'lucide-react';
import { formatCurrency } from '../utils/format';

export interface EvidenceItem {
  label: string;
  value: number;
  operator?: '+' | '-' | '=';
  isTotal?: boolean;
}

interface Props {
  title: string;
  items: EvidenceItem[];
  children: React.ReactNode;
  valueClass?: string; // Optional class to preserve existing styling of the number
}

export default function CalculationEvidence({ title, items, children, valueClass }: Props) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <div 
        onClick={(e) => { e.stopPropagation(); setIsOpen(true); }} 
        style={{ 
          display: 'inline-flex', 
          alignItems: 'center', 
          gap: 6, 
          cursor: 'pointer',
        }}
      >
        <span className={valueClass} style={{ borderBottom: '1px dashed var(--text-muted)' }}>
          {children}
        </span>
        <Info size={14} style={{ color: 'var(--accent-light)' }} />
      </div>

      {isOpen && (
        <div className="modal-overlay" onClick={(e) => { e.stopPropagation(); setIsOpen(false); }}>
          <div className="modal-sheet" onClick={(e) => e.stopPropagation()}>
            <div className="modal-handle" />
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <h2 className="modal-title" style={{ marginBottom: 0 }}>Calculation Evidence</h2>
              <button className="btn-icon" onClick={() => setIsOpen(false)} style={{ width: 32, height: 32 }}>
                <X size={16} />
              </button>
            </div>
            
            <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 20 }}>
              Here is how <strong>{title}</strong> is calculated:
            </p>

            <div style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)', padding: '16px', border: '1px solid var(--border-card)' }}>
              {items.map((item, idx) => {
                const isTotal = item.isTotal || item.operator === '=';
                return (
                  <div key={idx}>
                    {isTotal && <div className="divider" style={{ margin: '12px 0' }} />}
                    <div style={{ 
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      alignItems: 'center',
                      padding: '6px 0',
                      fontWeight: isTotal ? 800 : 500,
                      color: isTotal ? 'var(--text-primary)' : 'var(--text-secondary)',
                      fontSize: isTotal ? 16 : 14,
                    }}>
                      <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                        {!isTotal && <span style={{ color: 'var(--text-muted)', fontFamily: 'monospace' }}>{item.operator || '+'}</span>}
                        <span>{item.label}</span>
                      </div>
                      <span className="mono">
                        {item.operator === '-' && item.value > 0 ? '-' : ''}{formatCurrency(item.value)}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
            
            <button className="btn btn-secondary btn-full" style={{ marginTop: 20 }} onClick={() => setIsOpen(false)}>
              Close
            </button>
          </div>
        </div>
      )}
    </>
  );
}
