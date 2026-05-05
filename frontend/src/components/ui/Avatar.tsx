import { useState } from 'react';
import { cn } from '@/src/lib/utils';

interface AvatarProps {
  src?: string | null;
  name: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const sizeMap = { sm: 'w-8 h-8 text-xs', md: 'w-10 h-10 text-sm', lg: 'w-12 h-12 text-base' };

function getInitials(name: string): string {
  return name.slice(0, 2).toUpperCase();
}

export default function Avatar({ src, name, size = 'md', className }: AvatarProps) {
  const [imgError, setImgError] = useState(false);
  const showImage = src && !imgError;

  return (
    <div className={cn('relative rounded-full overflow-hidden shrink-0', sizeMap[size], className)}>
      {showImage ? (
        <img
          src={src}
          alt={name}
          onError={() => setImgError(true)}
          className="w-full h-full object-cover"
        />
      ) : (
        <div className="w-full h-full flex items-center justify-center font-semibold text-white bg-gradient-to-br from-brand-500 to-brand-600">
          {getInitials(name)}
        </div>
      )}
    </div>
  );
}
