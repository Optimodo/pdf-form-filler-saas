import React, { useState, useEffect } from 'react';
import APIService from '../../services/api';
import './AdminUsersList.css';

function AdminUsersList() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pagination, setPagination] = useState({ skip: 0, limit: 50, total: 0 });
  const [filters, setFilters] = useState({ 
    search: '', 
    tier: '',
    min_credits_used: '',
    max_credits_used: '',
    min_credits_remaining: '',
    max_credits_remaining: '',
    min_job_count: '',
    max_job_count: ''
  });
  const [numericFilterDrafts, setNumericFilterDrafts] = useState({
    min_credits_used: '',
    max_credits_used: '',
    min_credits_remaining: '',
    max_credits_remaining: '',
    min_job_count: '',
    max_job_count: ''
  });
  const [availableTiers, setAvailableTiers] = useState([]);
  const [sortBy, setSortBy] = useState(null);
  const [sortOrder, setSortOrder] = useState('desc');

  useEffect(() => {
    loadUsers();
    loadTiers();
  }, [pagination.skip, pagination.limit, filters.search, filters.tier, filters.min_credits_used, filters.max_credits_used, filters.min_credits_remaining, filters.max_credits_remaining, filters.min_job_count, filters.max_job_count, sortBy, sortOrder]);

  // Sync draft values with active filters when filters change externally (e.g., clear)
  useEffect(() => {
    setNumericFilterDrafts({
      min_credits_used: filters.min_credits_used,
      max_credits_used: filters.max_credits_used,
      min_credits_remaining: filters.min_credits_remaining,
      max_credits_remaining: filters.max_credits_remaining,
      min_job_count: filters.min_job_count,
      max_job_count: filters.max_job_count
    });
  }, [filters.min_credits_used, filters.max_credits_used, filters.min_credits_remaining, filters.max_credits_remaining, filters.min_job_count, filters.max_job_count]);

  const loadTiers = async () => {
    try {
      const data = await APIService.listSubscriptionTiers();
      const activeTiers = (data.tiers || [])
        .filter(tier => tier.is_active)
        .sort((a, b) => (a.display_order || 999) - (b.display_order || 999));
      setAvailableTiers(activeTiers);
    } catch (err) {
      console.error('Failed to load tiers:', err);
      setAvailableTiers([]);
    }
  };

  const loadUsers = async () => {
    try {
      setLoading(true);
      const params = {
        skip: pagination.skip,
        limit: pagination.limit,
        search: filters.search || undefined,
        tier: filters.tier || undefined,
      };
      
      // Add numeric filters only if they have values
      if (filters.min_credits_used) params.min_credits_used = parseInt(filters.min_credits_used);
      if (filters.max_credits_used) params.max_credits_used = parseInt(filters.max_credits_used);
      if (filters.min_credits_remaining) params.min_credits_remaining = parseInt(filters.min_credits_remaining);
      if (filters.max_credits_remaining) params.max_credits_remaining = parseInt(filters.max_credits_remaining);
      if (filters.min_job_count) params.min_job_count = parseInt(filters.min_job_count);
      if (filters.max_job_count) params.max_job_count = parseInt(filters.max_job_count);
      
      // Add sorting parameters
      if (sortBy) {
        params.sort_by = sortBy;
        params.sort_order = sortOrder;
      }
      
      const data = await APIService.listUsers(params);
      setUsers(data.users || []);
      setPagination(prev => ({ ...prev, total: data.total || 0 }));
      setError(null);
    } catch (err) {
      setError(err.message || 'Failed to load users');
      console.error('Users list error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    setPagination(prev => ({ ...prev, skip: 0 }));
  };

  const handleTierFilter = (tier) => {
    setFilters(prev => ({ ...prev, tier: tier === prev.tier ? '' : tier }));
    setPagination(prev => ({ ...prev, skip: 0 }));
  };

  const handleNumericFilterDraftChange = (field, value) => {
    // Only allow numeric input - update draft without triggering API call
    if (value === '' || /^-?\d+$/.test(value)) {
      setNumericFilterDrafts(prev => ({ ...prev, [field]: value }));
    }
  };

  const applyNumericFilters = () => {
    // Apply draft values to actual filters (triggers API call)
    setFilters(prev => ({
      ...prev,
      min_credits_used: numericFilterDrafts.min_credits_used,
      max_credits_used: numericFilterDrafts.max_credits_used,
      min_credits_remaining: numericFilterDrafts.min_credits_remaining,
      max_credits_remaining: numericFilterDrafts.max_credits_remaining,
      min_job_count: numericFilterDrafts.min_job_count,
      max_job_count: numericFilterDrafts.max_job_count
    }));
    setPagination(prev => ({ ...prev, skip: 0 }));
  };

  const clearNumericFilters = () => {
    // Clear both drafts and active filters
    setNumericFilterDrafts({
      min_credits_used: '',
      max_credits_used: '',
      min_credits_remaining: '',
      max_credits_remaining: '',
      min_job_count: '',
      max_job_count: ''
    });
    setFilters(prev => ({
      ...prev,
      min_credits_used: '',
      max_credits_used: '',
      min_credits_remaining: '',
      max_credits_remaining: '',
      min_job_count: '',
      max_job_count: ''
    }));
    setPagination(prev => ({ ...prev, skip: 0 }));
  };

  const handlePageChange = (newSkip) => {
    setPagination(prev => ({ ...prev, skip: newSkip }));
  };

  const handleSort = (field) => {
    if (sortBy === field) {
      // Toggle sort order if clicking the same field
      setSortOrder(prev => prev === 'desc' ? 'asc' : 'desc');
    } else {
      // Set new sort field, default to descending
      setSortBy(field);
      setSortOrder('desc');
    }
    setPagination(prev => ({ ...prev, skip: 0 }));
  };

  if (loading && users.length === 0) {
    return (
      <div className="admin-users-list">
        <div className="loading">Loading users...</div>
      </div>
    );
  }

  return (
    <div className="admin-users-list">
      <div className="users-header">
        <h1>User Management</h1>
        <button
          onClick={() => {
            window.location.pathname = '/admin';
          }}
          className="btn-secondary"
        >
          ← Back to Dashboard
        </button>
      </div>

      {/* Filters */}
      <div className="filters-section">
        <form onSubmit={handleSearch} className="search-form">
          <input
            type="text"
            placeholder="Search by email or name..."
            value={filters.search}
            onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
            className="search-input"
          />
          <button type="submit" className="btn-primary">Search</button>
        </form>

        <div className="tier-filters">
          <span>Filter by tier:</span>
          <button
            onClick={() => handleTierFilter('')}
            className={`tier-filter-btn ${filters.tier === '' ? 'active' : ''}`}
          >
            All
          </button>
          {availableTiers.map(tier => (
            <button
              key={tier.tier_key}
              onClick={() => handleTierFilter(tier.tier_key)}
              className={`tier-filter-btn ${filters.tier === tier.tier_key ? 'active' : ''}`}
            >
              {tier.display_name}
            </button>
          ))}
        </div>

        <div className="numeric-filters-section">
          <div className="numeric-filters">
            <div className="numeric-filter-group">
              <label>Lifetime Credits Used:</label>
              <input
                type="number"
                placeholder="Min"
                value={numericFilterDrafts.min_credits_used}
                onChange={(e) => handleNumericFilterDraftChange('min_credits_used', e.target.value)}
                className="numeric-input"
              />
              <span>to</span>
              <input
                type="number"
                placeholder="Max"
                value={numericFilterDrafts.max_credits_used}
                onChange={(e) => handleNumericFilterDraftChange('max_credits_used', e.target.value)}
                className="numeric-input"
              />
            </div>

            <div className="numeric-filter-group">
              <label>Remaining Credits:</label>
              <input
                type="number"
                placeholder="Min"
                value={numericFilterDrafts.min_credits_remaining}
                onChange={(e) => handleNumericFilterDraftChange('min_credits_remaining', e.target.value)}
                className="numeric-input"
              />
              <span>to</span>
              <input
                type="number"
                placeholder="Max"
                value={numericFilterDrafts.max_credits_remaining}
                onChange={(e) => handleNumericFilterDraftChange('max_credits_remaining', e.target.value)}
                className="numeric-input"
              />
            </div>

            <div className="numeric-filter-group">
              <label>Total PDF Runs:</label>
              <input
                type="number"
                placeholder="Min"
                value={numericFilterDrafts.min_job_count}
                onChange={(e) => handleNumericFilterDraftChange('min_job_count', e.target.value)}
                className="numeric-input"
              />
              <span>to</span>
              <input
                type="number"
                placeholder="Max"
                value={numericFilterDrafts.max_job_count}
                onChange={(e) => handleNumericFilterDraftChange('max_job_count', e.target.value)}
                className="numeric-input"
              />
            </div>

            <div className="numeric-filter-actions">
              <button
                type="button"
                onClick={applyNumericFilters}
                className="btn-primary"
              >
                Apply Filters
              </button>
              <button
                type="button"
                onClick={clearNumericFilters}
                className="btn-secondary"
              >
                Clear
              </button>
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className="error-message">
          Error: {error}
          <button onClick={loadUsers} className="btn-secondary">Retry</button>
        </div>
      )}

      {/* Users Table */}
      <div className="users-table-container">
        <table className="users-table">
          <thead>
            <tr>
              <th>Email</th>
              <th>Name</th>
              <th>Tier</th>
              <th>Status</th>
              <th 
                className="numeric-col sortable" 
                onClick={() => handleSort('credits_used_total')}
                style={{ cursor: 'pointer', userSelect: 'none' }}
              >
                Credits Used
                {sortBy === 'credits_used_total' && (
                  <span className="sort-indicator">{sortOrder === 'desc' ? ' ↓' : ' ↑'}</span>
                )}
              </th>
              <th 
                className="numeric-col sortable" 
                onClick={() => handleSort('credits_remaining')}
                style={{ cursor: 'pointer', userSelect: 'none' }}
              >
                Credits Remaining
                {sortBy === 'credits_remaining' && (
                  <span className="sort-indicator">{sortOrder === 'desc' ? ' ↓' : ' ↑'}</span>
                )}
              </th>
              <th 
                className="numeric-col sortable" 
                onClick={() => handleSort('total_pdf_runs')}
                style={{ cursor: 'pointer', userSelect: 'none' }}
              >
                PDF Runs
                {sortBy === 'total_pdf_runs' && (
                  <span className="sort-indicator">{sortOrder === 'desc' ? ' ↓' : ' ↑'}</span>
                )}
              </th>
              <th>Custom Limits</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map(user => (
              <tr key={user.id}>
                <td>{user.email}</td>
                <td>{user.first_name || ''} {user.last_name || ''}</td>
                <td>
                  <span className={`tier-badge tier-${user.subscription_tier}`}>
                    {availableTiers.find(t => t.tier_key === user.subscription_tier)?.display_name || user.subscription_tier}
                  </span>
                </td>
                <td>
                  <span className={`status-badge ${user.is_active ? 'active' : 'inactive'}`}>
                    {user.is_active ? 'Active' : 'Inactive'}
                  </span>
                  {user.is_superuser && <span className="admin-badge">Admin</span>}
                </td>
                <td className="numeric-col">{user.credits_used_total || 0}</td>
                <td className="numeric-col">{user.credits_remaining || 0}</td>
                <td className="numeric-col">{user.total_pdf_runs || 0}</td>
                <td>
                  {user.custom_limits_enabled ? (
                    <span className="custom-limits-badge">Yes</span>
                  ) : (
                    <span className="no-custom-limits">No</span>
                  )}
                </td>
                <td>{new Date(user.created_at).toLocaleDateString()}</td>
                <td>
                  <button
                    onClick={() => {
                      window.location.pathname = `/admin/users/${user.id}`;
                    }}
                    className="btn-link"
                  >
                    View Details
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {pagination.total > pagination.limit && (
        <div className="pagination">
          <button
            onClick={() => handlePageChange(Math.max(0, pagination.skip - pagination.limit))}
            disabled={pagination.skip === 0}
            className="btn-secondary"
          >
            Previous
          </button>
          <span>
            Showing {pagination.skip + 1} - {Math.min(pagination.skip + pagination.limit, pagination.total)} of {pagination.total}
          </span>
          <button
            onClick={() => handlePageChange(pagination.skip + pagination.limit)}
            disabled={pagination.skip + pagination.limit >= pagination.total}
            className="btn-secondary"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}

export default AdminUsersList;
