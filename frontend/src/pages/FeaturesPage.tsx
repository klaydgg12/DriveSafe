// FeaturesPage.tsx
// Features page for DriveSafe

import React, { useState } from "react";
import "./FeaturesPage.css";

// Data structure for features to make mapping easier
const featuresData = [
  {
    id: 1,
    icon: "🔒",
    title: "Secure Authentication",
    description: "OAuth 2.0 protected login ensures your Google account credentials are never stored on our servers.",
    list: ["Zero password storage", "Encrypted connections", "RA 10173 compliant"],
    details: "We utilize the official Google Identity Services SDK to handle the OAuth 2.0 Authorization Code Flow. This means your password never touches our backend. We only receive a temporary access token which is encrypted using AES-256 before being stored in a secure HTTP-only cookie."
  },
  {
    // NEW FEATURE: The "Star" of your show!
    id: 2,
    icon: "🧠", // Brain icon for AI
    title: "AI-Powered Organization",
    description: "Our Machine Learning engine automatically analyzes and sorts your files into smart categories.",
    list: ["Auto-categorization", "Separates School vs. Personal", "Smart tagging system"],
    details: "This is the core intelligence of DriveSafe. Using Python's 'scikit-learn' library, our backend analyzes file metadata (extensions, naming patterns, and sizes). It runs a classification algorithm to tag files as 'Academic', 'Multimedia', or 'Personal' before zipping them, ensuring your backup is organized, not just a messy dump."
  },
  {
    id: 3,
    icon: "⚡",
    title: "One-Click Backup",
    description: "Start a complete backup with a single click. Our system automatically fetches, compresses, and secures files.",
    list: ["Automated file fetching", "Smart ZIP compression", "Process in under 2 minutes"],
    details: "Our Python backend uses the Google Drive API v3 to recursively walk through your folders. It streams file data directly into a ZIP archive using the 'zipfile' library, meaning we don't need to save temporary files to our disk, greatly increasing speed and security."
  },
  {
    id: 4,
    icon: "✅",
    title: "Data Integrity",
    description: "Every backup includes MD5 checksum verification to ensure your files are perfectly preserved.",
    list: ["MD5 checksum generation", "Integrity verification", "Corruption detection"],
    details: "After creating the ZIP archive, we calculate its MD5 hash and compare it against the checksums provided by Google Drive's metadata. If even a single bit is different, the system flags the backup as 'Corrupted' and automatically retries the download."
  },
  {
    id: 5,
    icon: "🕒",
    title: "Backup History",
    description: "Access and manage your last 5 backups. View detailed metadata including file count and size.",
    list: ["Last 5 backups tracked", "Detailed metadata display", "Easy download access"],
    details: "We use a lightweight SQLite database to track your backup history. Each entry stores the timestamp, file size, file count, and expiration date. This allows the frontend to render your history instantly without needing to scan the storage system every time."
  },
  {
    id: 6,
    icon: "📦",
    title: "Smart Archiving",
    description: "Archives are stored securely for 7 days, giving you time to download while managing storage.",
    list: ["7-day secure storage", "Auto-deletion policy", "Expiration tracking"],
    details: "A scheduled 'Cron Job' runs on our server every midnight. It checks the creation date of all ZIP files. Any file older than 7 days is securely wiped using a secure delete standard to ensure compliance with data minimization principles."
  }
];

