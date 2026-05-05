import { cn } from '@/src/lib/utils';

interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  color?: string;
  className?: string;
}

const sizeMap = { sm: 16, md: 24, lg: 32 };

export default function Spinner({ size = 'md', color, className }: SpinnerProps) {
  const px = sizeMap[size];
  return (
    <span role="status" className={cn('inline-flex', className)} style={color ? { color } : undefined}>
      <svg
        width={px}
        height={px}
        viewBox="0 0 24 24"
        fill="none"
        aria-hidden="true"
        className="animate-spin"
      >
        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" opacity="0.2" />
        <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
      </svg>
      <span className="sr-only">加载中...</span>
    </span>
  );
}
