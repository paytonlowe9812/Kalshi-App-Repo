import React, { useEffect, useRef } from 'react';

export default function Modal({ open, onClose, title, children, width = 'max-w-lg' }) {
  const backdropRef = useRef(null);

  useEffect(() => {
    const handleEsc = (e) => {
      if (e.key === 'Escape') onClose();
    };
    if (open) {
      document.addEventListener('keydown', handleEsc);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.removeEventListener('keydown', handleEsc);
      document.body.style.overflow = '';
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      ref={backdropRef}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80"
      onClick={(e) => {
        if (e.target === backdropRef.current) onClose();
      }}
    >
      <div className={`bg-terminal-surface border border-terminal-border shadow-glow ${width} w-full md:mx-4 max-h-[90vh] md:max-h-[85vh] flex flex-col`}>
        <div className="flex items-center justify-between px-4 md:px-5 py-3 md:py-4 border-b border-terminal-border-dim flex-shrink-0">
          <h2 className="text-sm font-mono font-medium text-terminal-amber-bright tracking-wider text-glow-sm">{title}</h2>
          <button
            onClick={onClose}
            className="text-terminal-amber-dim hover:text-terminal-amber active:text-terminal-amber-bright text-sm leading-none w-8 h-8 flex items-center justify-center"
          >
            [X]
          </button>
        </div>
        <div className="p-4 md:p-5 overflow-y-auto flex-1">{children}</div>
      </div>
    </div>
  );
}
