import React, { useEffect, useRef, useState, useCallback } from 'react';

export default function StrategyAssistant({
  botId,
  disabled,
  onApplyRules,
}) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [pendingRules, setPendingRules] = useState(null);
  const [rulesError, setRulesError] = useState('');
  const [configured, setConfigured] = useState(false);
  const [activeProvider, setActiveProvider] = useState('');
  const [configuredProviders, setConfiguredProviders] = useState([]);
  const [collapsed, setCollapsed] = useState(false);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const bottomRef = useRef(null);

  const _FLAGS = { groq: 'strategy_llm_groq_key_configured', gemini: 'strategy_llm_gemini_key_configured', mistral: 'strategy_llm_mistral_key_configured', openai: 'strategy_llm_openai_key_configured' };

  const refreshKeyStatus = useCallback(() => {
    fetch('/api/settings')
      .then((r) => r.json())
      .then((d) => {
        setConfigured(d.strategy_llm_key_configured === 'true');
        const ap = (d.strategy_llm_provider || 'groq').toLowerCase();
        setActiveProvider(ap);
        const configured = Object.entries(_FLAGS)
          .filter(([, flag]) => d[flag] === 'true')
          .map(([p]) => p);
        setConfiguredProviders(configured);
      })
      .catch(() => { setConfigured(false); setActiveProvider(''); setConfiguredProviders([]); });
  }, []);

  const loadHistory = useCallback(async (id) => {
    if (!id) return;
    try {
      const res = await fetch(`/api/assistant/history/${id}`);
      if (!res.ok) return;
      const data = await res.json();
      setMessages(data);
    } catch {
      // ignore
    }
    setHistoryLoaded(true);
  }, []);

  useEffect(() => {
    setMessages([]);
    setInput('');
    setError('');
    setPendingRules(null);
    setRulesError('');
    setHistoryLoaded(false);
    refreshKeyStatus();
    loadHistory(botId);
  }, [botId, refreshKeyStatus, loadHistory]);

  useEffect(() => {
    const onVis = () => {
      if (document.visibilityState === 'visible') refreshKeyStatus();
    };
    document.addEventListener('visibilitychange', onVis);
    return () => document.removeEventListener('visibilitychange', onVis);
  }, [refreshKeyStatus]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const switchProvider = async (p) => {
    setActiveProvider(p);
    await fetch('/api/settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ settings: { strategy_llm_provider: p } }),
    });
  };

  const clearHistory = async () => {
    if (!botId) return;
    await fetch(`/api/assistant/history/${botId}`, { method: 'DELETE' });
    setMessages([]);
    setPendingRules(null);
    setError('');
    setRulesError('');
  };

  const send = async () => {
    const text = input.trim();
    if (!text || loading || !botId) return;
    setError('');
    setRulesError('');
    setInput('');
    const userMsg = { role: 'user', content: text };
    const nextMsgs = [...messages, userMsg];
    setMessages(nextMsgs);
    setLoading(true);
    try {
      const res = await fetch('/api/assistant/strategy-chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bot_id: botId, messages: nextMsgs }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = data.detail;
        const msg = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map((d) => d.msg).join('; ') : res.statusText;
        throw new Error(msg || 'Request failed');
      }
      const assistantMsg = { role: 'assistant', content: data.reply || '' };
      setMessages((m) => [...m, assistantMsg]);
      // Persist the new pair to DB
      fetch(`/api/assistant/history/${botId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: [userMsg, assistantMsg] }),
      }).catch(() => {});

      if (data.rules_error) {
        setRulesError(data.rules_error);
        setPendingRules(null);
      } else if (data.suggested_rules && data.suggested_rules.length > 0) {
        setPendingRules(data.suggested_rules);
      } else {
        setPendingRules(null);
      }
    } catch (e) {
      setError(e.message || String(e));
      setMessages((m) => m.slice(0, -1));
    } finally {
      setLoading(false);
    }
  };

  if (disabled) {
    return (
      <aside className="hidden lg:flex w-72 shrink-0 border-l border-terminal-border-dim bg-terminal-panel/80 flex-col items-center justify-center p-4 text-center">
        <p className="text-[10px] font-mono text-terminal-amber-dim leading-relaxed">
          STRATEGY ASSISTANT IS DISABLED DURING BULK EDIT. SELECT A SINGLE BOT TO USE CHAT.
        </p>
      </aside>
    );
  }

  if (collapsed) {
    return (
      <aside className="hidden lg:flex shrink-0 border-l border-terminal-border-dim bg-terminal-panel/90 flex-col h-full min-h-0 w-7 items-center pt-3">
        <button
          type="button"
          onClick={() => setCollapsed(false)}
          className="text-terminal-amber-dim hover:text-terminal-amber transition-colors"
          title="Expand Strategy Assistant"
        >
          <span className="text-[9px] font-mono" style={{ writingMode: 'vertical-rl', textOrientation: 'mixed', transform: 'rotate(180deg)', display: 'block', letterSpacing: '0.08em' }}>
            STRATEGY ASSISTANT
          </span>
        </button>
      </aside>
    );
  }

  return (
    <aside className="hidden lg:flex w-80 shrink-0 border-l border-terminal-border-dim bg-terminal-panel/90 flex-col h-full min-h-0">
      <div className="px-3 py-2 border-b border-terminal-border-dim shrink-0">
        <div className="flex items-center gap-1">
          <h3 className="text-[10px] font-mono font-bold text-terminal-amber-bright tracking-wider flex-1">STRATEGY ASSISTANT</h3>
          <button
            type="button"
            className="text-[10px] text-terminal-amber-dim hover:text-terminal-amber font-mono"
            onClick={() => setCollapsed(true)}
            title="Collapse"
          >
            [&gt;]
          </button>
        </div>
        {configuredProviders.length > 0 && (
          <div className="flex items-center gap-1 mt-1">
            {configuredProviders.map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => switchProvider(p)}
                className={`text-[9px] font-mono px-1.5 py-0.5 border transition-colors ${
                  activeProvider === p
                    ? 'border-terminal-amber text-terminal-amber-bright bg-terminal-amber-faint'
                    : 'border-terminal-border-dim text-terminal-amber-dim hover:text-terminal-amber hover:border-terminal-amber/50'
                }`}
              >
                {p.toUpperCase()}
              </button>
            ))}
          </div>
        )}
        <p className="text-[9px] text-terminal-amber-dim mt-1 leading-relaxed">
          Describe changes in plain language. If the model proposes a full rule set, use Apply to replace the editor.
        </p>
        <div className="flex items-center justify-between gap-1 mt-1">
          {!configured && (
            <p className="text-[9px] text-terminal-red-text flex-1">Add an LLM API key under CONFIG, then SAVE ALL CONFIG.</p>
          )}
          <div className="flex items-center gap-2 ml-auto shrink-0">
            {messages.length > 0 && (
              <button type="button" className="text-[9px] text-terminal-amber-dim hover:text-terminal-red-text" onClick={clearHistory}>
                Clear
              </button>
            )}
            <button type="button" className="text-[9px] text-terminal-amber-dim hover:text-terminal-amber" onClick={refreshKeyStatus}>
              Refresh
            </button>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-2 py-2 space-y-2 min-h-0">
        {messages.length === 0 && historyLoaded && (
          <p className="text-[10px] font-mono text-terminal-amber-dim px-1">
            Example: &quot;Add a resting limit guard: only place a limit when PositionSize and RestingLimitCount are both zero.&quot;
          </p>
        )}
        {messages.map((msg, i) => (
          <div
            key={`${i}-${msg.role}`}
            className={`text-[10px] font-mono rounded px-2 py-1.5 whitespace-pre-wrap break-words ${
              msg.role === 'user'
                ? 'bg-terminal-amber-faint/40 text-terminal-amber ml-2'
                : 'bg-terminal-bg text-terminal-amber-dim mr-2 border border-terminal-border-dim/50'
            }`}
          >
            {msg.content}
          </div>
        ))}
        {loading && <div className="text-[10px] font-mono text-terminal-amber-dim px-2 animate-pulse">Thinking...</div>}
        {error && <div className="text-[10px] font-mono text-terminal-red-text px-2">{error}</div>}
        {rulesError && <div className="text-[10px] font-mono text-terminal-red-text px-2">Rules parse: {rulesError}</div>}
        <div ref={bottomRef} />
      </div>

      {pendingRules && (
        <div className="px-2 py-2 border-t border-terminal-border-dim shrink-0 space-y-1">
          <p className="text-[9px] font-mono text-terminal-green-text">
            {pendingRules.length} rule line(s) proposed. Review the reply above, then apply or dismiss.
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              className="flex-1 btn-primary text-[10px] py-1"
              onClick={() => {
                if (onApplyRules) onApplyRules(pendingRules);
                setPendingRules(null);
                setRulesError('');
              }}
            >
              APPLY TO EDITOR
            </button>
            <button type="button" className="btn-secondary text-[10px] py-1 px-2" onClick={() => setPendingRules(null)}>
              DISMISS
            </button>
          </div>
        </div>
      )}

      <div className="p-2 border-t border-terminal-border-dim shrink-0 flex gap-1">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
          placeholder="Instructions..."
          disabled={loading || !configured}
          rows={2}
          className="flex-1 input-field text-[10px] font-mono resize-none min-h-[44px]"
        />
        <button
          type="button"
          onClick={send}
          disabled={loading || !configured || !input.trim()}
          className="btn-primary text-[10px] px-3 self-end"
        >
          SEND
        </button>
      </div>
    </aside>
  );
}
