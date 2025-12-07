// DashboardPage.tsx
// Dashboard page for DriveSafe after login

import React from "react";
import "../App.css";

const DashboardPage = () => {
  const handleLogout = () => {
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
            <a href="#dashboard" className="dashboard-nav-item active">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M4 4H16C16.5523 4 17 4.44772 17 5V15C17 15.5523 16.5523 16 16 16H4C3.44772 16 3 15.5523 3 15V5C3 4.44772 3.44772 4 4 4Z" stroke="currentColor" strokeWidth="1.5"/>
                <path d="M3 8H17" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                <path d="M7 4V8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                <path d="M10 6L12 8L10 10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              <span>New Backup</span>
            </a>
            <a href="#backup-history" className="dashboard-nav-item">
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
          <div className="dashboard-card">
            {/* Card Header */}
            <div className="dashboard-card-header">
              <div>
                <h1 className="dashboard-card-title">Create New Backup</h1>
                <p className="dashboard-card-description">
                  Automatically backup your Google Drive files with AI-powered analysis
                </p>
              </div>
              <div className="dashboard-card-icon">
                <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <circle cx="16" cy="16" r="14" fill="#e0f2fe"/>
                  <path d="M16 8V16M16 16L20 20M16 16L12 20" stroke="#2563eb" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <rect x="8" y="22" width="16" height="4" rx="1" fill="#2563eb"/>
                </svg>
              </div>
            </div>

            {/* Metrics */}
            <div className="dashboard-metrics">
              <div className="dashboard-metric-card metric-blue">
                <div className="metric-label">Files Ready</div>
                <div className="metric-value">87 files</div>
              </div>
              <div className="dashboard-metric-card metric-purple">
                <div className="metric-label">Est. Size</div>
                <div className="metric-value">245 MB</div>
              </div>
              <div className="dashboard-metric-card metric-purple">
                <div className="metric-label">Est. Time</div>
                <div className="metric-value">~2 min</div>
              </div>
            </div>

            {/* Start Backup Button */}
            <button className="btn-start-backup">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M6 4L14 10L6 16V4Z" fill="white"/>
              </svg>
              <span>Start Backup</span>
            </button>

            {/* Backup Process */}
            <div className="dashboard-process">
              <h3 className="process-title">Backup Process:</h3>
              <ul className="process-list">
                <li>Fetches up to 100 files from your Google Drive</li>
                <li>Compresses files into a secure ZIP archive</li>
                <li>Generates MD5 checksum for data integrity</li>
                <li>Archives are stored securely for 7 days</li>
              </ul>
            </div>

            {/* Privacy Compliance Banner */}
            <div className="dashboard-privacy-banner">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M10 1.66667L3.33333 4.16667V8.33333C3.33333 12.75 6.58333 16.6667 10 18.3333C13.4167 16.6667 16.6667 12.75 16.6667 8.33333V4.16667L10 1.66667Z" fill="#10b981" stroke="#10b981" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M7.5 10L9.16667 11.6667L12.5 8.33333" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              <p>
                All data Privacy Compliant with RA 10173 (Data Privacy Act of 2012). Your files are processed securely and automatically deleted after 7 days.
              </p>
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

export default DashboardPage;
