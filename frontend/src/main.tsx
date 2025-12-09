import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { GoogleOAuthProvider } from '@react-oauth/google'; // Import this
import './index.css'
import App from './App.tsx'

// REPLACE THIS WITH YOUR ACTUAL CLIENT ID FROM GOOGLE CONSOLE
const CLIENT_ID = "314972685252-4s63r50uod7a5ksq1lsj3cpodqschlen.apps.googleusercontent.com";

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <GoogleOAuthProvider clientId={CLIENT_ID}>
      <App />
    </GoogleOAuthProvider>
  </StrictMode>,
)