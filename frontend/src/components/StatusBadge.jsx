import clsx from 'clsx';
import { twMerge } from 'tailwind-merge';

export default function StatusBadge({ status, label }) {
  const statusMap = {
    green: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    yellow: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
    red: 'bg-red-500/10 text-red-400 border-red-500/20',
  };

  const dotMap = {
    green: 'bg-emerald-500',
    yellow: 'bg-yellow-500',
    red: 'bg-red-500',
  };

  const normalizedStatus = status?.toLowerCase() === 'healthy' || status?.toLowerCase() === 'online' || status?.toLowerCase() === 'active' || status?.toLowerCase() === 'good' ? 'green' 
    : status?.toLowerCase() === 'degraded' || status?.toLowerCase() === 'loading' || status?.toLowerCase() === 'stable' ? 'yellow' 
    : status?.toLowerCase() === 'failure' || status?.toLowerCase() === 'offline' ? 'red' : 'yellow';

  return (
    <div className={twMerge(clsx('inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border', statusMap[normalizedStatus]))}>
      <span className={twMerge(clsx('w-1.5 h-1.5 rounded-full mr-1.5', dotMap[normalizedStatus]))}></span>
      {label || status}
    </div>
  );
}
