// BackupHistoryPage.tsx
// Backup History page for DriveSafe

import React, { useEffect, useMemo, useState } from "react";
import "../App.css";

type BackupRecord = {
  id: number;
  filename: string;
  date: string;
  file_count?: number;
  size_mb?: string;
  md5?: string;
  status?: string;
};

const BackupHistoryPage = () => {
  const [history, setHistory] = useState<BackupRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [userEmail] = useState(localStorage.getItem("user_email") || "user@example.com");
  const [userName] = useState(localStorage.getItem("user_name") || "Authenticated via Google");

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const response = await fetch("http://localhost:5000/history");
        const data = await response.json();
        setHistory(data);
      } catch (error) {
        console.error("Failed to fetch history:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    window.location.hash = "";
  };

  const parseSizeMb = (size?: string) => {
    const num = parseFloat(size || "0");
    return Number.isFinite(num) ? num : 0;
  };

  const formatSize = (sizeMb: number) => {
    if (sizeMb >= 1024) return `${(sizeMb / 1024).toFixed(1)} GB`;
    return `${sizeMb.toFixed(1)} MB`;
  };

  const getExpiresBadge = (dateStr: string) => {
    const created = new Date(dateStr);
    if (Number.isNaN(created.getTime())) {
      return { label: "Expires soon", className: "expires-red" };
    }
    const diffDays = Math.max(
      0,
      7 - Math.floor((Date.now() - created.getTime()) / (1000 * 60 * 60 * 24))
    );
    const label =
      diffDays === 0
        ? "Expires today"
        : `Expires in ${diffDays} day${diffDays === 1 ? "" : "s"}`;
    if (diffDays >= 4) return { label, className: "expires-green" };
    if (diffDays >= 2) return { label, className: "expires-yellow" };
    return { label, className: "expires-red" };
  };

  const stats = useMemo(() => {
    const totalSizeMb = history.reduce(
      (sum, item) => sum + parseSizeMb(item.size_mb),
      0
    );
    const successCount = history.filter((item) => {
      const status = (item.status || "").toLowerCase();
      return status === "success" || status === "completed";
    }).length;
    const total = history.length;
    const successRate = total ? Math.round((successCount / total) * 100) : 0;
    return {
      totalArchives: history.length,
      totalSizeMb,
      successRate,
    };
  }, [history]);

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
              <div className="dashboard-user-email">{userEmail}</div>
              <div className="dashboard-user-auth">{userName}</div>
            </div>
            <button className="dashboard-logout-btn" onClick={handleLogout}>
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M4 4L12 12M12 4L4 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                <path d="M10 4L14 4L14 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M14 8L10 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
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
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M4 4H16C16.5523 4 17 4.44772 17 5V15C17 15.5523 16.5523 16 16 16H4C3.44772 16 3 15.5523 3 15V5C3 4.44772 3.44772 4 4 4Z" stroke="currentColor" strokeWidth="1.5"/>
                <path d="M3 8H17" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                <path d="M7 4V8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                <path d="M10 6L12 8L10 10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              <span>New Backup</span>
            </a>
            <a href="#backup-history" className="dashboard-nav-item active">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M10 3V10M10 10L13 13M10 10L7 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M3 17H17C17.5523 17 18 16.5523 18 16V4C18 3.44772 17.5523 3 17 3H3C2.44772 3 2 3.44772 2 4V16C2 16.5523 2.44772 17 3 17Z" stroke="currentColor" strokeWidth="1.5"/>
              </svg>
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
                <div className="summary-card-value">{stats.totalArchives} archives</div>
              </div>
            </div>

            <div className="summary-card">
              <div className="summary-card-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M20 13V17C20 18.1046 19.1046 19 18 19H6C4.89543 19 4 18.1046 4 17V13" stroke="#2563eb" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M12 15L12 5" stroke="#2563eb" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M8 9L12 5L16 9" stroke="#2563eb" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <div className="summary-card-content">
                <div className="summary-card-label">Total Size</div>
                <div className="summary-card-value">{formatSize(stats.totalSizeMb)}</div>
              </div>
            </div>

            <div className="summary-card">
              <div className="summary-card-icon success-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M5 13L9 17L19 7" stroke="#059669" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <div className="summary-card-content">
                <div className="summary-card-label">Success Rate</div>
                <div className="summary-card-value">{stats.successRate}%</div>
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
              {history.map((backup) => {
                const expiry = getExpiresBadge(backup.date);
                return (
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
                        <span className="backup-info">
                          {(backup.file_count ?? 0).toString()} files
                        </span>
                        <span className="backup-info">
                          {backup.size_mb || "0 MB"}
                        </span>
                        <span className="backup-md5">MD5: {backup.md5}</span>
                        <span className={`expires-tag ${expiry.className}`}>
                          {expiry.label}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="backup-item-right">
                    <button className="btn-download">
                      <span>Download</span>
                    </button>
                  </div>
                </div>
              )})}
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