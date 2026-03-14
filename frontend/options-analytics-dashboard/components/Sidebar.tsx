"use client";

const NAV_SECTIONS = [
  { id: "overview", label: "Market Overview", group: "Analytics" },
  { id: "structure", label: "Market Structure", group: "Analytics" },
  { id: "volatility", label: "Volatility Analytics", group: "Analytics" },
  { id: "liquidity", label: "Liquidity Analysis", group: "Analysis" },
  { id: "intelligence", label: "Market Intelligence", group: "Analysis" },
  { id: "narrative", label: "Market Narrative", group: "Insights" },
  { id: "events", label: "Market Events", group: "Insights" },
];

interface SidebarProps {
  activeSection: string;
  onSectionChange: (section: string) => void;
}

export default function Sidebar({
  activeSection,
  onSectionChange,
}: SidebarProps) {
  return (
    <aside className="sidebar">
      <nav className="sidebar-nav">
        {NAV_SECTIONS.map((section, index) => {
          const previousGroup = index > 0 ? NAV_SECTIONS[index - 1].group : "";
          const showGroup = section.group !== previousGroup;

          return (
            <div key={section.id} className={`animate-in stagger-${(index % 4) + 1}`}>
              {showGroup && (
                <span className="sidebar-section-label mono">{section.group}</span>
              )}
              <button
                className={`sidebar-item terminal-btn mono ${activeSection === section.id ? "sidebar-item-active" : ""}`}
                onClick={() => onSectionChange(section.id)}
              >
                {section.label.toUpperCase()} <span className="text-muted">{"<GO>"}</span>
              </button>
            </div>
          );
        })}
      </nav>
      <div className="sidebar-footer">
        <span className="sidebar-footer-text">GammaLens Terminal</span>
        <span className="sidebar-footer-text">v1.0.0</span>
      </div>
    </aside>
  );
}
