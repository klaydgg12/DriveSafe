import { useState, useEffect } from "react";
import { GoogleOAuthProvider } from "@react-oauth/google"; 
import HomePage from "./pages/HomePage";
import FeaturesPage from "./pages/FeaturesPage";
import AboutPage from "./pages/AboutPage";
import LoginPage from "./pages/LoginPage";
// REMOVED: import SignUpPage from "./pages/SignUpPage"; <--- No longer needed
import DashboardPage from "./pages/DashboardPage";
import BackupHistoryPage from "./pages/BackupHistoryPage";
import "./App.css";

// Use environment variable or fallback to string (Best Practice)
const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || "";

function App() {
  const [currentPage, setCurrentPage] = useState("home");

  // Handle hash-based navigation
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.substring(1); // Remove #
      if (hash === "features") {
        setCurrentPage("features");
      } else if (hash === "about") {
        setCurrentPage("about");
      } else if (hash === "signin") {
        setCurrentPage("signin");
      } else if (hash === "dashboard") {
        setCurrentPage("dashboard");
      } else if (hash === "backup-history") {
        setCurrentPage("backup-history");
      } else {
        setCurrentPage("home");
      }
      // REMOVED: Check for "signup" hash
    };

    // Set initial page based on hash
    handleHashChange();

    // Listen for hash changes
    window.addEventListener("hashchange", handleHashChange);

    return () => {
      window.removeEventListener("hashchange", handleHashChange);
    };
  }, []);

  const renderPage = () => {
    switch (currentPage) {
      case "features":
        return <FeaturesPage />;
      case "about":
        return <AboutPage />;
      case "signin":
        return <LoginPage />;
      // REMOVED: case "signup": return <SignUpPage />;
      case "dashboard":
        return <DashboardPage />;
      case "backup-history":
        return <BackupHistoryPage />;
      default:
        return <HomePage />;
    }
  };

  return (
    <GoogleOAuthProvider clientId={CLIENT_ID}>
      <div style={{ width: "100vw", height: "100vh", overflow: "auto" }}>
        {renderPage()}
      </div>
    </GoogleOAuthProvider>
  );
}

export default App;