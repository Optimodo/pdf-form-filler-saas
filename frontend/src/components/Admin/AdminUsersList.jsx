import React, { useState, useEffect } from 'react';
import APIService from '../../services/api';
import './AdminUsersList.css';

function AdminUsersList() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pagination, setPagination] = useState({ skip: 0, limit: 50, total: 0 });
  const [filters, setFilters] = useState({ search: '', tier: '' });

  useEffect(() => {
    loadUsers();
  }, [pagination.skip, pagination.limit, filters.search, filters.tier]);

  const loadUsers = async () => {
    try {
      setLoading(true);
      const data = await APIService.listUsers({
        skip: pagination.skip,
        limit: pagination.limit,
        search: filters.search || undefined,
        tier: filters.tier || undefined,
      });
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
    loadUsers();
  };

  const handleTierFilter = (tier) => {
    setFilters(prev => ({ ...prev, tier: tier === prev.tier ? '' : tier }));
    setPagination(prev => ({ ...prev, skip: 0 }));
  };

  const handlePageChange = (newSkip) => {
    setPagination(prev => ({ ...prev, skip: newSkip }));
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
          {['free', 'basic', 'pro', 'enterprise'].map(tier => (
            <button
              key={tier}
              onClick={() => handleTierFilter(tier)}
              className={`tier-filter-btn ${filters.tier === tier ? 'active' : ''}`}
            >
              {tier}
            </button>
          ))}
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
              <th>Credits</th>
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
                    {user.subscription_tier}
                  </span>
                </td>
                <td>
                  <span className={`status-badge ${user.is_active ? 'active' : 'inactive'}`}>
                    {user.is_active ? 'Active' : 'Inactive'}
                  </span>
                  {user.is_superuser && <span className="admin-badge">Admin</span>}
                </td>
                <td>{user.credits_remaining}</td>
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

