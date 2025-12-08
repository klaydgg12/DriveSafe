// AboutPage.tsx
// About page for DriveSafe

import React from "react";
import "../App.css";

const AboutPage = () => {
  return (
    <div className="drivesafe-about-page">
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

      {/* About Content */}
      <section className="about-hero">
        <div className="container">
          <div className="about-nav-link">
            <a href="#about">About the Project</a>
          </div>
          <h1 className="about-title">Academic Excellence in Software Development</h1>
          
          <div className="about-section">
            <p className="about-description">
              DriveSafe is a capstone project developed by Information Technology students of Cebu Institute of Technology University
            </p>
          </div>

          <div className="about-content">
            {/* Two-Column Layout for Objectives and Problem Statement */}
            <div className="about-two-column">
              <div className="about-card">
                <div className="about-card-icon">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="12" cy="12" r="10" fill="#2563eb"/>
                    <path d="M12 6V12L16 14" stroke="white" strokeWidth="2" strokeLinecap="round"/>
                  </svg>
                </div>
                <h2 className="about-card-title">Project Objectives</h2>
                <p className="about-card-description">
                  DriveSafe addresses the critical need for automated backup solutions for students and educators who risk losing access to important academic files stored in school-issued Google accounts.
                </p>
                
                <div className="objectives-list">
                  <div className="objective-item">
                    <span className="objective-checkmark">✓</span>
                    <div className="objective-content">
                      <h3 className="objective-title">Prevent Data Loss</h3>
                      <p className="objective-description">Protect academic files from account deactivation.</p>
                    </div>
                  </div>
                  
                  <div className="objective-item">
                    <span className="objective-checkmark">✓</span>
                    <div className="objective-content">
                      <h3 className="objective-title">Simplify Backups</h3>
                      <p className="objective-description">One-click solution vs manual/multi-step processes.</p>
                    </div>
                  </div>
                  
                  <div className="objective-item">
                    <span className="objective-checkmark">✓</span>
                    <div className="objective-content">
                      <h3 className="objective-title">Ensure Compliance</h3>
                      <p className="objective-description">Full adherence to RA 10173 Data Privacy Act.</p>
                    </div>
                  </div>
                </div>
              </div>
              
              <div className="about-card">
                <div className="about-card-icon">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="12" cy="12" r="10" fill="#2563eb"/>
                    <path d="M12 8V12M12 16H12.01" stroke="white" strokeWidth="2" strokeLinecap="round"/>
                    <circle cx="12" cy="12" r="1" fill="white"/>
                  </svg>
                </div>
                <h2 className="about-card-title">Problem Statement</h2>
                <p className="about-card-description">
                  Students and educators accumulate critical files on Google Drive, but face potential data loss upon graduation or account deactivation. Existing solutions like Google Takeout are manual and infrequently used.
                </p>
                
                <div className="challenge-box challenge-box-blue">
                  <h3 className="challenge-title">The Challenge</h3>
                  <p className="challenge-description">
                    How can we provide a smart, reliable, automated backup solution that prevents data loss while maintaining security and privacy compliance?
                  </p>
                </div>
                
                <div className="challenge-box challenge-box-green">
                  <h3 className="challenge-title">Our SOLUTION</h3>
                  <p className="challenge-description">
                    DriveSafe automates the entire backup process with enterprise-grade security, requiring just one click to protect your valuable academic files.
                  </p>
                </div>
              </div>
            </div>
            
            {/* Development Team Section */}
            <div className="about-card team-card">
              <div className="about-card-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <circle cx="12" cy="12" r="10" fill="#2563eb"/>
                  <path d="M12 8C13.1 8 14 8.9 14 10C14 11.1 13.1 12 12 12C10.9 12 10 11.1 10 10C10 8.9 10.9 8 12 8ZM12 14C14.67 14 18 15.33 18 17V18H6V17C6 15.33 9.33 14 12 14Z" fill="white"/>
                </svg>
              </div>
              <h2 className="about-card-title">Development Team</h2>
              <p className="team-subtitle">Information Technology Students • Class of 2025</p>
              
              <div className="team-members-grid">
                <div className="team-member-card">
                  <div className="member-initial">L</div>
                  <h3 className="member-name">Lyrech James E. Laspiñas</h3>
                  <p className="member-role">Developer</p>
                </div>
                
                <div className="team-member-card">
                  <div className="member-initial">L</div>
                  <h3 className="member-name">Louis Drey F. Castañeto</h3>
                  <p className="member-role">Developer</p>
                </div>
                
                <div className="team-member-card">
                  <div className="member-initial">J</div>
                  <h3 className="member-name">John Earl F. Mandawe</h3>
                  <p className="member-role">Developer</p>
                </div>
                
                <div className="team-member-card">
                  <div className="member-initial">C</div>
                  <h3 className="member-name">Clyde Nixon Jumawan</h3>
                  <p className="member-role">Developer</p>
                </div>
                
                <div className="team-member-card">
                  <div className="member-initial">M</div>
                  <h3 className="member-name">Mark Joenylle B. Cortes</h3>
                  <p className="member-role">Developer</p>
                </div>
              </div>
            </div>
            
            {/* Institutional Information Block */}
            <div className="institution-block">
              <div className="institution-icon">
                <svg width="48" height="48" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M24 4L6 10V22C6 30.5 12.5 38.5 24 42C35.5 38.5 42 30.5 42 22V10L24 4Z" fill="white" stroke="white" strokeWidth="2"/>
                </svg>
              </div>
              <h2 className="institution-name">CEBU INSTITUTE OF TECHNOLOGY UNIVERSITY</h2>
              <p className="institution-college">College of Computer Studies</p>
              <p className="institution-motto">
                Committed to excellence in technology education, CIT-U empowers students to create innovative solutions that address real-world problems through comprehensive computer science programs.
              </p>
              
              <div className="project-details-grid">
                <div className="project-detail-item">
                  <h3 className="project-detail-label">Project Release</h3>
                  <p className="project-detail-value">1.0 (2025)</p>
                </div>
                
                <div className="project-detail-item">
                  <h3 className="project-detail-label">Submission Date</h3>
                  <p className="project-detail-value">December 15, 2025</p>
                </div>
                
                <div className="project-detail-item">
                  <h3 className="project-detail-label">Status</h3>
                  <p className="project-detail-value">Capstone Project</p>
                </div>
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
              <p>Simple automated Google Drive backup tool for students and educators.</p>
            </div>
            
            <div className="footer-column">
              <h4>Project</h4>
              <p>Version 1.0</p>
              <p>Capstone Project</p>
              <p>CIT-U College of Computer Studies</p>
            </div>
            
            <div className="footer-column">
              <h4>Developed By</h4>
              <p>Lyrech James E. Laspiñas</p>
              <p>Louis Drey F. Castañeto</p>
              <p>John Earl F. Mandawe</p>
              <p>Clyde Nixon Jumawan</p>
              <p>Mark Joenylle B. Cortes</p>
            </div>
          </div>
          
          <div className="footer-bottom">
            <p>&copy; 2025 DriveSafe. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default AboutPage;