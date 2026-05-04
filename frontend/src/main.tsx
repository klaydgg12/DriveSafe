import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { GoogleOAuthProvider } from '@react-oauth/google'; // Import this
import './index.css'
import App from './App.tsx'

// REPLACE THIS WITH YOUR ACTUAL CLIENT ID FROM GOOGLE CONSOLE
const CLIENT_ID = "314972685252-t6v2r7ok3d41n91jp9vpboo83bg9cgk1.apps.googleusercontent.com";

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <GoogleOAuthProvider clientId={CLIENT_ID}>
      <App />
    </GoogleOAuthProvider>
  </StrictMode>,
)