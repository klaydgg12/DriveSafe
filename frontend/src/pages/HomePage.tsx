// HomePage.tsx
// Main landing page for DriveSafe

import React from "react";

const HomePage = () => {
  
  // 1. Function to handle navigation to Sign In
  const handleGetStarted = () => {
    window.location.hash = "signin";
  };

  return (
    <div className="drivesafe-landing-page">
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
            {/* 2. Added onClick here */}
            <button className="btn btn-primary btn-header" onClick={handleGetStarted}>
              Get Started
            </button>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <section className="hero" id="home">
        <div className="container">
          {/* Two-column layout */}
          <div className="hero-layout">
            <div className="hero-content">
              <div className="badge-container">
                <div className="badge">Free for Students & Educators</div>
              </div>
              
              <h1 className="hero-title">Automated Google Drive Backup Tool</h1>
              <p className="hero-description">
                Protect your academic files with one-click automated backups. Simple, secure, and compliant with data privacy laws.
              </p>
              
              <div className="features-highlight">
                <div className="feature-item">
                  <div className="feature-icon feature-icon-shield">
                    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M10 2L3 5V9C3 13.55 6.36 17.74 10 19C13.64 17.74 17 13.55 17 9V5L10 2Z" stroke="#2563eb" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
                    </svg>
                  </div>
                  <div className="feature-content">
                    <h3>Enterprise Security</h3>
                    <p>OAuth 2.0 authentication with RA 10173 compliance</p>
                  </div>
                </div>
                
                <div className="feature-item">
                  <div className="feature-icon feature-icon-lightning">
                    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M11 2L4 12H10L9 18L16 8H10L11 2Z" fill="#9333ea" stroke="#9333ea" strokeWidth="1"/>
                    </svg>
                  </div>
                  <div className="feature-content">
                    <h3>Lightning Fast</h3>
                    <p>Process 100 files in under 2 minutes</p>
                  </div>
                </div>
                
                <div className="feature-item">
                  <div className="feature-icon feature-icon-clock">
                    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <circle cx="10" cy="10" r="8" stroke="#ec4899" strokeWidth="2" fill="none"/>
                      <path d="M10 6V10L13 13" stroke="#ec4899" strokeWidth="2" strokeLinecap="round"/>
                    </svg>
                  </div>
                  <div className="feature-content">
                    <h3>Backup History</h3>
                    <p>Access and manage your last 5 backups</p>
                  </div>
                </div>
              </div>
              
              <div className="stats">
                <div className="stat-item">
                  <div className="stat-value">100 files</div>
                  <div className="stat-label">Per backup</div>
                </div>
                
                <div className="stat-item">
                  <div className="stat-value">&lt; 2 minutes</div>
                  <div className="stat-label">Average time</div>
                </div>
                
                <div className="stat-item">
                  <div className="stat-value">95%</div>
                  <div className="stat-label">Success rate</div>
                </div>
              </div>
            </div>
            
            {/* Right Column */}
            <div className="hero-sidebar">
              <div className="combined-container">
                <h2 className="container-title">Get Started</h2>
                <p className="container-subtitle">Sign in with your Google account to start backing up your files</p>
                
                {/* 3. Added onClick here too */}
                <button className="btn btn-primary btn-medium btn-full-width" onClick={handleGetStarted}>
                  Get Started Free <span className="arrow">→</span>
                </button>
                
                <div className="container-details">
                  <p className="detail-item"><span className="checkmark">✓</span> No credit card required</p>
                  <p className="detail-item"><span className="checkmark">✓</span> RA 10173 compliant</p>
                  <p className="detail-item"><span className="checkmark">✓</span> MD5 integrity verification</p>
                  <hr className="divider" />
                  <p className="terms-text">By continuing, you agree to our Terms & Privacy Policy</p>
                </div>
              </div>
            </div>
          </div>
          
          {/* Trusted By Section */}
          <div className="trusted-section">
            <h3>Trusted by students and educators at</h3>
            <div className="logos">
              <div className="logo-item">
                <div className="logo-placeholder">CEBU INSTITUTE OF TECHNOLOGY UNIVERSITY</div>
              </div>
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
              <a href="#features">Features</a>
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
    </div>
  );
};

export default HomePage;