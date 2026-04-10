import React from 'react';
import { ResponsiveContainer, LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell } from 'recharts';

export default function PnLChart({ data, chartType }) {
  if (!data || data.length === 0) return <div className="flex items-center justify-center h-64 text-xs text-terminal-amber-dim font-mono">NO CHART DATA AVAILABLE</div>;
  const chartData = data.map((d) => ({ date: d.date, pnl: d.pnl || 0 }));
  if (chartType === 'bar') {
    return (
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#5a4510" />
          <XAxis dataKey="date" tick={{ fill: '#8B7215', fontSize: 10, fontFamily: 'JetBrains Mono' }} />
          <YAxis tick={{ fill: '#8B7215', fontSize: 10, fontFamily: 'JetBrains Mono' }} />
          <Tooltip contentStyle={{ backgroundColor: '#0f0f0f', border: '1px solid #D4A017', borderRadius: '0' }} labelStyle={{ color: '#D4A017', fontFamily: 'JetBrains Mono' }} />
          <Bar dataKey="pnl">{chartData.map((entry, i) => (<Cell key={i} fill={entry.pnl >= 0 ? '#2B3623' : '#8B2500'} />))}</Bar>
        </BarChart>
      </ResponsiveContainer>
    );
  }
  let cumulative = 0;
  const lineData = chartData.map((d) => { cumulative += d.pnl; return { ...d, cumulative }; });
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={lineData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#5a4510" />
        <XAxis dataKey="date" tick={{ fill: '#8B7215', fontSize: 10, fontFamily: 'JetBrains Mono' }} />
        <YAxis tick={{ fill: '#8B7215', fontSize: 10, fontFamily: 'JetBrains Mono' }} />
        <Tooltip contentStyle={{ backgroundColor: '#0f0f0f', border: '1px solid #D4A017', borderRadius: '0' }} labelStyle={{ color: '#D4A017', fontFamily: 'JetBrains Mono' }} />
        <Line type="monotone" dataKey="cumulative" stroke="#D4A017" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
