import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { GoogleOAuthProvider } from '@react-oauth/google'; 
import axios from 'axios';
import './index.css'
import App from './App.tsx'

// Configure Axios for Split Deployment (Vercel + Hostinger)
const API_BASE_URL = import.meta.env.VITE_API_URL || ""; 
axios.defaults.baseURL = API_BASE_URL;
axios.defaults.withCredentials = true;

const CLIENT_ID = "314972685252-t6v2r7ok3d41n91jp9vpboo83bg9cgk1.apps.googleusercontent.com";

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <GoogleOAuthProvider clientId={CLIENT_ID}>
      <App />
    </GoogleOAuthProvider>
  </StrictMode>,
)