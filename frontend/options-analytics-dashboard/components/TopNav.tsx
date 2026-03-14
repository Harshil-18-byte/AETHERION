import { useTheme } from "next-themes";
import { Moon, Sun, Upload } from "lucide-react";
import React, { useEffect, useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import { LoginModal } from "./modals/LoginModal";
import { RegisterModal } from "./modals/RegisterModal";

interface TopNavProps {
  selectedExpiry: string;
  expiries: string[];
  onExpiryChange: (expiry: string) => void;
  lastUpdated?: string;
  spotPrice?: number;
  onFileUpload?: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

export default function TopNav({ selectedExpiry, expiries, onExpiryChange, lastUpdated, spotPrice, onFileUpload }: TopNavProps) {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const { user, logout } = useAuth();
  const [isLoginOpen, setIsLoginOpen] = useState(false);
  const [isRegisterOpen, setIsRegisterOpen] = useState(false);

  // Avoid hydration mismatch
  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <header className="topnav terminal-header">
      <div className="topnav-left">
        <div className="topnav-brand pulse-border">
          <span className="topnav-title mono text-amber">GAMMALENS</span>
          <span className="topnav-tagline mono">TERM <span className="text-green">READY</span></span>
        </div>

        <div className="topnav-divider" />

        <div className="topnav-asset-info">
          <div className="topnav-asset-item">
            <span className="topnav-asset-label">SYM</span>
            <span className="topnav-asset-value mono text-cyan">NIFTY</span>
          </div>
          {spotPrice != null && (
            <div className="topnav-asset-item">
              <span className="topnav-asset-label">PX_LAST</span>
              <span className="topnav-asset-value mono text-green">
                {spotPrice.toLocaleString(undefined, { maximumFractionDigits: 2, minimumFractionDigits: 2 })}
              </span>
            </div>
          )}
        </div>
      </div>

      <div className="topnav-right">
        {user ? (
          <div className="flex items-center gap-3 mr-4">
            <span className="text-[10px] uppercase tracking-widest text-gray-500 font-bold">User: {user.full_name}</span>
            <button 
              onClick={logout}
              className="px-2 py-1 text-[10px] uppercase tracking-widest bg-red-900/20 text-red-400 border border-red-900/50 rounded hover:bg-red-900/40 transition-colors"
            >
              Logout
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-2 mr-4">
            <button 
              onClick={() => setIsLoginOpen(true)}
              className="px-2 py-1 text-[10px] uppercase tracking-widest text-gray-400 hover:text-white transition-colors"
            >
              Login
            </button>
            <button 
              onClick={() => setIsRegisterOpen(true)}
              className="px-2 py-1 text-[10px] uppercase tracking-widest bg-blue-600/20 text-blue-400 border border-blue-600/50 rounded hover:bg-blue-600/40 transition-colors"
            >
              Register
            </button>
          </div>
        )}

        {mounted && (
          <button
            className="theme-toggle-btn"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            title="Toggle Theme"
          >
            {theme === "dark" ? <Sun size={14} /> : <Moon size={14} />}
          </button>
        )}

        <label className="topnav-label">
          Expiry
          <select
            className="topnav-select"
            value={selectedExpiry}
            onChange={(e) => onExpiryChange(e.target.value)}
          >
            {expiries.map((exp) => (
              <option key={exp} value={exp}>{exp}</option>
            ))}
          </select>
        </label>
        
        {onFileUpload && (
          <label className="filter-refresh-btn" style={{ cursor: "pointer", display: "flex", alignItems: "center", gap: "6px" }}>
            <Upload size={12} />
            Upload CSV
            <input type="file" accept=".csv" style={{ display: "none" }} onChange={onFileUpload} />
          </label>
        )}

        {lastUpdated && (
          <span className="topnav-updated">
            <span className="topnav-status-dot" />
            Updated {lastUpdated}
          </span>
        )}
      </div>

      <LoginModal 
        isOpen={isLoginOpen} 
        onClose={() => setIsLoginOpen(false)} 
        onSwitchToRegister={() => {
          setIsLoginOpen(false);
          setIsRegisterOpen(true);
        }}
      />
      
      <RegisterModal 
        isOpen={isRegisterOpen} 
        onClose={() => setIsRegisterOpen(false)} 
        onSwitchToLogin={() => {
          setIsRegisterOpen(false);
          setIsLoginOpen(true);
        }}
      />
    </header>
  );
}
