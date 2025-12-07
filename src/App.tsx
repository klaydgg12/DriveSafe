import { useState, useEffect } from "react";
import HomePage from "./pages/HomePage";
import FeaturesPage from "./pages/FeaturesPage";
import AboutPage from "./pages/AboutPage";
import LoginPage from "./pages/LoginPage";
import SignUpPage from "./pages/SignUpPage";
import DashboardPage from "./pages/DashboardPage";
import BackupHistoryPage from "./pages/BackupHistoryPage";
import "./App.css";

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
      } else if (hash === "signup") {
        setCurrentPage("signup");
      } else if (hash === "dashboard") {
        setCurrentPage("dashboard");
      } else if (hash === "backup-history") {
        setCurrentPage("backup-history");
      } else {
        setCurrentPage("home");
      }
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
      case "signup":
        return <SignUpPage />;
      case "dashboard":
        return <DashboardPage />;
      case "backup-history":
        return <BackupHistoryPage />;
      default:
        return <HomePage />;
    }
  };

  return (
    <div style={{ width: "100vw", height: "100vh", overflow: "auto" }}>
      {renderPage()}
    </div>
  );
}

export default App;