import { useState } from 'react';
import { twMerge } from 'tailwind-merge';

export default function Tooltip({ text, children, className }) {
  const [isVisible, setIsVisible] = useState(false);

  return (
    <div 
      className={twMerge('relative inline-flex', className)}
      onMouseEnter={() => setIsVisible(true)}
      onMouseLeave={() => setIsVisible(false)}
    >
      {children}
      {isVisible && (
        <div className="absolute z-50 bottom-full mb-2 left-1/2 -translate-x-1/2 px-2.5 py-1.5 bg-elevated border border-subtle rounded-md shadow-card text-xs text-primary whitespace-nowrap">
          {text}
          <div className="absolute top-full left-1/2 -translate-x-1/2 border-[4px] border-transparent border-t-elevated" />
        </div>
      )}
    </div>
  );
}
