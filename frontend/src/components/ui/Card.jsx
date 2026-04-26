import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export default function Card({ children, accent, className }) {
  const normalizedAccent = accent?.toUpperCase();
  
  let borderAccent = '';
  if (normalizedAccent === 'CRITICAL') borderAccent = 'border-t-4 border-t-red-500';
  else if (normalizedAccent === 'HIGH') borderAccent = 'border-t-4 border-t-orange-500';
  else if (normalizedAccent === 'MEDIUM') borderAccent = 'border-t-4 border-t-yellow-500';
  else if (normalizedAccent === 'LOW') borderAccent = 'border-t-4 border-t-green-500';
  else borderAccent = 'border border-subtle';

  return (
    <div className={twMerge(
      'bg-surface rounded-xl shadow-card',
      borderAccent,
      className
    )}>
      {children}
    </div>
  );
}
