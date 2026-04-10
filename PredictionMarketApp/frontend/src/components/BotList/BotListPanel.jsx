import React, { useEffect, useState, useMemo, useCallback, useRef } from 'react';
import useAppStore from '../../store/useAppStore';
import useBotStore from '../../store/useBotStore';
import BotGroup from './BotGroup';
import BotRow from './BotRow';
import ConfirmDialog from '../shared/ConfirmDialog';
import Modal from '../shared/Modal';

export default function BotListPanel() {
  const { setActiveBotId, setActiveTab, setBulkEditIds } = useAppStore();
  const { groups, ungroupedBots, fetchBots, loading } = useBotStore();
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [confirmDeleteGroup, setConfirmDeleteGroup] = useState(null);
  const [showNewBot, setShowNewBot] = useState(false);
  const [showNewGroup, setShowNewGroup] = useState(false);
  const [newBotName, setNewBotName] = useState('');
  const [newGroupName, setNewGroupName] = useState('');
  const [selectedIds, setSelectedIds] = useState([]);
  const [bulkDeleteOpen, setBulkDeleteOpen] = useState(false);
  const selectAllRef = useRef(null);

  const availableGroups = useMemo(
    () => groups.map((g) => ({ id: g.id, name: g.name })),
    [groups],
  );

  const allBotIds = useMemo(() => {
    const ids = ungroupedBots.map((b) => b.id);
    for (const g of groups) {
      for (const b of g.bots || []) ids.push(b.id);
    }
    return ids;
  }, [groups, ungroupedBots]);

  const allVisibleSelected = allBotIds.length > 0 && allBotIds.every((id) => selectedIds.includes(id));

  const toggleSelect = useCallback((id) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }, []);

  const toggleSelectGroup = useCallback((group) => {
    const ids = (group.bots || []).map((b) => b.id);
    if (ids.length === 0) return;
    setSelectedIds((prev) => {
      const allOn = ids.every((id) => prev.includes(id));
      if (allOn) return prev.filter((id) => !ids.includes(id));
      const next = new Set(prev);
      ids.forEach((id) => next.add(id));
      return [...next];
    });
  }, []);

  const toggleSelectAll = useCallback(() => {
    if (allVisibleSelected) setSelectedIds([]);
    else setSelectedIds([...allBotIds]);
  }, [allBotIds, allVisibleSelected]);

  const clearSelection = useCallback(() => setSelectedIds([]), []);

  const bulkEditFirst = useCallback(() => {
    const id = selectedIds[0];
    if (id == null) return;
    setBulkEditIds(selectedIds.length > 1 ? [...selectedIds] : []);
    setActiveBotId(id);
    setActiveTab('editor');
  }, [selectedIds, setActiveBotId, setActiveTab, setBulkEditIds]);

  const bulkStartSelected = useCallback(async () => {
    if (selectedIds.length === 0) return;
    for (const id of selectedIds) {
      await fetch(`/api/bots/${id}/start`, { method: 'POST' });
    }
    fetchBots();
  }, [selectedIds, fetchBots]);

  const bulkStopSelected = useCallback(async () => {
    if (selectedIds.length === 0) return;
    for (const id of selectedIds) {
      await fetch(`/api/bots/${id}/stop`, { method: 'POST' });
    }
    fetchBots();
  }, [selectedIds, fetchBots]);

  const bulkCopySelected = useCallback(async () => {
    if (selectedIds.length === 0) return;
    for (const id of selectedIds) {
      await fetch(`/api/bots/${id}/copy`, { method: 'POST' });
    }
    fetchBots();
  }, [selectedIds, fetchBots]);

  const deleteBulkConfirmed = useCallback(async () => {
    const ids = [...selectedIds];
    setBulkDeleteOpen(false);
    for (const id of ids) {
      await fetch(`/api/bots/${id}`, { method: 'DELETE' });
    }
    setSelectedIds([]);
    fetchBots();
  }, [selectedIds, fetchBots]);

  useEffect(() => {
    const el = selectAllRef.current;
    if (el) {
      el.indeterminate = selectedIds.length > 0 && !allVisibleSelected;
    }
  }, [selectedIds.length, allVisibleSelected]);

  useEffect(() => { fetchBots(); }, []);

  const selectBot = (bot) => { setBulkEditIds([]); setActiveBotId(bot.id); setActiveTab('editor'); };
  const startBot = async (id) => { await fetch(`/api/bots/${id}/start`, { method: 'POST' }); fetchBots(); };
  const stopBot = async (id) => { await fetch(`/api/bots/${id}/stop`, { method: 'POST' }); fetchBots(); };
  const copyBot = async (id) => { await fetch(`/api/bots/${id}/copy`, { method: 'POST' }); fetchBots(); };
  const deleteBot = async (id) => {
    await fetch(`/api/bots/${id}`, { method: 'DELETE' });
    setSelectedIds((prev) => prev.filter((x) => x !== id));
    fetchBots();
  };
  const startAll = async (groupId) => { await fetch(`/api/groups/${groupId}/start-all`, { method: 'POST' }); fetchBots(); };
  const stopAll = async (groupId) => { await fetch(`/api/groups/${groupId}/stop-all`, { method: 'POST' }); fetchBots(); };

  const moveBotToGroup = async (botId, groupId) => {
    await fetch(`/api/bots/${botId}/move`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ group_id: groupId }),
    });
    fetchBots();
  };

  const deleteGroupConfirmed = async () => {
    const g = confirmDeleteGroup;
    if (!g) return;
    await fetch(`/api/groups/${g.id}`, { method: 'DELETE' });
    fetchBots();
  };

  const createBot = async () => {
    if (!newBotName.trim()) return;
    await fetch('/api/bots', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: newBotName }) });
    setShowNewBot(false); setNewBotName(''); fetchBots();
  };

  const createGroup = async () => {
    if (!newGroupName.trim()) return;
    await fetch('/api/groups', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: newGroupName }) });
    setShowNewGroup(false); setNewGroupName(''); fetchBots();
  };

  const isEmpty = groups.length === 0 && ungroupedBots.length === 0;

  return (
    <div className="h-full flex flex-col">
      <div className="border-b border-terminal-border-dim">
      <div className="max-w-3xl mx-auto flex items-center justify-between px-3 md:px-4 py-2 gap-1.5 flex-wrap">
        <h2 className="panel-header">BOT REGISTRY</h2>
        <div className="flex gap-1 items-center flex-wrap">
          {selectedIds.length > 0 && (
            <>
              <span
                className="text-[9px] font-mono text-terminal-amber-bright border border-terminal-amber/40 px-1.5 py-0.5"
                title={`${selectedIds.length} bot(s) selected`}
              >
                {selectedIds.length} SEL
              </span>
              <div className="flex gap-0.5 flex-wrap items-center border-l border-terminal-border-dim/60 pl-1.5 ml-0.5">
                <button
                  type="button"
                  onClick={bulkStartSelected}
                  className="btn-secondary text-[11px] py-0.5 px-1.5 text-terminal-green-text border-terminal-green/40 hover:border-terminal-green/60"
                  title={selectedIds.length > 1 ? 'Start each selected bot' : 'Start bot'}
                >
                  START
                </button>
                <button
                  type="button"
                  onClick={bulkStopSelected}
                  className="btn-secondary text-[11px] py-0.5 px-1.5 text-terminal-amber border-terminal-border-dim hover:border-terminal-amber/40"
                  title={selectedIds.length > 1 ? 'Stop each selected bot' : 'Stop bot'}
                >
                  STOP
                </button>
                <button
                  type="button"
                  onClick={bulkEditFirst}
                  className="btn-secondary text-[11px] py-0.5 px-1.5"
                  title={selectedIds.length > 1 ? 'Open the first selected bot in the rules editor' : 'Open in rules editor'}
                >
                  EDIT
                </button>
                <button
                  type="button"
                  onClick={bulkCopySelected}
                  className="btn-secondary text-[11px] py-0.5 px-1.5"
                  title={selectedIds.length > 1 ? 'Copy each selected bot' : 'Copy bot'}
                >
                  COPY
                </button>
                <button
                  type="button"
                  onClick={() => selectedIds.length > 0 && setBulkDeleteOpen(true)}
                  className="btn-secondary text-[11px] py-0.5 px-1.5 text-terminal-red-text border-terminal-red/30 hover:border-terminal-red/50"
                  title={selectedIds.length > 1 ? 'Delete all selected bots' : 'Delete bot'}
                >
                  DELETE
                </button>
              </div>
              <button type="button" onClick={clearSelection} className="btn-secondary text-[11px] py-0.5 px-1.5">
                CLEAR
              </button>
            </>
          )}
          <button type="button" onClick={() => setShowNewGroup(true)} className="btn-secondary text-[11px] py-0.5 px-1.5">NEW GROUP</button>
          <button type="button" onClick={() => setShowNewBot(true)} className="btn-primary text-[11px] py-0.5 px-1.5">NEW BOT</button>
        </div>
      </div>
      </div>

      <div className="border-b border-terminal-border-dim/50 bg-terminal-panel">
      <div className="hidden md:flex max-w-3xl mx-auto items-center gap-2 px-3 md:px-4 py-1 text-[9px] text-terminal-amber-dim uppercase tracking-wide font-mono">
        <label className="w-5 shrink-0 flex items-center justify-center cursor-pointer" title="Select all bots">
          <input
            ref={selectAllRef}
            type="checkbox"
            checked={allVisibleSelected}
            onChange={toggleSelectAll}
            disabled={allBotIds.length === 0}
            className="registry-checkbox w-3.5 h-3.5 border border-terminal-amber bg-terminal-bg rounded-sm disabled:opacity-30"
            style={{ accentColor: '#D4A017' }}
            aria-label="Select all bots"
          />
        </label>
        <span className="w-2" />
        <span className="flex-1">NAME</span>
        <span className="w-24 shrink-0" title="Market ticker">MKT</span>
        <span className="w-14 shrink-0 text-right" title="Status">STAT</span>
        <span className="w-10 shrink-0 text-right" title="Run count">RUN</span>
        <span className="w-6 shrink-0" />
      </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto">
        {loading && <div className="flex items-center justify-center h-32 text-xs text-terminal-amber-dim font-mono">LOADING...</div>}
        {isEmpty && !loading && (
          <div className="flex flex-col items-center justify-center h-64 gap-4">
            <p className="text-terminal-amber-dim text-xs font-mono">NO BOTS REGISTERED. CREATE YOUR FIRST BOT.</p>
            <button onClick={() => setShowNewBot(true)} className="btn-primary">CREATE FIRST BOT</button>
          </div>
        )}
        {groups.map((group) => (
          <BotGroup
            key={group.id}
            group={group}
            onSelectBot={selectBot}
            onStartBot={startBot}
            onStopBot={stopBot}
            onCopyBot={copyBot}
            onDeleteBot={(id) => setConfirmDelete(id)}
            onStartAll={startAll}
            onStopAll={stopAll}
            onRequestDeleteGroup={() =>
              setConfirmDeleteGroup({
                id: group.id,
                name: group.name,
                botCount: group.bots?.length || 0,
              })
            }
            onMoveToGroup={moveBotToGroup}
            availableGroups={availableGroups}
            selectedIds={selectedIds}
            onToggleSelect={toggleSelect}
            onToggleSelectGroup={toggleSelectGroup}
          />
        ))}
        {ungroupedBots.map((bot) => (
          <BotRow
            key={bot.id}
            bot={bot}
            onSelect={selectBot}
            onStart={startBot}
            onStop={stopBot}
            onCopy={copyBot}
            onDelete={(id) => setConfirmDelete(id)}
            onMoveToGroup={moveBotToGroup}
            availableGroups={availableGroups}
            selected={selectedIds.includes(bot.id)}
            onToggleSelect={toggleSelect}
          />
        ))}
        </div>
      </div>

      <ConfirmDialog open={confirmDelete !== null} onClose={() => setConfirmDelete(null)} onConfirm={() => deleteBot(confirmDelete)} title="DELETE BOT" message="Are you sure you want to delete this bot? This cannot be undone." confirmText="DELETE" danger />

      <ConfirmDialog
        open={bulkDeleteOpen}
        onClose={() => setBulkDeleteOpen(false)}
        onConfirm={deleteBulkConfirmed}
        title="DELETE BOTS"
        message={
          selectedIds.length > 1
            ? `Delete ${selectedIds.length} bots? This cannot be undone.`
            : 'Delete this bot? This cannot be undone.'
        }
        confirmText="DELETE"
        danger
      />

      <ConfirmDialog
        open={confirmDeleteGroup !== null}
        onClose={() => setConfirmDeleteGroup(null)}
        onConfirm={deleteGroupConfirmed}
        title="DELETE GROUP"
        message={
          confirmDeleteGroup
            ? confirmDeleteGroup.botCount > 0
              ? `Delete folder "${confirmDeleteGroup.name}"? The ${confirmDeleteGroup.botCount} bot(s) inside will move to ungrouped (they are not deleted).`
              : `Delete empty folder "${confirmDeleteGroup.name}"?`
            : ''
        }
        confirmText="DELETE GROUP"
        danger
      />

      <Modal open={showNewBot} onClose={() => setShowNewBot(false)} title="CREATE BOT">
        <div className="space-y-4">
          <input type="text" value={newBotName} onChange={(e) => setNewBotName(e.target.value)} placeholder="Bot name" className="input-field w-full" onKeyDown={(e) => e.key === 'Enter' && createBot()} autoFocus />
          <div className="flex justify-end gap-3">
            <button onClick={() => setShowNewBot(false)} className="btn-secondary">CANCEL</button>
            <button onClick={createBot} className="btn-primary">CREATE</button>
          </div>
        </div>
      </Modal>

      <Modal open={showNewGroup} onClose={() => setShowNewGroup(false)} title="CREATE GROUP">
        <div className="space-y-4">
          <input type="text" value={newGroupName} onChange={(e) => setNewGroupName(e.target.value)} placeholder="Group name" className="input-field w-full" onKeyDown={(e) => e.key === 'Enter' && createGroup()} autoFocus />
          <div className="flex justify-end gap-3">
            <button onClick={() => setShowNewGroup(false)} className="btn-secondary">CANCEL</button>
            <button onClick={createGroup} className="btn-primary">CREATE</button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
