// FeaturesPage.tsx
// Features page for DriveSafe

import React from "react";
import "./FeaturesPage.css";

const FeaturesPage = () => {
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
            <a href="#signin">Sign In</a>
            <button className="btn btn-primary btn-header">Get Started</button>
          </nav>
        </div>
      </header>

      {/* Features Hero Section */}
      <section className="features-hero">
        <div className="container">
          <h1 className="features-title">Powerful Features</h1>
          <p className="features-subtitle">Everything You Need for Safe Backups</p>
          <p className="features-description">
            DriveSafe provides enterprise-grade features designed specifically for students and educators
          </p>
        </div>
      </section>

      {/* Features Grid with Performance Stats */}
      <section className="features-grid-section">
        <div className="container">
          <div className="features-grid">
            {/* Secure Authentication */}
            <div className="feature-card">
              <div className="feature-icon">🔒</div>
              <h3 className="feature-title">Secure Authentication</h3>
              <p className="feature-description">
                OAuth 2.0 protected login ensures your Google account credentials are never stored on our servers. 
                Full compliance with RA 10173 Data Privacy Act.
              </p>
              <ul className="feature-list">
                <li>Zero password storage</li>
                <li>Encrypted connections</li>
                <li>RA 10173 compliant</li>
              </ul>
            </div>

            {/* One-Click Backup */}
            <div className="feature-card">
              <div className="feature-icon">⚡</div>
              <h3 className="feature-title">One-Click Backup</h3>
              <p className="feature-description">
                Start a complete backup with a single click. Our system automatically fetches, compresses, 
                and secures up to 100 files from your Drive.
              </p>
              <ul className="feature-list">
                <li>Automated file fetching</li>
                <li>Smart ZIP compression</li>
                <li>Process in under 2 minutes</li>
              </ul>
            </div>

            {/* Data Integrity */}
            <div className="feature-card">
              <div className="feature-icon">✅</div>
              <h3 className="feature-title">Data Integrity</h3>
              <p className="feature-description">
                Every backup includes MD5 checksum verification to ensure your files are perfectly preserved 
                without corruption or data loss.
              </p>
              <ul className="feature-list">
                <li>MD5 checksum generation</li>
                <li>Integrity verification</li>
                <li>Corruption detection</li>
              </ul>
            </div>

            {/* Backup History */}
            <div className="feature-card">
              <div className="feature-icon">🕒</div>
              <h3 className="feature-title">Backup History</h3>
              <p className="feature-description">
                Access and manage your last 5 backups. View detailed metadata including file count, size, 
                timestamps, and expiration dates.
              </p>
              <ul className="feature-list">
                <li>Last 5 backups tracked</li>
                <li>Detailed metadata display</li>
                <li>Easy download access</li>
              </ul>
            </div>

            {/* Smart Archiving */}
            <div className="feature-card">
              <div className="feature-icon">📦</div>
              <h3 className="feature-title">Smart Archiving</h3>
              <p className="feature-description">
                Archives are stored securely for 7 days, giving you time to download while automatically 
                managing storage constraints.
              </p>
              <ul className="feature-list">
                <li>7-day secure storage</li>
                <li>Auto-deletion policy</li>
                <li>Expiration tracking</li>
              </ul>
            </div>

            {/* Simple Dashboard */}
            <div className="feature-card">
              <div className="feature-icon">📊</div>
              <h3 className="feature-title">Simple Dashboard</h3>
              <p className="feature-description">
                Clean, intuitive interface shows backup progress, file statistics, and provides instant access 
                to your archive history.
              </p>
              <ul className="feature-list">
                <li>Real-time progress tracking</li>
                <li>File statistics display</li>
                <li>User-friendly interface</li>
              </ul>
            </div>


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
              <a href="#signin">Sign In</a>
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
    </div>
  );
};

export default FeaturesPage;