const FeaturesPage = () => {
  const [selectedFeature, setSelectedFeature] = useState<any>(null);

  const handleGetStarted = () => {
    window.location.hash = "signin";
  };

  const openModal = (feature: any) => {
    setSelectedFeature(feature);
    document.body.style.overflow = 'hidden'; // Prevent scrolling when modal is open
  };

  const closeModal = () => {
    setSelectedFeature(null);
    document.body.style.overflow = 'unset';
  };

  return (
    <div className="drivesafe-features-page">
      {/* Header Section */}
      <header className="header">
        <div className="container">
          <div className="logo-container">
            <div className="logo-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect x="3" y="3" width="18" height="18" rx="2" fill="#2563eb"/>
                <rect x="7" y="7" width="10" height="10" rx="1" fill="white"/>
                <rect x="9" y="9" width="6" height="6" rx="0.5" fill="#2563eb"/>
              </svg>
            </div>
            <div className="logo">DriveSafe</div>
          </div>
          <nav className="nav">
            <a href="#">Home</a>
            <a href="#features">Features</a>
            <a href="#about">About</a>
            <button className="btn btn-primary btn-header" onClick={handleGetStarted}>Get Started</button>
          </nav>
        </div>
      </header>

      {/* Features Hero Section */}
      <section className="features-hero">
        <div className="container">
          <h1 className="features-title">Powerful Features</h1>
          <p className="features-subtitle">Everything You Need for Safe Backups</p>
          <p className="features-description">
            DriveSafe provides enterprise-grade features designed specifically for students and educators.
            <br />
            <span style={{ fontSize: '0.9em', color: '#2563eb', fontWeight: 600 }}>
              (Click on any feature card to learn how it works)
            </span>
          </p>
        </div>
      </section>

      {/* Features Grid with Performance Stats */}
      <section className="features-grid-section">
        <div className="container">
          <div className="features-grid">
            {featuresData.map((feature) => (
              <div 
                key={feature.id} 
                className="feature-card interactive-card" 
                onClick={() => openModal(feature)}
              >
                <div className="feature-icon">{feature.icon}</div>
                <h3 className="feature-title">{feature.title}</h3>
                <p className="feature-description">
                  {feature.description}
                </p>
                <ul className="feature-list">
                  {feature.list.map((item, index) => (
                    <li key={index}>{item}</li>
                  ))}
                </ul>
                <div className="click-indicator">
                  <span>Learn more</span>
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M6 12L10 8L6 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Performance Section */}
      <section className="performance-section">
        <div className="container">
          <div className="performance-header">
            <h2 className="performance-title">Built for Performance</h2>
            <p className="performance-description">Our system is optimized for speed and reliability</p>
          </div>
          <div className="performance-stats-grid">
            <div className="performance-stat-card">
              <div className="stat-value">95%</div>
              <div className="stat-label">Success Rate</div>
            </div>
            <div className="performance-stat-card">
              <div className="stat-value">&lt; 2 min</div>
              <div className="stat-label">Backup Time</div>
            </div>
            <div className="performance-stat-card">
              <div className="stat-value">100 files</div>
              <div className="stat-label">Per Backup</div>
            </div>
            <div className="performance-stat-card">
              <div className="stat-value">100%</div>
              <div className="stat-label">Encrypted</div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="footer">
        <div className="container">
          <div className="footer-content">
            <div className="footer-column">
              <h3>DriveSafe</h3>
              <p>Protecting your academic files with automated backups.</p>
            </div>
            <div className="footer-column">
              <h4>Product</h4>
              <a href="#">Home</a>
              <a href="#">Features</a>
              <a href="#about">About</a>
            </div>
            <div className="footer-column">
              <h4>Resources</h4>
              <a href="#">Documentation</a>
              <a href="#">Support</a>
            </div>
            <div className="footer-column">
              <h4>Legal</h4>
              <a href="#">Privacy Policy</a>
              <a href="#">Terms of Service</a>
            </div>
          </div>
          <div className="footer-bottom">
            <p>&copy; 2023 DriveSafe. All rights reserved.</p>
          </div>
        </div>
      </footer>

      {/* Interactive Feature Modal */}
      {selectedFeature && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="feature-modal" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close-btn" onClick={closeModal}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M18 6L6 18M6 6L18 18" stroke="#64748b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
            
            <div className="modal-header">
              <div className="modal-icon">{selectedFeature.icon}</div>
              <h2 className="modal-title">{selectedFeature.title}</h2>
            </div>
            
            <div className="modal-body">
              <h4 className="modal-section-title">Overview</h4>
              <p className="modal-text">{selectedFeature.description}</p>
              
              <h4 className="modal-section-title">Technical How-It-Works</h4>
              <div className="technical-box">
                <p>{selectedFeature.details}</p>
              </div>
              
              <h4 className="modal-section-title">Key Capabilities</h4>
              <ul className="modal-list">
                {selectedFeature.list.map((item: string, index: number) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FeaturesPage;