import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  Camera,
  Upload,
  Search,
  X,
  Plus,
  Trash2,
  Truck,
  Eye,
  CheckCircle2,
  Clock,
  ArrowRight,
} from 'lucide-react';
import { challansApi, partiesApi, invoicesApi } from '../../api/endpoints';
import { formatDate } from '../../utils/format';
import { ImageViewerModal } from '../../components/ImageViewerModal';
import { compressImageIfNeeded } from '../../utils/imageCompressor';

export default function ChallansList() {
  const navigate = useNavigate();
  const qc = useQueryClient();

  const [activeTab, setActiveTab] = useState<'PENDING' | 'INVOICED' | 'ALL'>('PENDING');
  const [search, setSearch] = useState('');
  const [selectedImageModal, setSelectedImageModal] = useState<string | null>(null);

  // Upload modal state
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [uploadedUrl, setUploadedUrl] = useState<string | null>(null);
  const [selectedPartyId, setSelectedPartyId] = useState<number | ''>('');
  const [customPartyName, setCustomPartyName] = useState('');
  const [challanNumber, setChallanNumber] = useState('');
  const [notes, setNotes] = useState('');
  const [partySearch, setPartySearch] = useState('');

  // Fetch challans
  const { data, isLoading } = useQuery({
    queryKey: ['challans', activeTab, search],
    queryFn: () => challansApi.list(activeTab, undefined, search || undefined).then((r) => r.data),
  });

  const challans = data?.items || [];
  const totalCount = data?.total || 0;
  const pendingCount = data?.pending_count || 0;
  const invoicedCount = data?.invoiced_count || 0;

  // Parties list for customer selection
  const { data: partiesData } = useQuery({
    queryKey: ['parties-for-challans', partySearch],
    queryFn: () => partiesApi.list(partySearch, 0, 100).then((r) => r.data.items),
    enabled: showUploadModal,
  });
  const parties = partiesData || [];

  // Delete challan mutation
  const deleteMutation = useMutation({
    mutationFn: (id: number) => challansApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['challans'] });
    },
  });

  // Handle image capture / selection
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Show instant local preview
    const objectUrl = URL.createObjectURL(file);
    setPreviewUrl(objectUrl);

    setUploading(true);
    try {
      const compressed = await compressImageIfNeeded(file);
      const res = await invoicesApi.upload(compressed);
      setUploadedUrl(res.data.url);
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Upload failed';
      alert(`Image upload failed: ${msg}`);
      setPreviewUrl(null);
      setUploadedUrl(null);
    } finally {
      setUploading(false);
    }
  };

  const handleSaveChallan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadedUrl) {
      alert('Please take or upload a challan photo first.');
      return;
    }

    try {
      setUploading(true);
      const selectedParty = parties.find((p: any) => p.id === Number(selectedPartyId));
      const partyName = selectedParty ? selectedParty.name : customPartyName.trim() || undefined;

      await challansApi.create({
        image_url: uploadedUrl,
        party_id: selectedPartyId ? Number(selectedPartyId) : undefined,
        party_name: partyName,
        challan_number: challanNumber.trim() || undefined,
        notes: notes.trim() || undefined,
      });

      qc.invalidateQueries({ queryKey: ['challans'] });
      resetUploadModal();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Failed to save challan';
      alert(`Error: ${msg}`);
    } finally {
      setUploading(false);
    }
  };

  const resetUploadModal = () => {
    setShowUploadModal(false);
    setPreviewUrl(null);
    setUploadedUrl(null);
    setSelectedPartyId('');
    setCustomPartyName('');
    setChallanNumber('');
    setNotes('');
    setPartySearch('');
  };

  const handleDelete = (id: number, number: string | null) => {
    if (window.confirm(`Are you sure you want to delete delivery challan ${number || ''}?`)) {
      deleteMutation.mutate(id);
    }
  };

  return (
    <div className="page-content">
      {/* Header */}
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 className="page-title">Delivery Challans</h1>
          <p className="page-subtitle">
            <span style={{ color: '#d97706', fontWeight: 600 }}>{pendingCount} Pending Invoice</span> · {totalCount} Total
          </p>
        </div>
        <button
          className="btn btn-primary"
          style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '8px 14px', fontSize: 13 }}
          onClick={() => setShowUploadModal(true)}
        >
          <Camera size={16} />
          <span>Upload Challan</span>
        </button>
      </div>

      {/* Search Bar */}
      <div className="search-bar" style={{ marginBottom: 12 }}>
        <Search size={16} />
        <input
          placeholder="Search by party, DC number, or notes…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        {search && (
          <button
            onClick={() => setSearch('')}
            style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
          >
            <X size={14} />
          </button>
        )}
      </div>

      {/* Filter Tabs */}
      <div className="chips" style={{ marginBottom: 12 }}>
        <button
          className={`chip ${activeTab === 'PENDING' ? 'active' : ''}`}
          onClick={() => setActiveTab('PENDING')}
        >
          <Clock size={13} style={{ marginRight: 4 }} />
          Pending Invoice ({pendingCount})
        </button>
        <button
          className={`chip ${activeTab === 'INVOICED' ? 'active' : ''}`}
          onClick={() => setActiveTab('INVOICED')}
        >
          <CheckCircle2 size={13} style={{ marginRight: 4 }} />
          Invoiced ({invoicedCount})
        </button>
        <button
          className={`chip ${activeTab === 'ALL' ? 'active' : ''}`}
          onClick={() => setActiveTab('ALL')}
        >
          All ({totalCount})
        </button>
      </div>

      {/* Challans List */}
      {isLoading ? (
        <div className="loading-screen">
          <div className="spinner" />
        </div>
      ) : challans.length === 0 ? (
        <div className="empty-state">
          <Truck size={48} />
          <h3>
            {activeTab === 'PENDING'
              ? 'No Pending Challans'
              : activeTab === 'INVOICED'
              ? 'No Invoiced Challans'
              : 'No Delivery Challans Yet'}
          </h3>
          <p>
            {activeTab === 'PENDING'
              ? 'All uploaded delivery challans have invoices created! Great job.'
              : 'Take photos of delivery challans or goods acknowledgements on the go.'}
          </p>
          <button
            className="btn btn-secondary"
            style={{ marginTop: 12 }}
            onClick={() => setShowUploadModal(true)}
          >
            <Camera size={16} style={{ marginRight: 6 }} /> Take / Upload Challan Photo
          </button>
        </div>
      ) : (
        <div className="list-container">
          {challans.map((c: any) => {
            const isPending = c.status === 'PENDING';
            return (
              <div key={c.id} className="invoice-big-card">
                {/* Top Row: Full-width Party Name Header */}
                <div className="card-party-header">
                  <div
                    style={{ position: 'relative', cursor: 'pointer', flexShrink: 0 }}
                    onClick={() => setSelectedImageModal(c.image_url)}
                    title="Click to view full photo"
                  >
                    <img
                      src={c.image_url}
                      alt={c.challan_number || 'Challan'}
                      className="challan-thumb"
                      style={{ width: 56, height: 56, borderRadius: 10 }}
                    />
                    <div
                      style={{
                        position: 'absolute',
                        inset: 0,
                        backgroundColor: 'rgba(0,0,0,0.18)',
                        borderRadius: 10,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: 'white',
                      }}
                    >
                      <Eye size={18} />
                    </div>
                  </div>

                  <div style={{ flex: 1, minWidth: 0 }}>
                    <h3
                      className="card-party-name"
                      onClick={() => {
                        if (c.party_id) navigate(`/parties/${c.party_id}`);
                      }}
                      title="View Party Details"
                    >
                      {c.party_name || 'Customer Not Specified'}
                    </h3>
                    <div className="card-inv-meta">
                      <span className="card-inv-number">{c.challan_number || `DC-${c.id}`}</span>
                      <span className="meta-dot">·</span>
                      <span>{formatDate(c.created_at)}</span>
                      {c.invoice_number && (
                        <>
                          <span className="meta-dot">·</span>
                          <span style={{ color: 'var(--accent)', fontWeight: 700 }}>
                            {c.invoice_number}
                          </span>
                        </>
                      )}
                    </div>
                  </div>

                  <span
                    className={`status-pill ${isPending ? 'partial' : 'paid'}`}
                    style={{ flexShrink: 0 }}
                  >
                    {isPending ? '⏳ PENDING' : '✓ INVOICED'}
                  </span>
                </div>

                {c.notes && (
                  <div style={{ background: 'rgba(0,0,0,0.02)', padding: '8px 12px', borderRadius: 8, fontSize: 12, color: 'var(--text-secondary)' }}>
                    <strong>Note:</strong> {c.notes}
                  </div>
                )}

                {/* Bottom Action Row */}
                <div className="card-actions-bar" style={{ marginTop: 2 }}>
                  {isPending && (
                    <button
                      type="button"
                      className="card-action-btn pay"
                      style={{
                        background: 'var(--accent)',
                        color: '#ffffff',
                        borderColor: 'var(--accent)',
                        marginRight: 'auto',
                      }}
                      onClick={() => {
                        const params = new URLSearchParams();
                        if (c.party_id) params.set('party', String(c.party_id));
                        params.set('challan_url', c.image_url);
                        params.set('challan_id', String(c.id));
                        navigate(`/invoices/new?${params.toString()}`);
                      }}
                    >
                      <Plus size={14} />
                      <span>Create Invoice</span>
                      <ArrowRight size={13} />
                    </button>
                  )}

                  <button
                    type="button"
                    className="card-action-btn"
                    onClick={() => setSelectedImageModal(c.image_url)}
                    title="View full photo"
                  >
                    <Eye size={13} />
                    <span>View Photo</span>
                  </button>

                  <button
                    type="button"
                    className="card-action-btn danger"
                    onClick={() => handleDelete(c.id, c.challan_number)}
                    title="Delete challan"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Floating Action Button */}
      <button className="fab" onClick={() => setShowUploadModal(true)} title="Upload Delivery Challan">
        <Camera size={24} />
      </button>

      {/* Upload Modal */}
      {showUploadModal && (
        <div
          className="modal-overlay"
          onClick={resetUploadModal}
          style={{
            zIndex: 9999,
            backgroundColor: 'rgba(0, 0, 0, 0.65)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 16,
          }}
        >
          <div
            className="modal-card"
            onClick={(e) => e.stopPropagation()}
            style={{
              width: '100%',
              maxWidth: 480,
              background: 'var(--bg-card)',
              borderRadius: 16,
              overflow: 'hidden',
              boxShadow: '0 20px 40px rgba(0,0,0,0.3)',
            }}
          >
            {/* Modal Header */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '16px 20px',
                borderBottom: '1px solid var(--border)',
              }}
            >
              <h3 style={{ margin: 0, fontSize: 17, fontWeight: 700 }}>Upload Delivery Challan</h3>
              <button
                type="button"
                onClick={resetUploadModal}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                <X size={20} />
              </button>
            </div>

            {/* Modal Body / Form */}
            <form onSubmit={handleSaveChallan} style={{ padding: '16px 20px' }}>
              {/* Photo Input / Preview */}
              <div style={{ marginBottom: 16 }}>
                <label className="form-label" style={{ marginBottom: 6, display: 'block', fontSize: 13, fontWeight: 600 }}>
                  Challan Photo *
                </label>

                {previewUrl || uploadedUrl ? (
                  <div style={{ position: 'relative', borderRadius: 12, overflow: 'hidden', border: '1px solid var(--border)' }}>
                    <img
                      src={previewUrl || uploadedUrl || ''}
                      alt="Challan preview"
                      style={{ width: '100%', maxHeight: 220, objectFit: 'contain', background: '#000' }}
                    />
                    <div
                      style={{
                        position: 'absolute',
                        bottom: 8,
                        right: 8,
                        display: 'flex',
                        gap: 8,
                      }}
                    >
                      <label
                        htmlFor="retake-camera"
                        className="btn btn-sm btn-secondary"
                        style={{ cursor: 'pointer', margin: 0, background: 'rgba(0,0,0,0.7)', color: '#fff', border: 'none' }}
                      >
                        Retake
                      </label>
                      <button
                        type="button"
                        className="btn btn-sm btn-secondary"
                        style={{ background: 'rgba(239,68,68,0.85)', color: '#fff', border: 'none' }}
                        onClick={() => {
                          setPreviewUrl(null);
                          setUploadedUrl(null);
                        }}
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </div>
                ) : (
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                    <label
                      htmlFor="challan-camera-input"
                      className="btn btn-secondary"
                      style={{
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        padding: '16px 8px',
                        gap: 6,
                        cursor: uploading ? 'not-allowed' : 'pointer',
                        background: 'rgba(217, 154, 0, 0.08)',
                        border: '1.5px dashed var(--accent)',
                        color: 'var(--accent)',
                        borderRadius: 12,
                        margin: 0,
                      }}
                    >
                      <Camera size={24} />
                      <span style={{ fontSize: 13, fontWeight: 600 }}>Take Photo</span>
                    </label>

                    <label
                      htmlFor="challan-gallery-input"
                      className="btn btn-secondary"
                      style={{
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        padding: '16px 8px',
                        gap: 6,
                        cursor: uploading ? 'not-allowed' : 'pointer',
                        border: '1.5px dashed var(--border)',
                        borderRadius: 12,
                        margin: 0,
                      }}
                    >
                      <Upload size={24} />
                      <span style={{ fontSize: 13, fontWeight: 600 }}>From Gallery</span>
                    </label>
                  </div>
                )}

                {/* Hidden native inputs */}
                <input
                  id="challan-camera-input"
                  type="file"
                  accept="image/*"
                  capture="environment"
                  style={{ display: 'none' }}
                  onChange={handleFileChange}
                  disabled={uploading}
                />
                <input
                  id="retake-camera"
                  type="file"
                  accept="image/*"
                  capture="environment"
                  style={{ display: 'none' }}
                  onChange={handleFileChange}
                  disabled={uploading}
                />
                <input
                  id="challan-gallery-input"
                  type="file"
                  accept="image/*"
                  style={{ display: 'none' }}
                  onChange={handleFileChange}
                  disabled={uploading}
                />

                {uploading && (
                  <p style={{ fontSize: 12, color: 'var(--accent)', marginTop: 6, fontWeight: 600 }}>
                    Optimizing and uploading image…
                  </p>
                )}
              </div>

              {/* Party Select */}
              <div style={{ marginBottom: 14 }}>
                <label className="form-label" style={{ marginBottom: 4, display: 'block', fontSize: 13 }}>
                  Party / Customer (Optional)
                </label>
                <select
                  className="form-input"
                  value={selectedPartyId}
                  onChange={(e) => {
                    setSelectedPartyId(e.target.value ? Number(e.target.value) : '');
                  }}
                  style={{ width: '100%', fontSize: 13 }}
                >
                  <option value="">-- Select Party or Leave Blank --</option>
                  {parties.map((p: any) => (
                    <option key={p.id} value={p.id}>
                      {p.name} {p.billing_city ? `(${p.billing_city})` : ''}
                    </option>
                  ))}
                </select>
                {!selectedPartyId && (
                  <input
                    type="text"
                    className="form-input"
                    placeholder="Or type customer name directly…"
                    value={customPartyName}
                    onChange={(e) => setCustomPartyName(e.target.value)}
                    style={{ marginTop: 6, width: '100%', fontSize: 12 }}
                  />
                )}
              </div>

              {/* Challan Number */}
              <div style={{ marginBottom: 14 }}>
                <label className="form-label" style={{ marginBottom: 4, display: 'block', fontSize: 13 }}>
                  Challan / DC Number (Optional)
                </label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="Auto-generated if left blank (e.g. DC-0012)"
                  value={challanNumber}
                  onChange={(e) => setChallanNumber(e.target.value)}
                  style={{ width: '100%', fontSize: 13 }}
                />
              </div>

              {/* Notes */}
              <div style={{ marginBottom: 18 }}>
                <label className="form-label" style={{ marginBottom: 4, display: 'block', fontSize: 13 }}>
                  Notes / Transport Details (Optional)
                </label>
                <textarea
                  className="form-input"
                  placeholder="e.g. 3 bales sent via Sri Ram Transport"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={2}
                  style={{ width: '100%', fontSize: 13, resize: 'none' }}
                />
              </div>

              {/* Submit Buttons */}
              <div style={{ display: 'flex', gap: 10 }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={resetUploadModal}
                  style={{ flex: 1 }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={uploading || !uploadedUrl}
                  style={{ flex: 2, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}
                >
                  <Plus size={16} />
                  <span>Save (Pending Invoice)</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Full Screen Image Viewer */}
      <ImageViewerModal
        isOpen={!!selectedImageModal}
        onClose={() => setSelectedImageModal(null)}
        imageUrl={selectedImageModal}
        title="Delivery Challan Photo"
      />
    </div>
  );
}
