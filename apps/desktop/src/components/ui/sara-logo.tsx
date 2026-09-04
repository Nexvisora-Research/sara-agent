import { cn } from '@/lib/utils'

interface SaraLogoProps {
  className?: string
  size?: number
  animated?: boolean
  variant?: 'asset' | 'glyph'
}

const assetPath = (path: string) => `${import.meta.env.BASE_URL}${path.replace(/^\/+/, '')}`

export function SaraLogo({ className, size = 32, animated = true, variant = 'asset' }: SaraLogoProps) {
  if (variant === 'asset') {
    return (
      <img
        alt=""
        className={cn('shrink-0 rounded-[0.35rem] object-cover', animated && 'animate-[saraPulse_3s_ease-in-out_infinite]', className)}
        height={size}
        src={assetPath('sara-logo.png')}
        style={{ height: size, width: size }}
        width={size}
      />
    )
  }

  return (
    <svg
      className={cn(
        animated && 'animate-[saraPulse_3s_ease-in-out_infinite]',
        className
      )}
      fill="none"
      height={size}
      viewBox="0 0 32 32"
      width={size}
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id="saraGrad" x1="0" x2="32" y1="0" y2="32">
          <stop offset="0%" stopColor="#ff2d55" />
          <stop offset="100%" stopColor="#cc0033" />
        </linearGradient>
      </defs>
      {/* Ant body - elongated oval */}
      <ellipse cx="16" cy="20" fill="url(#saraGrad)" rx="7" ry="4.5" />
      {/* Ant head - smaller circle */}
      <circle cx="16" cy="11" fill="#ff2d55" r="3.5" />
      {/* Left antenna */}
      <path
        className={animated ? 'animate-[antennaWave_2s_ease-in-out_infinite]' : undefined}
        d="M13.5 8.5C12 6.5 9.5 4.5 8 3.5"
        fill="none"
        stroke="#ff2d55"
        strokeLinecap="round"
        strokeWidth="1.2"
        style={{ transformOrigin: '13.5px 8.5px' }}
      />
      {/* Right antenna */}
      <path
        className={animated ? 'animate-[antennaWave_2s_ease-in-out_infinite_0.3s]' : undefined}
        d="M18.5 8.5C20 6.5 22.5 4.5 24 3.5"
        fill="none"
        stroke="#ff2d55"
        strokeLinecap="round"
        strokeWidth="1.2"
        style={{ transformOrigin: '18.5px 8.5px' }}
      />
      {/* Ant legs */}
      <line stroke="#ff2d55" strokeLinecap="round" strokeWidth="1" x1="10" x2="6" y1="18" y2="15" />
      <line stroke="#ff2d55" strokeLinecap="round" strokeWidth="1" x1="10" x2="5" y1="20" y2="20" />
      <line stroke="#ff2d55" strokeLinecap="round" strokeWidth="1" x1="10" x2="6" y1="22" y2="25" />
      <line stroke="#ff2d55" strokeLinecap="round" strokeWidth="1" x1="22" x2="26" y1="18" y2="15" />
      <line stroke="#ff2d55" strokeLinecap="round" strokeWidth="1" x1="22" x2="27" y1="20" y2="20" />
      <line stroke="#ff2d55" strokeLinecap="round" strokeWidth="1" x1="22" x2="26" y1="22" y2="25" />
      {/* Eye */}
      <circle cx="16" cy="10.5" fill="#050505" r="0.8" />
    </svg>
  )
}
