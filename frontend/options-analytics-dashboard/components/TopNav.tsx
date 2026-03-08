import { useTheme } from "next-themes";
import { Moon, Sun, Upload } from "lucide-react";
import { useEffect, useState } from "react";

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

  // Avoid hydration mismatch
  useEffect(() => setMounted(true), []);

  return (
    <header className="topnav">
      <div className="topnav-left">
        <div className="topnav-brand">
          <span className="topnav-title">GammaLens</span>
          <span className="topnav-tagline">Options Market Intelligence</span>
        </div>

        <div className="topnav-divider" />

        <div className="topnav-asset-info">
          <div className="topnav-asset-item">
            <span className="topnav-asset-label">Underlying</span>
            <span className="topnav-asset-value">NIFTY</span>
          </div>
          {spotPrice != null && (
            <div className="topnav-asset-item">
              <span className="topnav-asset-label">Price</span>
              <span className="topnav-asset-value">
                {spotPrice.toLocaleString(undefined, { maximumFractionDigits: 2 })}
              </span>
            </div>
          )}
        </div>
      </div>

      <div className="topnav-right">
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
    </header>
  );
}
