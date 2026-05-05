import React, { createContext, useContext, useEffect } from 'react';

interface ThemeContextType {
  darkMode: boolean;
  toggleDarkMode: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

// Force light mode by default and disable toggle
export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const darkMode = false;
  const toggleDarkMode = () => {};

  useEffect(() => {
    // Explicitly remove dark class and clear storage to force light mode
    const root = window.document.documentElement;
    root.classList.remove('dark');
    localStorage.removeItem('theme');
  }, []);

  return (
    <ThemeContext.Provider value={{ darkMode, toggleDarkMode }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};
