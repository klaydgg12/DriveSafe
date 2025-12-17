// LoginPage.tsx
// Login page for DriveSafe

import React from "react";
import { useGoogleLogin } from "@react-oauth/google";
import "../App.css";

const LoginPage = () => {
  
  const googleLogin = useGoogleLogin({
    flow: 'auth-code',
    scope: "https://www.googleapis.com/auth/drive.readonly",
    // @ts-ignore
    prompt: 'consent', 
    onSuccess: async (codeResponse) => {
      console.log("Google Code Received:", codeResponse.code);
      
      try {
        const response = await fetch('http://localhost:5000/auth/google', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ code: codeResponse.code }),
        });

        const data = await response.json();

        if (response.ok) {
          console.log("Backend Login Success:", data);
          
          localStorage.setItem('access_token', data.access_token); 
          if (data.user_email) localStorage.setItem('user_email', data.user_email);
          if (data.user_name) localStorage.setItem('user_name', data.user_name);
          if (data.user_picture) localStorage.setItem('user_picture', data.user_picture);
          
          window.location.hash = "dashboard";
        } else {
          console.error("Backend Error Details:", data);
          alert("Login Failed: " + (data.error || JSON.stringify(data)));
        }
      } catch (error) {
        console.error("Network error:", error);
      }
    },
    onError: () => {
      console.log('Login Failed');
    },
  });

  const handleClose = () => {
    window.location.hash = "";
  };

  return (
    <div className="drivesafe-login-page">
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
            {/* "Sign In" is sufficient for both login and signup */}
            <a href="#signin">Sign In</a>
            <button className="btn btn-primary btn-header" onClick={() => googleLogin()}>Get Started</button>
          </nav>
        </div>
      </header>

      <div className="login-overlay">
        <div className="login-modal">
          <button className="login-close-btn" onClick={handleClose}>
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M15 5L5 15M5 5L15 15" stroke="#64748b" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </button>

          <div className="login-header">
            <div className="login-logo">
              <svg width="48" height="48" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect x="6" y="6" width="36" height="36" rx="4" fill="#2563eb"/>
                <rect x="14" y="14" width="20" height="20" rx="2" fill="white"/>
                <rect x="18" y="18" width="12" height="12" rx="1" fill="#2563eb"/>
              </svg>
            </div>
            <h1 className="login-title">Welcome Back</h1>
            <p className="login-subtitle">Sign in to access your backups</p>
          </div>

          <button className="btn-google" onClick={() => googleLogin()}> 
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M19.6 10.2273C19.6 9.51818 19.5364 8.83636 19.4182 8.18182H10V12.05H15.3818C15.15 13.3 14.4455 14.3591 13.3864 15.0682V17.5773H16.6182C18.5091 15.8364 19.6 13.2727 19.6 10.2273Z" fill="#4285F4"/>
              <path d="M10 20C12.7 20 14.9636 19.1045 16.6182 17.5773L13.3864 15.0682C12.4909 15.6682 11.3455 16.0227 10 16.0227C7.39545 16.0227 5.19091 14.2636 4.40455 11.9H1.06364V14.4909C2.70909 17.7591 6.09091 20 10 20Z" fill="#34A853"/>
              <path d="M4.40455 11.9C4.20455 11.3 4.09091 10.6591 4.09091 10C4.09091 9.34091 4.20455 8.7 4.40455 8.1V5.50909H1.06364C0.386364 6.85909 0 8.38636 0 10C0 11.6136 0.386364 13.1409 1.06364 14.4909L4.40455 11.9Z" fill="#FBBC05"/>
              <path d="M10 3.97727C11.4682 3.97727 12.7864 4.44091 13.8227 5.29091L16.6909 2.42273C14.9591 0.790909 12.6955 0 10 0C6.09091 0 2.70909 2.24091 1.06364 5.50909L4.40455 8.1C5.19091 5.73636 7.39545 3.97727 10 3.97727Z" fill="#EA4335"/>
            </svg>
            <span>Sign in with Google</span>
          </button>

          <div className="login-privacy">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M8 1.33333L2.66667 4V7.33333C2.66667 10.3 4.96667 13.0333 8 14.6667C11.0333 13.0333 13.3333 10.3 13.3333 7.33333V4L8 1.33333Z" fill="#10b981" stroke="#10b981" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            <p>By continuing, you agree to our <a href="#">Terms of Service</a> and <a href="#">Privacy Policy</a>. We're compliant with RA 10173 Data Privacy Act.</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;