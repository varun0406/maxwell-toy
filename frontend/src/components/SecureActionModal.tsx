import React, { useState } from 'react';
import { X, Lock } from 'lucide-react';

interface SecureActionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title?: string;
  message?: string;
}

export function SecureActionModal({ isOpen, onClose, onConfirm, title = "Security Check", message = "Enter Master PIN to proceed." }: SecureActionModalProps) {
  const [pin, setPin] = useState('');
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const unlockCode = import.meta.env.VITE_UNLOCK_CODE || '2809';
    if (pin === unlockCode) {
      setError('');
      setPin('');
      onConfirm();
    } else {
      setError('Incorrect PIN');
      setPin('');
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content" style={{ maxWidth: 320 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Lock size={20} color="var(--warning)" />
            <h2 style={{ fontSize: 18, fontWeight: 600 }}>{title}</h2>
          </div>
          <button type="button" className="btn-icon" onClick={onClose}><X size={20} /></button>
        </div>
        
        <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginBottom: 20 }}>
          {message}
        </p>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <input
              type="password"
              className="form-control"
              placeholder="Enter PIN"
              value={pin}
              onChange={(e) => setPin(e.target.value)}
              autoFocus
              maxLength={4}
              pattern="[0-9]*"
              inputMode="numeric"
              style={{ textAlign: 'center', fontSize: 24, letterSpacing: 8 }}
            />
            {error && <div className="form-error" style={{ textAlign: 'center', marginTop: 8 }}>{error}</div>}
          </div>
          <div style={{ display: 'flex', gap: 12, marginTop: 24 }}>
            <button type="button" className="btn btn-secondary" style={{ flex: 1 }} onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" style={{ flex: 1, background: 'var(--danger)', borderColor: 'var(--danger)' }}>Confirm</button>
          </div>
        </form>
      </div>
    </div>
  );
}
