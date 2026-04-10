import React from 'react';
import useAppStore from '../../store/useAppStore';

const TABS = [
  { id: 'bots', label: 'BOTS' },
  { id: 'editor', label: 'EDITOR' },
  { id: 'simulator', label: 'SIM' },
  { id: 'markets', label: 'MARKETS' },
  { id: 'portfolio', label: 'P&L' },
  { id: 'log', label: 'LOG' },
  { id: 'vars', label: 'VARS' },
  { id: 'settings', label: 'CONFIG' },
];

export default function TopNav() {
  const { activeTab, setActiveTab } = useAppStore();

  return (
    <nav className="bg-terminal-surface border-b border-terminal-border-dim">
      <div className="hidden md:flex items-center h-9 gap-0 overflow-x-auto px-1">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-2.5 py-1.5 text-[11px] font-mono font-medium transition-all whitespace-nowrap tracking-wide border-b-2 ${
              activeTab === tab.id
                ? 'text-terminal-amber-bright text-glow border-terminal-amber'
                : 'text-terminal-amber-dim hover:text-terminal-amber border-transparent hover:border-terminal-border-dim'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
    </nav>
  );
}
