import { useEffect } from 'react';
import { X, ExternalLink, Download, FileText } from 'lucide-react';

interface ImageViewerModalProps {
  isOpen: boolean;
  onClose: () => void;
  imageUrl: string | null;
  title?: string;
}

export function ImageViewerModal({
  isOpen,
  onClose,
  imageUrl,
  title = 'Delivery Challan',
}: ImageViewerModalProps) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !imageUrl) return null;

  const isPdf = imageUrl.toLowerCase().split('?')[0].endsWith('.pdf');

  return (
    <div
      className="modal-overlay"
      onClick={onClose}
      style={{
        zIndex: 10000,
        backgroundColor: 'rgba(0, 0, 0, 0.85)',
        backdropFilter: 'blur(5px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '16px',
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: '100%',
          maxWidth: '560px',
          maxHeight: '92vh',
          backgroundColor: 'var(--bg-elevated, #ffffff)',
          borderRadius: 18,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          boxShadow: '0 25px 60px rgba(0, 0, 0, 0.45)',
          border: '1px solid var(--border)',
        }}
      >
        {/* Modal Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '14px 18px',
            borderBottom: '1px solid var(--border)',
            background: 'var(--bg-surface, #fff8dc)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: 8,
                background: 'var(--accent-glow, rgba(244, 196, 48, 0.2))',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--accent-dark, #9a6900)',
              }}
            >
              <FileText size={18} />
            </div>
            <div>
              <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
                {title}
              </h3>
              <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                {isPdf ? 'PDF Document' : 'Photo Attachment'}
              </span>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <a
              href={imageUrl}
              target="_blank"
              rel="noreferrer"
              className="btn-icon"
              style={{ padding: 6, color: 'var(--text-secondary)' }}
              title="Open full image in browser"
            >
              <ExternalLink size={18} />
            </a>
            <button
              type="button"
              className="btn-icon"
              onClick={onClose}
              style={{ padding: 6, color: 'var(--text-primary)' }}
              title="Close"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Modal Media Body */}
        <div
          style={{
            flex: 1,
            overflow: 'auto',
            padding: 16,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: '#121212',
            minHeight: 280,
          }}
        >
          {isPdf ? (
            <div style={{ textAlign: 'center', color: '#ffffff', padding: 24 }}>
              <FileText size={52} color="var(--accent, #d99a00)" style={{ margin: '0 auto 16px' }} />
              <p style={{ fontWeight: 600, fontSize: 16, marginBottom: 8 }}>PDF Document Attached</p>
              <p style={{ fontSize: 13, color: '#aaa', marginBottom: 20 }}>
                Tap below to view or download the full PDF
              </p>
              <a
                href={imageUrl}
                target="_blank"
                rel="noreferrer"
                className="btn btn-primary"
                style={{ display: 'inline-flex', alignItems: 'center', gap: 8, margin: '0 auto' }}
              >
                <Download size={16} /> Open / Download PDF
              </a>
            </div>
          ) : (
            <img
              src={imageUrl}
              alt="Challan"
              style={{
                maxWidth: '100%',
                maxHeight: '72vh',
                objectFit: 'contain',
                borderRadius: 8,
                boxShadow: '0 4px 16px rgba(0,0,0,0.3)',
              }}
            />
          )}
        </div>
      </div>
    </div>
  );
}
