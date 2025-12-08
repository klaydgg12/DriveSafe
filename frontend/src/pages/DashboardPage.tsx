// DashboardPage.tsx
// Dashboard page for DriveSafe after login

import React, { useEffect, useState } from "react";
import "../App.css";

const DashboardPage = () => {
  // 1. State to hold the data from Python
  const [files, setFiles] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [isBackingUp, setIsBackingUp] = useState(false);
  const [userEmail, setUserEmail] = useState(localStorage.getItem("user_email") || "user@example.com");
  const [userName, setUserName] = useState(localStorage.getItem("user_name") || "Authenticated via Google");

  // 2. Fetch data from Python Backend on load
  // Inside DashboardPage.tsx

  useEffect(() => {
    const fetchDriveFiles = async () => {
      console.log("--- FRONTEND DEBUG: Starting Fetch... ---"); // Spy 1
      
      const token = localStorage.getItem('access_token');
      console.log("--- FRONTEND DEBUG: Token found?", token ? "YES" : "NO"); // Spy 2

      if (!token) {
        console.error("--- FRONTEND ERROR: No token! Aborting fetch. ---");
        return;
      }

      setLoading(true);
      try {
        console.log("--- FRONTEND DEBUG: Sending request to Backend... ---"); // Spy 3
        const response = await fetch('http://localhost:5000/drive/files', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        console.log("--- FRONTEND DEBUG: Response Status:", response.status); // Spy 4
        const data = await response.json();
        console.log("--- FRONTEND DEBUG: Data received:", data); // Spy 5
        
        if (data.files) {
          setFiles(data.files);
          setStats(data.ai_stats);
        }
      } catch (error) {
        console.error("--- FRONTEND ERROR: Connection Failed:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchDriveFiles();
  }, []);
  const handleStartBackup = async () => {
  if (files.length === 0) {
    alert("No files found to backup! Please add files to your Google Drive first.");
    return;
  }

  setIsBackingUp(true);
  const token = localStorage.getItem('access_token');

  try {
    const response = await fetch('http://localhost:5000/drive/backup', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    
    const data = await response.json();
    
    if (response.ok) {
      alert(`Backup Successful!\nFile: ${data.filename}\nSize: ${data.size}`);
      // Redirect to history to see it
      window.location.hash = "backup-history";
    } else {
      alert("Backup Failed: " + data.error);
    }
  } catch (error) {
    console.error("Backup error:", error);
    alert("Network error during backup.");
  } finally {
    setIsBackingUp(false);
  }
};

  const handleLogout = () => {
    // In a real app, you might want to clear the token too
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

            {/* Metrics - NOW CONNECTED TO REAL AI DATA */}
            <div className="dashboard-metrics">
              <div className="dashboard-metric-card metric-blue">
                <div className="metric-label">Files Found</div>
                <div className="metric-value">
                  {loading ? "Scanning..." : `${files.length} files`}
                </div>
              </div>
              <div className="dashboard-metric-card metric-purple">
                <div className="metric-label">Academic Files (AI)</div>
                <div className="metric-value">
                  {loading ? "..." : (stats ? stats.Academic : 0)}
                </div>
              </div>
              <div className="dashboard-metric-card metric-purple">
                <div className="metric-label">Personal Files (AI)</div>
                <div className="metric-value">
                  {loading ? "..." : (stats ? stats.Personal : 0)}
                </div>
              </div>
            </div>
            {/* --- NEW: FILE PREVIEW LIST --- */}
            <div style={{ marginTop: '20px', marginBottom: '20px' }}>
              <h3 style={{ fontSize: '16px', color: '#1e293b', marginBottom: '10px' }}>
                Detected Files ({files.length})
              </h3>
              
              <div style={{ 
                border: '1px solid #e2e8f0', 
                borderRadius: '8px', 
                maxHeight: '200px', 
                overflowY: 'auto',
                background: '#f8fafc' 
              }}>
                {files.length === 0 ? (
                  <div style={{ padding: '20px', textAlign: 'center', color: '#94a3b8', fontSize: '14px' }}>
                    Scanning for files...
                  </div>
                ) : (
                  files.map((file) => (
                    <div key={file.id} style={{ 
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      alignItems: 'center',
                      padding: '10px 15px',
                      borderBottom: '1px solid #e2e8f0',
                      fontSize: '14px',
                      background: 'white'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', overflow: 'hidden' }}>
                        {/* Simple Icon based on AI Category */}
                        <span>
                          {file.category === 'Academic' ? '📚' : 
                           file.category === 'Personal' ? '🖼️' : '📄'}
                        </span>
                        <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '200px', fontWeight: 500 }}>
                          {file.name}
                        </span>
                      </div>
                      
                      {/* The AI Tag */}
                      <span style={{ 
                        fontSize: '12px', 
                        padding: '2px 8px', 
                        borderRadius: '12px',
                        backgroundColor: file.category === 'Academic' ? '#dbeafe' : 
                                         file.category === 'Personal' ? '#fce7f3' : '#f1f5f9',
                        color: file.category === 'Academic' ? '#1e40af' : 
                               file.category === 'Personal' ? '#be185d' : '#475569',
                        fontWeight: 600
                      }}>
                        {file.category || "Analyzing..."}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Start Backup Button */}
            <button 
  className="btn-start-backup" 
  onClick={handleStartBackup} 
  disabled={isBackingUp || loading}
  style={{ opacity: isBackingUp ? 0.7 : 1 }}
>
  <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M6 4L14 10L6 16V4Z" fill="white"/>
  </svg>
  <span>{isBackingUp ? "Backing up..." : "Start Backup"}</span>
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