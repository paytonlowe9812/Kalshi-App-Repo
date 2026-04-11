import React from 'react';
import Toggle from '../shared/Toggle';
import useAppStore from '../../store/useAppStore';

const PROVIDERS = [
  { value: 'groq', label: 'Groq', keyField: 'strategy_llm_groq_key', configuredFlag: 'strategy_llm_groq_key_configured', modelField: 'strategy_llm_groq_model', placeholder: 'gsk_...', defaultModel: 'llama-3.3-70b-versatile', modelHint: 'e.g. llama-3.3-70b-versatile, llama3-8b-8192' },
  { value: 'gemini', label: 'Gemini', keyField: 'strategy_llm_gemini_key', configuredFlag: 'strategy_llm_gemini_key_configured', modelField: 'strategy_llm_gemini_model', placeholder: 'AIza...', defaultModel: 'gemini-2.0-flash', modelHint: 'e.g. gemini-2.0-flash, gemini-1.5-flash' },
  { value: 'mistral', label: 'Mistral', keyField: 'strategy_llm_mistral_key', configuredFlag: 'strategy_llm_mistral_key_configured', modelField: 'strategy_llm_mistral_model', placeholder: '...', defaultModel: 'mistral-small-latest', modelHint: 'e.g. mistral-small-latest, open-mistral-7b' },
  { value: 'openai', label: 'OpenAI', keyField: 'strategy_llm_api_key', configuredFlag: 'strategy_llm_openai_key_configured', modelField: 'strategy_llm_model', placeholder: 'sk-...', defaultModel: 'gpt-4o-mini', modelHint: 'e.g. gpt-4o-mini, gpt-4o' },
];

export default function AppSettings({ settings, onUpdate }) {
  const { theme, setTheme } = useAppStore();
  const s = settings || {};
  const toggleTheme = () => { const next = theme === 'dark' ? 'light' : 'dark'; setTheme(next); onUpdate('theme', next); };
  const exportBots = async () => { const res = await fetch('/api/bots'); const bots = await res.json(); const blob = new Blob([JSON.stringify(bots, null, 2)], { type: 'application/json' }); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = 'bots_backup.json'; a.click(); URL.revokeObjectURL(url); };
  const importBots = (e) => { const file = e.target.files?.[0]; if (!file) return; const reader = new FileReader(); reader.onload = async (ev) => { try { const bots = JSON.parse(ev.target.result); for (const bot of bots) { await fetch('/api/bots', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: bot.name, market_ticker: bot.market_ticker }) }); } } catch {} }; reader.readAsText(file); };

  const activeProvider = s.strategy_llm_provider || 'groq';

  return (
    <div className="card space-y-4 font-mono">
      <h3 className="panel-header">APP CONFIG</h3>
      <Toggle checked={theme === 'dark'} onChange={toggleTheme} label={`THEME: ${theme === 'dark' ? 'DARK' : 'LIGHT'}`} />
      <div className="flex items-center gap-3"><span className="text-xs text-terminal-amber-dim font-mono">LOOP INTERVAL:</span><select value={s.loop_interval_ms || '500'} onChange={(e) => onUpdate('loop_interval_ms', e.target.value)} className="input-field text-xs"><option value="500">500ms</option><option value="1000">1s</option><option value="5000">5s</option><option value="10000">10s</option><option value="30000">30s</option><option value="60000">60s</option></select></div>
      <div className="flex items-center gap-3"><span className="text-xs text-terminal-amber-dim font-mono">MAX BOTS:</span><input type="number" value={s.max_simultaneous_bots || 10} onChange={(e) => onUpdate('max_simultaneous_bots', e.target.value)} className="input-field w-20 text-xs" min={1} /></div>
      <div className="flex gap-2 pt-2 border-t border-terminal-border-dim">
        <button type="button" onClick={exportBots} className="btn-secondary text-xs">EXPORT BOTS</button>
        <label className="btn-secondary text-xs cursor-pointer">IMPORT BOTS<input type="file" accept=".json" onChange={importBots} className="hidden" /></label>
      </div>

      <div className="space-y-4 pt-4 border-t border-terminal-border-dim">
        <h3 className="panel-header">STRATEGY ASSISTANT (LLM)</h3>
        <p className="text-[10px] text-terminal-amber-dim leading-relaxed max-w-xl">
          Powers the chat panel on the rule editor. Keys stay on the server and are never returned to the browser after save. Leave a key blank when saving to keep the existing value.
        </p>

        <div className="space-y-1.5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-[10px] text-terminal-amber-dim font-mono">EXTRA SYSTEM PROMPT (APPENDED)</span>
            <button
              type="button"
              className="text-[9px] font-mono border border-terminal-border-dim px-1.5 py-0.5 text-terminal-amber-dim hover:text-terminal-amber hover:border-terminal-amber/50"
              onClick={() => onUpdate('strategy_llm_system_prompt', '')}
            >
              CLEAR EXTRA
            </button>
          </div>
          <p className="text-[9px] text-terminal-amber-muted leading-relaxed max-w-xl">
            Appended after the built-in strategy assistant instructions (JSON schema, safety rules, tips). Does not remove or replace them. Then the app appends the active bot summary, current rules JSON, and ```strategy_rules``` rules. Save all config when done.
          </p>
          <textarea
            value={s.strategy_llm_system_prompt || ''}
            onChange={(e) => onUpdate('strategy_llm_system_prompt', e.target.value)}
            rows={14}
            spellCheck={false}
            className="input-field text-[11px] font-mono w-full max-w-3xl min-h-[200px] resize-y"
            placeholder="Optional. Added after the default system prompt, before bot context and rules."
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-terminal-amber-dim font-mono">ACTIVE PROVIDER</span>
          <select
            value={activeProvider}
            onChange={(e) => onUpdate('strategy_llm_provider', e.target.value)}
            className="input-field text-xs"
          >
            {PROVIDERS.map((p) => (
              <option key={p.value} value={p.value}>{p.label}</option>
            ))}
          </select>
          <span className="text-[10px] text-terminal-amber-dim">Falls back to other configured providers on rate limits.</span>
        </div>

        {PROVIDERS.map((p) => (
          <div key={p.value} className={`space-y-2 p-2 border rounded-sm ${activeProvider === p.value ? 'border-terminal-amber/40 bg-terminal-amber-faint/20' : 'border-terminal-border-dim'}`}>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono font-bold text-terminal-amber-bright">{p.label}</span>
              {s[p.configuredFlag] === 'true' && (
                <span className="text-[9px] text-terminal-green-text font-mono">[KEY SAVED]</span>
              )}
              {activeProvider === p.value && (
                <span className="text-[9px] text-terminal-amber font-mono ml-auto">ACTIVE</span>
              )}
            </div>
            <div className="flex flex-col gap-0.5">
              <span className="text-[10px] text-terminal-amber-dim font-mono">API KEY</span>
              <input
                type="password"
                value={s[p.keyField] || ''}
                onChange={(e) => onUpdate(p.keyField, e.target.value)}
                className="input-field text-xs max-w-md"
                placeholder={s[p.configuredFlag] === 'true' ? 'Leave blank to keep saved key' : p.placeholder}
                autoComplete="off"
              />
            </div>
            <div className="flex flex-col gap-0.5">
              <span className="text-[10px] text-terminal-amber-dim font-mono">MODEL (optional, default: {p.defaultModel})</span>
              <input
                type="text"
                value={s[p.modelField] || ''}
                onChange={(e) => onUpdate(p.modelField, e.target.value)}
                className="input-field text-xs max-w-md"
                placeholder={p.modelHint}
                autoComplete="off"
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
