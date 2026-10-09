import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { settingsApi } from '../../api/endpoints';
import { Lock, Save } from 'lucide-react';
import { formatDateShort } from '../../utils/format';

export default function Settings() {
  const qc = useQueryClient();
  const [periodLockDate, setPeriodLockDate] = useState('');

  const { data: settings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: () => settingsApi.get().then(r => r.data),
  });

  useEffect(() => {
    if (settings && settings.period_lock_date) {
      setPeriodLockDate(settings.period_lock_date);
    }
  }, [settings]);

  const updateMutation = useMutation({
    mutationFn: (data: any) => settingsApi.update(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['settings'] });
      alert('Settings updated successfully.');
    },
    onError: (err: any) => {
      alert(err.response?.data?.detail || 'Failed to update settings');
    }
  });

  const handleSave = () => {
    updateMutation.mutate({
      period_lock_date: periodLockDate || null,
    });
  };

  return (
    <div className="page-layout">
      <div className="page-header" style={{ padding: '16px 20px' }}>
        <h1 className="page-title">System Settings</h1>
      </div>

      <div className="content-area" style={{ padding: '0 20px' }}>
        {isLoading ? (
          <div style={{ padding: 24, textAlign: 'center' }}>Loading settings...</div>
        ) : (
          <div className="card" style={{ padding: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
              <Lock style={{ color: 'var(--danger)' }} />
              <h2 style={{ fontSize: 16, fontWeight: 700 }}>Period Lock</h2>
            </div>
            
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 20, lineHeight: 1.5 }}>
              Set a "Books Closed" date to prevent any new vouchers, edits, or reversals from being posted on or before this date. 
              This is typically used when you close a financial month or year.
            </p>

            <div className="form-group" style={{ marginBottom: 24 }}>
              <label className="form-label">Books Closed On or Before</label>
              <input 
                type="date" 
                className="form-input" 
                value={periodLockDate} 
                onChange={e => setPeriodLockDate(e.target.value)} 
                style={{ maxWidth: 300 }}
              />
              {periodLockDate && (
                <div style={{ marginTop: 8, fontSize: 12, color: 'var(--warning)', background: 'var(--warning-glow)', padding: '8px 12px', borderRadius: 6, display: 'inline-block' }}>
                  No one will be able to alter records on or before {formatDateShort(periodLockDate)}.
                </div>
              )}
            </div>

            <button 
              className="btn btn-primary" 
              onClick={handleSave} 
              disabled={updateMutation.isPending}
              style={{ display: 'flex', alignItems: 'center', gap: 8 }}
            >
              <Save size={16} /> Save Settings
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
