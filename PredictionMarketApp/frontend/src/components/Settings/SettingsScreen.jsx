import React, { useEffect, useState, useCallback } from 'react';
import useAppStore from '../../store/useAppStore';
import ApiKeyManager from './ApiKeyManager';
import ExportHistory from './ExportHistory';
import RiskControls from './RiskControls';
import TradingSchedule from './TradingSchedule';
import AppSettings from './AppSettings';
import ConfirmDialog from '../shared/ConfirmDialog';

function normalizeSettingsForSave(obj) {
  const out = {};
  for (const [k, v] of Object.entries(obj || {})) {
    if (typeof v === 'boolean') out[k] = v ? 'true' : 'false';
    else if (v === null || v === undefined) out[k] = '';
    else out[k] = String(v);
  }
  return out;
}

export default function SettingsScreen() {
  const { firstLaunch, setTheme } = useAppStore();
  const [settings, setSettings] = useState({});
  const [showPanic, setShowPanic] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [saveError, setSaveError] = useState('');
  const [saving, setSaving] = useState(false);

  const loadSettings = useCallback(async () => {
    const res = await fetch('/api/settings');
    if (!res.ok) return;
    const data = await res.json();
    setSettings(data);
    if (data.theme === 'dark' || data.theme === 'light') setTheme(data.theme);
  }, [setTheme]);

  useEffect(() => { loadSettings(); }, [loadSettings]);

  const updateSetting = (key, value) => { setSettings((p) => ({ ...p, [key]: value })); setDirty(true); setSaveError(''); };

  const saveAll = async () => {
    setSaveError('');
    setSaving(true);
    try {
      const body = { settings: normalizeSettingsForSave(settings) };
      const res = await fetch('/api/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
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
      await loadSettings();
      setDirty(false);
    } catch (e) {
      setSaveError(e.message || 'Network error');
    } finally {
      setSaving(false);
    }
  };

  const handlePanic = async () => { await fetch('/api/settings/panic', { method: 'POST' }); };
  return (
    <div className="h-full overflow-y-auto relative">
      {dirty && (
        <div className="sticky top-0 z-10 flex flex-col sm:flex-row sm:items-center sm:justify-end gap-2 px-4 py-2 bg-terminal-surface/90 backdrop-blur border-b border-terminal-border-dim">
          {saveError && (
            <span className="text-[10px] font-mono text-terminal-red-text sm:mr-auto sm:text-right order-2 sm:order-1">{saveError}</span>
          )}
          <button type="button" onClick={saveAll} disabled={saving} className="btn-primary text-xs order-1 sm:order-2 disabled:opacity-50">
            {saving ? 'SAVING...' : 'SAVE ALL CONFIG'}
          </button>
        </div>
      )}
      <div className="max-w-3xl mx-auto px-3 md:px-4 py-4 md:py-6 space-y-4 md:space-y-6 pb-20 md:pb-6">
        <ApiKeyManager firstLaunch={firstLaunch} />
        <ExportHistory />
        <RiskControls settings={settings} onUpdate={updateSetting} onPanic={() => setShowPanic(true)} />
        <TradingSchedule enabled={settings.trading_schedule_enabled === 'true'} onToggle={(v) => updateSetting('trading_schedule_enabled', v ? 'true' : 'false')} />
        <AppSettings settings={settings} onUpdate={updateSetting} />
      </div>
      <ConfirmDialog open={showPanic} onClose={() => setShowPanic(false)} onConfirm={handlePanic} title="EMERGENCY STOP" message="This will close all open positions at market price and stop all running bots." confirmText="EMERGENCY STOP" danger />
    </div>
  );
}
