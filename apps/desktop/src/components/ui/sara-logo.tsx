import { cn } from '@/lib/utils'

interface SaraLogoProps {
  className?: string
  size?: number
  animated?: boolean
}

export function SaraLogo({ className, size = 32, animated = true }: SaraLogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={cn(
        animated && 'animate-[saraPulse_3s_ease-in-out_infinite]',
        className
      )}
    >
      <defs>
        <linearGradient id="saraGrad" x1="0" y1="0" x2="32" y2="32">
          <stop offset="0%" stopColor="#ff2d55" />
          <stop offset="100%" stopColor="#cc0033" />
        </linearGradient>
      </defs>
      {/* Ant body - elongated oval */}
      <ellipse cx="16" cy="20" rx="7" ry="4.5" fill="url(#saraGrad)" />
      {/* Ant head - smaller circle */}
      <circle cx="16" cy="11" r="3.5" fill="#ff2d55" />
      {/* Left antenna */}
      <path
        d="M13.5 8.5C12 6.5 9.5 4.5 8 3.5"
        stroke="#ff2d55"
        strokeWidth="1.2"
        strokeLinecap="round"
        fill="none"
        className={animated ? 'animate-[antennaWave_2s_ease-in-out_infinite]' : undefined}
        style={{ transformOrigin: '13.5px 8.5px' }}
      />
      {/* Right antenna */}
      <path
        d="M18.5 8.5C20 6.5 22.5 4.5 24 3.5"
        stroke="#ff2d55"
        strokeWidth="1.2"
        strokeLinecap="round"
        fill="none"
        className={animated ? 'animate-[antennaWave_2s_ease-in-out_infinite_0.3s]' : undefined}
        style={{ transformOrigin: '18.5px 8.5px' }}
      />
      {/* Ant legs */}
      <line x1="10" y1="18" x2="6" y2="15" stroke="#ff2d55" strokeWidth="1" strokeLinecap="round" />
      <line x1="10" y1="20" x2="5" y2="20" stroke="#ff2d55" strokeWidth="1" strokeLinecap="round" />
      <line x1="10" y1="22" x2="6" y2="25" stroke="#ff2d55" strokeWidth="1" strokeLinecap="round" />
      <line x1="22" y1="18" x2="26" y2="15" stroke="#ff2d55" strokeWidth="1" strokeLinecap="round" />
      <line x1="22" y1="20" x2="27" y2="20" stroke="#ff2d55" strokeWidth="1" strokeLinecap="round" />
      <line x1="22" y1="22" x2="26" y2="25" stroke="#ff2d55" strokeWidth="1" strokeLinecap="round" />
      {/* Eye */}
      <circle cx="16" cy="10.5" r="0.8" fill="#050505" />
    </svg>
  )
}
