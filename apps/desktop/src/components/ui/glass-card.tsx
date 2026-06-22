import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

interface GlassCardProps {
  children: ReactNode
  className?: string
  variant?: 'subtle' | 'default' | 'strong'
  hover?: boolean
}

const variantStyles = {
  subtle: 'glass-subtle',
  default: 'glass',
  strong: 'glass-strong'
}

export function GlassCard({ children, className, variant = 'default', hover = false }: GlassCardProps) {
  return (
    <div
      className={cn(
        'rounded-2xl',
        variantStyles[variant],
        hover && 'cursor-pointer transition-all duration-200 hover:border-(--ui-stroke-secondary) hover:bg-(--ui-bg-quaternary)',
        className
      )}
    >
      {children}
    </div>
  )
}
