// BackupHistoryPage.tsx
// Backup History page for DriveSafe

import React from "react";
import "../App.css";

const BackupHistoryPage = () => {
  const handleLogout = () => {
    window.location.hash = "";
  };

  const backups = [
    {
      filename: "backup_2025-11-27.zip",
      date: "2025-11-27 14:35:22",
      files: "87 files",
      size: "245 MB",
      md5: "a3f5e9d2c4b1",
      expiresIn: "6 days",
      expiresColor: "green"
    },
    {
      filename: "backup_2025-11-20.zip",
      date: "2025-11-20 09:15:10",
      files: "82 files",
      size: "231 MB",
      md5: "b7c2a1f8e5d3",
      expiresIn: "2 days",
      expiresColor: "yellow"
    },
    {
      filename: "backup_2025-11-13.zip",
      date: "2025-11-13 16:42:05",
      files: "78 files",
      size: "218 MB",
      md5: "c9e4f3a1b6d2",
      expiresIn: "1 day",
      expiresColor: "red"
    },
    {
      filename: "backup_2025-11-06.zip",
      date: "2025-11-06 11:20:35",
      files: "75 files",
      size: "205 MB",
      md5: "d1f7b3e9c2a4",
      expiresIn: "< 1 day",
      expiresColor: "red"
    },
    {
      filename: "backup_2025-10-30.zip",
      date: "2025-10-30 08:45:12",
      files: "71 files",
      size: "198 MB",
      md5: "e3a8c4f1d7b5",
      expiresIn: "< 1 day",
      expiresColor: "red"
    }
  ];

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
          {/* Summary Cards */}
          <div className="history-summary-cards">
            <div className="summary-card">
              <div className="summary-card-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M4 4H20C20.5523 4 21 4.44772 21 5V19C21 19.5523 20.5523 20 20 20H4C3.44772 20 3 19.5523 3 19V5C3 4.44772 3.44772 4 4 4Z" stroke="#2563eb" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M3 9H21" stroke="#2563eb" strokeWidth="2" strokeLinecap="round"/>
                  <path d="M7 4V9" stroke="#2563eb" strokeWidth="2" strokeLinecap="round"/>
                </svg>
              </div>
              <div className="summary-card-content">
                <div className="summary-card-label">Recent Backups</div>
                <div className="summary-card-value">5 archives</div>
              </div>
            </div>

            <div className="summary-card">
              <div className="summary-card-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M4 4H20C20.5523 4 21 4.44772 21 5V19C21 19.5523 20.5523 20 20 20H4C3.44772 20 3 19.5523 3 19V5C3 4.44772 3.44772 4 4 4Z" stroke="#2563eb" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <div className="summary-card-content">
                <div className="summary-card-label">Total Size</div>
                <div className="summary-card-value">1.1 GB</div>
              </div>
            </div>

            <div className="summary-card">
              <div className="summary-card-icon success-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <circle cx="12" cy="12" r="10" fill="#10b981"/>
                  <path d="M8 12L11 15L16 9" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <div className="summary-card-content">
                <div className="summary-card-label">Success Rate</div>
                <div className="summary-card-value">100%</div>
              </div>
            </div>
          </div>

          {/* Backup History Section */}
          <div className="history-section">
            <div className="history-header">
              <h1 className="history-title">Backup History</h1>
              <p className="history-subtitle">Showing your last 5 backups • Archives auto-delete after 7 days</p>
            </div>

            {/* Backup List */}
            <div className="backup-list">
              {backups.map((backup, index) => (
                <div key={index} className="backup-item">
                  <div className="backup-item-left">
                    <div className="backup-icon">
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M4 4H20C20.5523 4 21 4.44772 21 5V19C21 19.5523 20.5523 20 20 20H4C3.44772 20 3 19.5523 3 19V5C3 4.44772 3.44772 4 4 4Z" stroke="#2563eb" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                        <path d="M3 9H21" stroke="#2563eb" strokeWidth="2" strokeLinecap="round"/>
                      </svg>
                    </div>
                    <div className="backup-details">
                      <div className="backup-filename">{backup.filename}</div>
                      <div className="backup-meta">
                        <span className="backup-date">{backup.date}</span>
                        <span className="backup-status">
                          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <circle cx="8" cy="8" r="6" fill="#10b981"/>
                            <path d="M5 8L7 10L11 6" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                          </svg>
                          completed
                        </span>
                        <span className="backup-info">{backup.files}</span>
                        <span className="backup-info">{backup.size}</span>
                        <span className="backup-md5">MD5: {backup.md5}</span>
                      </div>
                    </div>
                  </div>
                  <div className="backup-item-right">
                    <div className={`expires-tag expires-${backup.expiresColor}`}>
                      Expires in {backup.expiresIn}
                    </div>
                    <button className="btn-download">
                      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M9 12V3M9 12L6 9M9 12L12 9" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                        <path d="M3 15H15" stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
                      </svg>
                      <span>Download</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {/* Warning Banners */}
            <div className="history-banner history-banner-warning">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M10 2L2 18H18L10 2Z" fill="#fbbf24" stroke="#fbbf24" strokeWidth="1.5"/>
                <path d="M10 7V11" stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
                <circle cx="10" cy="13" r="1" fill="white"/>
              </svg>
              <p>Auto-Deletion Policy: Backup archives are stored securely for 7 days and then automatically deleted. Download your backups before they expire to prevent data loss.</p>
            </div>

            <div className="history-banner history-banner-info">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="10" cy="10" r="8" fill="#2563eb"/>
                <path d="M10 6V10M10 14H10.01" stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
              <p>Only 5 backups are displayed. Creating a new backup when you have 5 existing backups will automatically delete the oldest one to maintain compliance with storage constraints.</p>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="dashboard-footer">
        <div className="container">
          <p>DriveSafe v1.0 © 2025 CEBU INSTITUTE OF TECHNOLOGY UNIVERSITY College of Computer Studies.</p>
        </div>
      </footer>
    </div>
  );
};

export default BackupHistoryPage;
