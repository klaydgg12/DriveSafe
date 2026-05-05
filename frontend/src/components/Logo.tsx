import React from 'react';

interface LogoProps {
  size?: number;
  className?: string;
}

const Logo: React.FC<LogoProps> = ({ size = 24, className = "" }) => {
  return (
    <div 
      className={`relative flex-shrink-0 flex items-center justify-center ${className}`} 
      style={{ width: size, height: size }}
    >
      {/* Dynamic Shining/Glow Background Background */}
      <div className="absolute inset-0 bg-gradient-to-br from-indigo-500 via-purple-500 to-indigo-600 rounded-full blur-md opacity-40 animate-pulse"></div>
      
      {/* The Logo Image */}
      <div className="relative z-10 w-full h-full rounded-full overflow-hidden border border-white/20 shadow-lg">
        <img 
          src="/logo.jpg" 
          alt="DriveSafe Logo" 
          className="w-full h-full object-contain"
        />
      </div>

      {/* Decorative Shine Overlay */}
      <div className="absolute inset-0 bg-gradient-to-tr from-transparent via-white/30 to-transparent rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none"></div>
    </div>
  );
};

export default Logo;
