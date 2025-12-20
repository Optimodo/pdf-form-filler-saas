import React, { useState, useEffect } from 'react';
import APIService from '../../services/api';
import InlineMessage from '../UI/InlineMessage';
import ConfirmDialog from '../UI/ConfirmDialog';
import './AdminTiers.css';

function AdminTiers() {
  const [tiers, setTiers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);
  const [messageType, setMessageType] = useState('success');
  const [editingTier, setEditingTier] = useState(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [confirmDialog, setConfirmDialog] = useState(null);

  useEffect(() => {
    loadTiers();
  }, []);

  const loadTiers = async () => {
    try {
      setLoading(true);
      const data = await APIService.listSubscriptionTiers();
      setTiers(data.tiers || []);
      setError(null);
    } catch (err) {
      setError(err.message || 'Failed to load subscription tiers');
      console.error('Tiers list error:', err);
    } finally {
      setLoading(false);
    }
  };

  const showMessage = (msg, type = 'success') => {
    setMessage(msg);
    setMessageType(type);
    // Auto-clear after 5 seconds
    setTimeout(() => setMessage(null), 5000);
  };

  const handleEdit = async (tier) => {
    try {
      // Fetch full tier details (with byte values) for editing
      const tierDetails = await APIService.getSubscriptionTier(tier.id);
      setEditingTier(tierDetails);
      setShowCreateForm(false);
    } catch (err) {
      showMessage(`Failed to load tier details: ${err.message}`, 'error');
    }
  };

  const handleCreate = () => {
    setEditingTier(null);
    setShowCreateForm(true);
  };

  const handleCancel = () => {
    setEditingTier(null);
    setShowCreateForm(false);
  };

  const handleSave = async (tierData) => {
    try {
      setActionLoading(true);
      if (editingTier) {
        // Update existing tier
        // Convert file sizes from MB to bytes
        const updateData = {
          ...tierData,
          max_pdf_size: tierData.max_pdf_size * 1024 * 1024,
          max_csv_size: tierData.max_csv_size * 1024 * 1024,
        };
        await APIService.updateSubscriptionTier(editingTier.id, updateData);
        showMessage('Tier updated successfully');
      } else {
        // Create new tier
        const createData = {
          ...tierData,
          max_pdf_size: tierData.max_pdf_size * 1024 * 1024,
          max_csv_size: tierData.max_csv_size * 1024 * 1024,
        };
        await APIService.createSubscriptionTier(createData);
        showMessage('Tier created successfully');
      }
      await loadTiers();
      handleCancel();
    } catch (err) {
      showMessage(`Failed to save tier: ${err.message}`, 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeleteClick = (tier) => {
    setConfirmDialog({
      title: 'Delete Tier',
      message: `Are you sure you want to delete tier "${tier.display_name}"? This cannot be undone and will only work if no users are assigned to this tier.`,
      confirmText: 'Delete',
      cancelText: 'Cancel',
      variant: 'danger',
      onConfirm: () => handleDelete(tier.id),
      onCancel: () => setConfirmDialog(null),
    });
  };

  const handleDelete = async (tierId) => {
    setConfirmDialog(null);
    try {
      setActionLoading(true);
      await APIService.deleteSubscriptionTier(tierId);
      showMessage('Tier deleted successfully');
      await loadTiers();
    } catch (err) {
      showMessage(`Failed to delete tier: ${err.message}`, 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const bytesToMb = (bytes) => (bytes / (1024 * 1024)).toFixed(1);

  if (loading) {
    return (
      <div className="admin-tiers">
        <div className="loading">Loading subscription tiers...</div>
      </div>
    );
  }

  return (
    <div className="admin-tiers">
      <div className="tiers-header">
        <h1>Subscription Tiers Management</h1>
        <div className="header-actions">
          <button
            onClick={() => {
              window.location.pathname = '/admin';
            }}
            className="btn-secondary"
          >
            ← Back to Dashboard
          </button>
          <button
            onClick={handleCreate}
            className="btn-primary"
            disabled={actionLoading || showCreateForm || editingTier}
          >
            + Create New Tier
          </button>
        </div>
      </div>

      <InlineMessage 
        message={error ? `Error: ${error}` : message}
        type={error ? 'error' : messageType}
        onClose={error ? () => setError(null) : () => setMessage(null)}
      />

      {error && (
        <div style={{ textAlign: 'center', marginBottom: '1rem' }}>
          <button onClick={loadTiers} className="btn-secondary">Retry</button>
        </div>
      )}

      <ConfirmDialog
        isOpen={confirmDialog !== null}
        title={confirmDialog?.title}
        message={confirmDialog?.message}
        confirmText={confirmDialog?.confirmText}
        cancelText={confirmDialog?.cancelText}
        variant={confirmDialog?.variant}
        onConfirm={confirmDialog?.onConfirm}
        onCancel={confirmDialog?.onCancel}
      />

      {/* Create/Edit Form */}
      {(showCreateForm || editingTier) && (
          <TierForm
            tier={editingTier}
            onSave={handleSave}
            onCancel={handleCancel}
            loading={actionLoading}
          />
      )}

      {/* Tiers List */}
      <div className="tiers-list">
        {tiers.map(tier => (
            <TierCard
            key={tier.id}
            tier={tier}
            onEdit={handleEdit}
            onDelete={handleDeleteClick}
            disabled={actionLoading}
          />
        ))}
      </div>

      {tiers.length === 0 && !loading && (
        <div className="empty-state">
          <p>No subscription tiers found. Create your first tier to get started.</p>
        </div>
      )}
    </div>
  );
}

function TierCard({ tier, onEdit, onDelete, disabled }) {
  return (
    <div className={`tier-card ${!tier.is_active ? 'inactive' : ''}`}>
      <div className="tier-card-header">
        <div>
          <h2>{tier.display_name}</h2>
          <span className="tier-key">({tier.tier_key})</span>
          {!tier.is_active && <span className="inactive-badge">Inactive</span>}
        </div>
        <div className="tier-card-actions">
          <button
            onClick={() => onEdit(tier)}
            className="btn-secondary"
            disabled={disabled}
          >
            Edit
          </button>
          <button
            onClick={() => onDelete(tier)}
            className="btn-danger"
            disabled={disabled}
          >
            Delete
          </button>
        </div>
      </div>

      {tier.description && <p className="tier-description">{tier.description}</p>}

      <div className="tier-limits-grid">
        <div className="limit-item">
          <label>Max PDF Size</label>
          <div>{tier.max_pdf_size}</div>
        </div>
        <div className="limit-item">
          <label>Max CSV Size</label>
          <div>{tier.max_csv_size}</div>
        </div>
        <div className="limit-item">
          <label>Daily Jobs</label>
          <div>{tier.max_daily_jobs}</div>
        </div>
        <div className="limit-item">
          <label>Monthly Jobs</label>
          <div>{tier.max_monthly_jobs}</div>
        </div>
        <div className="limit-item">
          <label>Files per Job</label>
          <div>{tier.max_files_per_job}</div>
        </div>
        <div className="limit-item">
          <label>Can Save Templates</label>
          <div>{tier.can_save_templates ? 'Yes' : 'No'}</div>
        </div>
        <div className="limit-item">
          <label>Can Use API</label>
          <div>{tier.can_use_api ? 'Yes' : 'No'}</div>
        </div>
        <div className="limit-item">
          <label>Priority Processing</label>
          <div>{tier.priority_processing ? 'Yes' : 'No'}</div>
        </div>
      </div>
    </div>
  );
}

function TierForm({ tier, onSave, onCancel, loading }) {
  // Convert bytes to MB for form display
  const bytesToMb = (bytes) => {
    if (!bytes) return 0;
    return (bytes / (1024 * 1024)).toFixed(1);
  };

  const [formData, setFormData] = useState({
    tier_key: tier?.tier_key || '',
    display_name: tier?.display_name || '',
    description: tier?.description || '',
    max_pdf_size: tier ? parseFloat(bytesToMb(tier.max_pdf_size)) : 1,
    max_csv_size: tier ? parseFloat(bytesToMb(tier.max_csv_size)) : 0.25,
    max_daily_jobs: tier?.max_daily_jobs || 10,
    max_monthly_jobs: tier?.max_monthly_jobs || 100,
    max_files_per_job: tier?.max_files_per_job || 100,
    can_save_templates: tier?.can_save_templates || false,
    can_use_api: tier?.can_use_api || false,
    priority_processing: tier?.priority_processing || false,
    max_saved_templates: tier?.max_saved_templates || 0,
    max_total_storage_mb: tier?.max_total_storage_mb || 0,
    display_order: tier?.display_order || 999,
    is_active: tier?.is_active !== undefined ? tier.is_active : true,
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave(formData);
  };

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  return (
    <div className="tier-form-container">
      <h2>{tier ? 'Edit Tier' : 'Create New Tier'}</h2>
      <form onSubmit={handleSubmit} className="tier-form">
        <div className="form-grid">
          <div className="form-group">
            <label>Tier Key *</label>
            <input
              type="text"
              value={formData.tier_key}
              onChange={(e) => handleChange('tier_key', e.target.value)}
              required
              disabled={!!tier} // Can't change tier_key after creation
              placeholder="e.g., free, member, pro"
            />
            {tier && <small>Tier key cannot be changed after creation</small>}
          </div>

          <div className="form-group">
            <label>Display Name *</label>
            <input
              type="text"
              value={formData.display_name}
              onChange={(e) => handleChange('display_name', e.target.value)}
              required
              placeholder="e.g., Free, Member, Pro"
            />
          </div>

          <div className="form-group full-width">
            <label>Description</label>
            <textarea
              value={formData.description}
              onChange={(e) => handleChange('description', e.target.value)}
              rows="2"
              placeholder="Optional description for this tier"
            />
          </div>

          <div className="form-group">
            <label>Max PDF Size (MB) *</label>
            <input
              type="number"
              step="0.1"
              value={formData.max_pdf_size}
              onChange={(e) => handleChange('max_pdf_size', parseFloat(e.target.value) || 0)}
              required
              min="0"
            />
          </div>

          <div className="form-group">
            <label>Max CSV Size (MB) *</label>
            <input
              type="number"
              step="0.1"
              value={formData.max_csv_size}
              onChange={(e) => handleChange('max_csv_size', parseFloat(e.target.value) || 0)}
              required
              min="0"
            />
          </div>

          <div className="form-group">
            <label>Daily Jobs</label>
            <input
              type="number"
              value={formData.max_daily_jobs}
              onChange={(e) => handleChange('max_daily_jobs', parseInt(e.target.value) || 0)}
              min="0"
            />
          </div>

          <div className="form-group">
            <label>Monthly Jobs</label>
            <input
              type="number"
              value={formData.max_monthly_jobs}
              onChange={(e) => handleChange('max_monthly_jobs', parseInt(e.target.value) || 0)}
              min="0"
            />
          </div>

          <div className="form-group">
            <label>Files per Job</label>
            <input
              type="number"
              value={formData.max_files_per_job}
              onChange={(e) => handleChange('max_files_per_job', parseInt(e.target.value) || 0)}
              min="0"
            />
          </div>

          <div className="form-group">
            <label>Max Saved Templates</label>
            <input
              type="number"
              value={formData.max_saved_templates}
              onChange={(e) => handleChange('max_saved_templates', parseInt(e.target.value) || 0)}
              min="0"
            />
          </div>

          <div className="form-group">
            <label>Max Total Storage (MB)</label>
            <input
              type="number"
              value={formData.max_total_storage_mb}
              onChange={(e) => handleChange('max_total_storage_mb', parseInt(e.target.value) || 0)}
              min="0"
            />
          </div>

          <div className="form-group">
            <label>Display Order</label>
            <input
              type="number"
              value={formData.display_order}
              onChange={(e) => handleChange('display_order', parseInt(e.target.value) || 0)}
            />
            <small>Lower numbers appear first</small>
          </div>

          <div className="form-group checkbox-group">
            <label>
              <input
                type="checkbox"
                checked={formData.can_save_templates}
                onChange={(e) => handleChange('can_save_templates', e.target.checked)}
              />
              Can Save Templates
            </label>
          </div>

          <div className="form-group checkbox-group">
            <label>
              <input
                type="checkbox"
                checked={formData.can_use_api}
                onChange={(e) => handleChange('can_use_api', e.target.checked)}
              />
              Can Use API
            </label>
          </div>

          <div className="form-group checkbox-group">
            <label>
              <input
                type="checkbox"
                checked={formData.priority_processing}
                onChange={(e) => handleChange('priority_processing', e.target.checked)}
              />
              Priority Processing
            </label>
          </div>

          <div className="form-group checkbox-group">
            <label>
              <input
                type="checkbox"
                checked={formData.is_active}
                onChange={(e) => handleChange('is_active', e.target.checked)}
              />
              Active
            </label>
          </div>
        </div>

        <div className="form-actions">
          <button type="button" onClick={onCancel} className="btn-secondary" disabled={loading}>
            Cancel
          </button>
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Saving...' : (tier ? 'Update Tier' : 'Create Tier')}
          </button>
        </div>
      </form>
    </div>
  );
}

export default AdminTiers;
