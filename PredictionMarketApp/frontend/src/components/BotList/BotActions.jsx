import React, { useState, useRef, useEffect } from 'react';

export default function BotActions({ bot, onEdit, onStart, onStop, onCopy, onDelete, groups = [], onMoveToGroup }) {
  const [open, setOpen] = useState(false);
  const [showGroupPicker, setShowGroupPicker] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const handle = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', handle);
    document.addEventListener('touchstart', handle);
    return () => {
      document.removeEventListener('mousedown', handle);
      document.removeEventListener('touchstart', handle);
    };
  }, []);

  useEffect(() => {
    if (!open) setShowGroupPicker(false);
  }, [open]);

  const handleMove = (e, groupId) => {
    e.stopPropagation();
    onMoveToGroup?.(groupId);
    setOpen(false);
  };

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setOpen(!open);
        }}
        className="text-terminal-amber-dim active:text-terminal-amber hover:text-terminal-amber w-7 h-7 flex items-center justify-center font-mono text-[11px]"
        aria-haspopup="menu"
        aria-expanded={open}
      >
        [:]
      </button>
      {open && (
        <div
          className={`absolute right-0 z-30 mt-1 bg-terminal-surface border border-terminal-border shadow-glow py-1 ${
            showGroupPicker ? 'min-w-[220px] max-w-[min(100vw-2rem,280px)]' : 'min-w-[160px]'
          } max-h-[min(70vh,24rem)] flex flex-col`}
          onClick={(e) => e.stopPropagation()}
          onMouseDown={(e) => e.stopPropagation()}
        >
          <div className="overflow-y-auto flex-1">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onEdit();
                setOpen(false);
              }}
              className="block w-full text-left px-3 py-2 md:py-1 text-[11px] font-mono text-terminal-amber active:bg-terminal-amber-faint hover:bg-terminal-amber-faint"
            >
              EDIT
            </button>
            {bot.status === 'running' ? (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onStop();
                  setOpen(false);
                }}
                className="block w-full text-left px-3 py-2 md:py-1 text-[11px] font-mono text-terminal-amber active:bg-terminal-amber-faint hover:bg-terminal-amber-faint"
              >
                STOP
              </button>
            ) : (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onStart();
                  setOpen(false);
                }}
                className="block w-full text-left px-3 py-2 md:py-1 text-[11px] font-mono text-terminal-green-text active:bg-terminal-amber-faint hover:bg-terminal-amber-faint"
              >
                START
              </button>
            )}
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onCopy();
                setOpen(false);
              }}
              className="block w-full text-left px-3 py-2 md:py-1 text-[11px] font-mono text-terminal-amber active:bg-terminal-amber-faint hover:bg-terminal-amber-faint"
            >
              COPY
            </button>

            <div className="border-t border-terminal-border-dim/50 my-1" />

            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setShowGroupPicker((v) => !v);
              }}
              className="block w-full text-left px-3 py-2 md:py-1 text-[11px] font-mono text-terminal-amber-bright active:bg-terminal-amber-faint hover:bg-terminal-amber-faint flex items-center justify-between gap-2"
            >
              <span>ADD TO GROUP</span>
              <span className="text-terminal-amber-dim">{showGroupPicker ? '^' : 'v'}</span>
            </button>

            {showGroupPicker && (
              <div className="border-t border-terminal-border-dim/40 bg-terminal-panel/50 px-2 py-1.5 max-h-40 overflow-y-auto">
                <div className="text-[10px] font-mono text-terminal-amber-dim uppercase tracking-wider px-2 py-1">
                  Available groups
                </div>
                {bot.group_id != null && (
                  <button
                    type="button"
                    onClick={(e) => handleMove(e, null)}
                    className="block w-full text-left px-3 py-2 md:py-1.5 text-xs font-mono text-terminal-amber active:bg-terminal-amber-faint hover:bg-terminal-amber-faint rounded-sm"
                  >
                    Ungrouped (root)
                  </button>
                )}
                {groups.length === 0 && (
                  <p className="text-[10px] font-mono text-terminal-amber-dim px-2 py-2">
                    No groups yet. Use NEW GROUP in the toolbar.
                  </p>
                )}
                {groups.map((g) => {
                  const current = bot.group_id === g.id;
                  return (
                    <button
                      key={g.id}
                      type="button"
                      disabled={current}
                      onClick={(e) => handleMove(e, g.id)}
                      className={`block w-full text-left px-3 py-2 md:py-1.5 text-xs font-mono rounded-sm truncate disabled:cursor-default ${
                        current
                          ? 'text-terminal-green-text/90 opacity-80'
                          : 'text-terminal-amber active:bg-terminal-amber-faint hover:bg-terminal-amber-faint'
                      }`}
                    >
                      {g.name}
                      {current ? ' (current)' : ''}
                    </button>
                  );
                })}
              </div>
            )}

            <div className="border-t border-terminal-border-dim/50 my-1" />

            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onDelete();
                setOpen(false);
              }}
              className="block w-full text-left px-3 py-2 md:py-1 text-[11px] font-mono text-terminal-red-text active:bg-terminal-amber-faint hover:bg-terminal-amber-faint"
            >
              DELETE
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
