import React from 'react';

export default function TitleBar() {
  const { minimize, maximize, close } = window.saraGUI?.windowControls || {};

  return (
    <div className="flex items-center justify-between h-10 px-4 bg-bg-card border-b border-white/5 select-none" style={{ WebkitAppRegion: 'drag' } as any}>
      <div className="flex items-center gap-2">
        <div className="w-5 h-5 rounded-full bg-gradient-to-br from-primary to-secondary" />
        <span className="text-sm font-semibold text-text-primary">Sara Agent</span>
      </div>
      <div className="flex items-center gap-1" style={{ WebkitAppRegion: 'no-drag' } as any}>
        <button onClick={minimize} className="w-8 h-8 flex items-center justify-center rounded-md hover:bg-bg-hover text-text-muted hover:text-text-primary transition-colors">─</button>
        <button onClick={maximize} className="w-8 h-8 flex items-center justify-center rounded-md hover:bg-bg-hover text-text-muted hover:text-text-primary transition-colors">□</button>
        <button onClick={close} className="w-8 h-8 flex items-center justify-center rounded-md hover:bg-error/20 text-text-muted hover:text-error transition-colors">✕</button>
      </div>
    </div>
  );
}