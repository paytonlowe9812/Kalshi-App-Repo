import React from 'react';
import useAppStore from '../../store/useAppStore';
import useIndexStore from '../../store/useIndexStore';
import Dropdown from '../shared/Dropdown';

export default function IndexDropdown({ onCreateNew, onEditIndex }) {
  const { activeIndexId, setActiveIndexId } = useAppStore();
  const { indexes } = useIndexStore();

  const activeIndex = indexes.find((i) => i.id === activeIndexId);

  return (
    <Dropdown
      trigger={
        <button
          type="button"
          className="flex items-center gap-1 max-w-[120px] md:max-w-[150px] px-1.5 py-0.5 text-[9px] md:text-[10px] font-mono font-medium text-terminal-amber hover:text-terminal-amber-bright transition-colors border border-terminal-border-dim hover:border-terminal-border"
        >
          <span className="truncate">{activeIndex ? activeIndex.name : '[ SELECT INDEX ]'}</span>
          <span className="text-terminal-amber-dim shrink-0">v</span>
        </button>
      }
    >
      {indexes.map((idx) => (
        <button
          key={idx.id}
          onClick={() => setActiveIndexId(idx.id)}
          className={`block w-full text-left px-4 py-2 text-xs font-mono hover:bg-terminal-amber-faint active:bg-terminal-amber-faint transition-colors ${
            idx.id === activeIndexId ? 'text-terminal-amber-bright text-glow-sm' : 'text-terminal-amber'
          }`}
        >
          {idx.name}
        </button>
      ))}
      <div className="border-t border-terminal-border-dim mt-1 pt-1">
        <button
          type="button"
          onClick={() => onEditIndex?.()}
          disabled={!activeIndexId}
          className="block w-full text-left px-4 py-2 text-xs font-mono hover:bg-terminal-amber-faint disabled:opacity-40 disabled:cursor-not-allowed text-terminal-amber"
        >
          EDIT INDEX
        </button>
        <button
          type="button"
          onClick={onCreateNew}
          className="block w-full text-left px-4 py-2 text-xs font-mono text-terminal-amber hover:bg-terminal-amber-faint"
        >
          + NEW INDEX
        </button>
      </div>
    </Dropdown>
  );
}
