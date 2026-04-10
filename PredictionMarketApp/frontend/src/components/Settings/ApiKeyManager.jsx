import React, { useEffect, useState } from 'react';
import Modal from '../shared/Modal';
import StatusDot from '../shared/StatusDot';

export default function ApiKeyManager({ firstLaunch }) {
  const [keys, setKeys] = useState([]);
  const [showAdd, setShowAdd] = useState(false);
  const [newKey, setNewKey] = useState({ name: '', key_id: '', key_secret: '', is_demo: false });
  const [testResults, setTestResults] = useState({});
  const [saveError, setSaveError] = useState('');

  const fetchKeys = async () => {
    const res = await fetch('/api/keys');
    if (!res.ok) {
      setKeys([]);
      return;
    }
    setKeys(await res.json());
  };

  useEffect(() => { fetchKeys(); }, []);

  const addKey = async () => {
    setSaveError('');
    const res = await fetch('/api/keys', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newKey),
    });
    if (!res.ok) {
      let msg = `Save failed (${res.status})`;
      try {
        const err = await res.json();
        if (Array.isArray(err.detail)) {
          msg = err.detail.map((d) => d.msg || JSON.stringify(d)).join('; ');
        } else if (typeof err.detail === 'string') {
          msg = err.detail;
        }
      } catch {
        /* ignore */
      }
      setSaveError(msg);
      return;
    }
    setShowAdd(false);
    setNewKey({ name: '', key_id: '', key_secret: '', is_demo: false });
    fetchKeys();
  };

  const testKey = async (id) => {
    const res = await fetch(`/api/keys/${id}/test`, { method: 'POST' });
    const data = await res.json();
    setTestResults((prev) => ({ ...prev, [id]: data }));
  };

  const activateKey = async (id) => {
    await fetch(`/api/keys/${id}/activate`, { method: 'POST' });
    fetchKeys();
  };

  const deleteKey = async (id) => {
    await fetch(`/api/keys/${id}`, { method: 'DELETE' });
    fetchKeys();
  };

  return (
    <div className="card font-mono">
      <h3 className="panel-header mb-3">API KEY MANAGEMENT</h3>

      {firstLaunch && (
        <div className="bg-terminal-amber-faint border border-terminal-amber/30 p-3 mb-4 text-sm text-terminal-amber-bright">
          WELCOME -- PLEASE ADD YOUR KALSHI API KEY TO GET STARTED.
        </div>
      )}

      {/* Desktop table */}
      <table className="hidden md:table w-full text-sm">
        <thead>
          <tr className="text-[10px] text-terminal-amber-dim uppercase tracking-wider">
            <th className="text-left py-2">NAME</th>
            <th className="text-left py-2">ENVIRONMENT</th>
            <th className="text-left py-2">LAST USED</th>
            <th className="text-left py-2">ACTIVE</th>
            <th className="text-right py-2">ACTIONS</th>
          </tr>
        </thead>
        <tbody>
          {keys.map((k) => (
            <tr key={k.id} className="border-t border-terminal-border-dim/50">
              <td className="py-2 text-terminal-amber">{k.name}</td>
              <td className="py-2">
                <span className={`badge ${k.is_demo ? 'bg-terminal-amber-faint text-terminal-amber' : 'bg-terminal-green/20 text-terminal-green-text'}`}>
                  {k.is_demo ? 'DEMO' : 'LIVE'}
                </span>
              </td>
              <td className="py-2 text-terminal-amber-dim text-xs">
                {k.last_used ? new Date(k.last_used).toLocaleDateString() : 'NEVER'}
              </td>
              <td className="py-2">
                {k.is_active ? <StatusDot status="running" /> : <StatusDot status="stopped" />}
              </td>
              <td className="py-2 text-right">
                <div className="flex gap-1 justify-end">
                  <button type="button" onClick={() => activateKey(k.id)} className="text-xs text-terminal-amber-bright hover:text-terminal-amber px-1">
                    {k.is_active ? 'ACTIVE' : 'SET ACTIVE'}
                  </button>
                  <button type="button" onClick={() => testKey(k.id)} className="text-xs text-terminal-green-text hover:text-terminal-green-bright px-1">TEST</button>
                  <button type="button" onClick={() => deleteKey(k.id)} className="text-xs text-terminal-red-text hover:text-terminal-red-bright px-1">DELETE</button>
                </div>
                {testResults[k.id] && (
                  <div className={`text-[10px] mt-0.5 ${testResults[k.id].valid ? 'text-terminal-green-text' : 'text-terminal-red-text'}`}>
                    {testResults[k.id].valid ? 'CONNECTION OK' : testResults[k.id].error || 'FAILED'}
                  </div>
                )}
              </td>
            </tr>
          ))}
          {keys.length === 0 && (
            <tr><td colSpan={5} className="py-4 text-center text-terminal-amber-dim text-xs">NO API KEYS SAVED</td></tr>
          )}
        </tbody>
      </table>

      {/* Mobile list */}
      <div className="md:hidden space-y-2">
        {keys.map((k) => (
          <div key={k.id} className="bg-terminal-panel border border-terminal-border-dim/50 p-3 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {k.is_active ? <StatusDot status="running" /> : <StatusDot status="stopped" />}
                <span className="text-sm font-medium text-terminal-amber">{k.name}</span>
              </div>
              <span className={`badge text-[10px] ${k.is_demo ? 'bg-terminal-amber-faint text-terminal-amber' : 'bg-terminal-green/20 text-terminal-green-text'}`}>
                {k.is_demo ? 'DEMO' : 'LIVE'}
              </span>
            </div>
            <div className="text-[10px] text-terminal-amber-dim">
              LAST USED: {k.last_used ? new Date(k.last_used).toLocaleDateString() : 'NEVER'}
            </div>
            <div className="flex gap-2">
              <button type="button" onClick={() => activateKey(k.id)} className="text-xs text-terminal-amber-bright active:text-terminal-amber py-1 px-2 bg-terminal-amber-faint border border-terminal-border-dim/50">
                {k.is_active ? 'ACTIVE' : 'SET ACTIVE'}
              </button>
              <button type="button" onClick={() => testKey(k.id)} className="text-xs text-terminal-green-text active:text-terminal-green-bright py-1 px-2 bg-terminal-green/10 border border-terminal-border-dim/50">
                TEST
              </button>
              <button type="button" onClick={() => deleteKey(k.id)} className="text-xs text-terminal-red-text active:text-terminal-red-bright py-1 px-2 bg-terminal-red/10 border border-terminal-border-dim/50">
                DELETE
              </button>
            </div>
            {testResults[k.id] && (
              <div className={`text-[10px] ${testResults[k.id].valid ? 'text-terminal-green-text' : 'text-terminal-red-text'}`}>
                {testResults[k.id].valid ? 'CONNECTION OK' : testResults[k.id].error || 'FAILED'}
              </div>
            )}
          </div>
        ))}
        {keys.length === 0 && (
          <div className="py-4 text-center text-terminal-amber-dim text-xs">NO API KEYS SAVED</div>
        )}
      </div>

      <button type="button" onClick={() => setShowAdd(true)} className="btn-primary text-xs mt-3">ADD KEY</button>

      <Modal open={showAdd} onClose={() => { setShowAdd(false); setSaveError(''); }} title="ADD API KEY">
        <div className="space-y-3 font-mono">
          {saveError && (
            <div className="text-xs text-terminal-red-text border border-terminal-red/40 bg-terminal-red/10 px-2 py-1.5">{saveError}</div>
          )}
          <div>
            <label className="block text-xs text-terminal-amber-dim mb-1 uppercase">NAME</label>
            <input type="text" value={newKey.name} onChange={(e) => setNewKey({ ...newKey, name: e.target.value })} className="input-field w-full" placeholder="MY KEY" />
          </div>
          <div>
            <label className="block text-xs text-terminal-amber-dim mb-1 uppercase">KEY ID</label>
            <input type="text" value={newKey.key_id} onChange={(e) => setNewKey({ ...newKey, key_id: e.target.value })} className="input-field w-full" />
          </div>
          <div>
            <label className="block text-xs text-terminal-amber-dim mb-1 uppercase">PRIVATE KEY (.key FILE OR PEM TEXT)</label>
            <div className="flex gap-2 mb-1">
              <label className="btn-secondary text-xs cursor-pointer inline-block">
                LOAD .KEY FILE
                <input
                  type="file"
                  accept=".key,.pem"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) {
                      const reader = new FileReader();
                      reader.onload = (ev) => {
                        const text = typeof ev.target?.result === 'string' ? ev.target.result : '';
                        setNewKey((prev) => ({ ...prev, key_secret: text }));
                      };
                      reader.readAsText(file);
                    }
                  }}
                />
              </label>
            </div>
            <textarea
              rows={4}
              value={newKey.key_secret}
              onChange={(e) => setNewKey({ ...newKey, key_secret: e.target.value })}
              className="input-field w-full font-mono text-xs resize-y"
              placeholder={"-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"}
            />
          </div>
          <label className="flex items-center gap-2 min-h-[44px]">
            <input type="checkbox" className="w-5 h-5 border-terminal-border-dim" style={{ accentColor: '#D4A017' }} checked={newKey.is_demo} onChange={(e) => setNewKey({ ...newKey, is_demo: e.target.checked })} />
            <span className="text-xs text-terminal-amber-dim uppercase">DEMO ENVIRONMENT</span>
          </label>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={() => setShowAdd(false)} className="btn-secondary">CANCEL</button>
            <button type="button" onClick={addKey} className="btn-primary">SAVE</button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
