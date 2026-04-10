import React from 'react';

const GROUP_COLORS = [
  'border-blue-500',
  'border-purple-500',
  'border-teal-500',
  'border-amber-500',
];

export default function GroupBracket({ groupId, groupLogic, depth = 0, children }) {
  if (!groupId) return children;
  const color = GROUP_COLORS[depth % GROUP_COLORS.length];

  return (
    <div className={`border-l-2 ${color} ml-2 pl-2 relative`}>
      <span className="absolute -left-5 top-0 text-[10px] text-slate-500 font-mono">
        {groupLogic || 'AND'}
      </span>
      {children}
    </div>
  );
}
