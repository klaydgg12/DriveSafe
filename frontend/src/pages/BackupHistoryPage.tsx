// BackupHistoryPage.tsx
// Backup History page for DriveSafe

import React, { useEffect, useState } from "react";
import "../App.css";

const BackupHistoryPage = () => {
  // 1. State for real history data
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // 2. Fetch history from backend
  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const response = await fetch('http://localhost:5000/history');
        const data = await response.json();
        setHistory(data); // Save the real data
      } catch (error) {
        console.error("Failed to fetch history:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    window.location.hash = "";
  };

  return (
    <div className="drivesafe-dashboard-page">
      {/* Header Section */}
      <header className="header">
        <div className="container">
          <div className="dashboard-logo-section">
            <div className="dashboard-logo-icon-gradient">
              <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect x="2" y="2" width="28" height="28" rx="4" fill="url(#gradient)"/>
                <rect x="8" y="8" width="16" height="12" rx="1" stroke="white" strokeWidth="1.5" fill="none"/>
                <circle cx="12" cy="12" r="1.5" fill="white"/>
                <circle cx="20" cy="12" r="1.5" fill="white"/>
                <defs>
                  <linearGradient id="gradient" x1="0" y1="0" x2="32" y2="32">
                    <stop offset="0%" stopColor="#2563eb"/>
                    <stop offset="100%" stopColor="#9333ea"/>
                  </linearGradient>
                </defs>
              </svg>
            </div>
            <div className="dashboard-logo-text">
              <div className="dashboard-logo-title">DriveSafe</div>
              <div className="dashboard-logo-subtitle">Automated Backup Tool</div>
            </div>
          </div>
          <div className="dashboard-user-section">
            <div className="dashboard-user-info">
              <div className="dashboard-user-email">user@example.com</div>
              <div className="dashboard-user-auth">Authenticated via Google</div>
            </div>
            <button className="dashboard-logout-btn" onClick={handleLogout}>
              <span>Logout</span>
            </button>
          </div>
        </div>
      </header>

      {/* Secondary Navigation */}
      <nav className="dashboard-nav">
        <div className="container">
          <div className="dashboard-nav-container">
            <a href="#dashboard" className="dashboard-nav-item">
              <span>New Backup</span>
            </a>
            <a href="#backup-history" className="dashboard-nav-item active">
              <span>Backup History</span>
            </a>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="dashboard-main">
        <div className="container">
          
          {/* Summary Cards (DYNAMIC NOW) */}
          <div className="history-summary-cards">
            <div className="summary-card">
              <div className="summary-card-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M4 4H20C20.5523 4 21 4.44772 21 5V19C21 19.5523 20.5523 20 20 20H4C3.44772 20 3 19.5523 3 19V5C3 4.44772 3.44772 4 4 4Z" stroke="#2563eb" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <div className="summary-card-content">
                <div className="summary-card-label">Recent Backups</div>
                <div className="summary-card-value">{history.length} archives</div>
              </div>
            </div>
          </div>

          {/* Backup History Section */}
          <div className="history-section">
            <div className="history-header">
              <h1 className="history-title">Backup History</h1>
              <p className="history-subtitle">Showing your last 5 backups • Archives auto-delete after 7 days</p>
            </div>

            {/* EMPTY STATE: If no backups exist yet */}
            {history.length === 0 && !loading && (
              <div style={{ textAlign: 'center', padding: '50px', color: '#64748b' }}>
                <h3>No backups found yet.</h3>
                <p>Go to the Dashboard to create your first backup!</p>
              </div>
            )}

            {/* REAL LIST: Only shows if data exists */}
            <div className="backup-list">
              {history.map((backup) => (
                <div key={backup.id} className="backup-item">
                  <div className="backup-item-left">
                    <div className="backup-icon">
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M4 4H20C20.5523 4 21 4.44772 21 5V19C21 19.5523 20.5523 20 20 20H4C3.44772 20 3 19.5523 3 19V5C3 4.44772 3.44772 4 4 4Z" stroke="#2563eb" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    </div>
                    <div className="backup-details">
                      <div className="backup-filename">{backup.filename}</div>
                      <div className="backup-meta">
                        <span className="backup-date">{backup.date}</span>
                        <span className="backup-status" style={{color: 'green'}}>
                          {backup.status}
                        </span>
                        <span className="backup-info">{backup.files}</span>
                        <span className="backup-info">{backup.size}</span>
                        <span className="backup-md5">MD5: {backup.md5}</span>
                      </div>
                    </div>
                  </div>
                  <div className="backup-item-right">
                    <button className="btn-download">
                      <span>Download</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </main>

      <footer className="dashboard-footer">
        <div className="container">
          <p>DriveSafe v1.0 © 2025 CEBU INSTITUTE OF TECHNOLOGY UNIVERSITY College of Computer Studies.</p>
        </div>
      </footer>
    </div>
  );
};

export default BackupHistoryPage;