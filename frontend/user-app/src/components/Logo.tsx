import React from "react";

interface LogoProps {
  size?: number;
  className?: string;
  animated?: boolean;
}

export const Logo: React.FC<LogoProps> = ({ size = 36, className = "", animated = true }) => {
  return (
    <div
      className={`app-logo-wrap ${animated ? "animating" : ""} ${className}`}
      style={{ width: size, height: size }}
      aria-label="College Knowledge Logo"
    >
      <svg
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="app-logo-svg"
      >
        <defs>
          <linearGradient id="logoPrimaryGrad" x1="15" y1="15" x2="85" y2="85" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#2563eb" />
            <stop offset="100%" stopColor="#4f46e5" />
          </linearGradient>
          <linearGradient id="logoSecondaryGrad" x1="85" y1="15" x2="15" y2="85" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#3b82f6" />
            <stop offset="100%" stopColor="#6366f1" />
          </linearGradient>
          <radialGradient id="logoSoftAura" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.18" />
            <stop offset="100%" stopColor="#3b82f6" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* Soft Ambient Aura */}
        <circle cx="50" cy="50" r="42" className="logo-aura" fill="url(#logoSoftAura)" />

        {/* Outer Academic Diamond Crest */}
        <path
          className="logo-path path-crest"
          d="M50 13 L83 32 L83 68 L50 87 L17 68 L17 32 Z"
          stroke="url(#logoPrimaryGrad)"
          strokeWidth="3.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Left Book Wing */}
        <path
          className="logo-path path-left"
          d="M50 36 C37 36 27 42 27 55 C27 67 37 70 50 75"
          stroke="url(#logoSecondaryGrad)"
          strokeWidth="3.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Right Book Wing */}
        <path
          className="logo-path path-right"
          d="M50 36 C63 36 73 42 73 55 C73 67 63 70 50 75"
          stroke="url(#logoPrimaryGrad)"
          strokeWidth="3.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Central Beacon Spine */}
        <path
          className="logo-path path-center"
          d="M50 25 L50 75"
          stroke="url(#logoPrimaryGrad)"
          strokeWidth="3.2"
          strokeLinecap="round"
        />

        {/* Floating Intellectual Spark */}
        <circle
          cx="50"
          cy="46"
          r="4"
          className="logo-spark"
          fill="url(#logoPrimaryGrad)"
        />
      </svg>
    </div>
  );
};
