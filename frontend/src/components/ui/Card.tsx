import { HTMLAttributes, forwardRef } from 'react';
import { cn } from '@/src/lib/utils';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  hover?: boolean;
}

const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ hover, className, children, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'bg-surface rounded-lg shadow-card border border-border-light',
        hover && 'hover:shadow-md transition-shadow cursor-pointer',
        className,
      )}
      {...props}
    >
      {children}
    </div>
  ),
);

Card.displayName = 'Card';
export default Card;
