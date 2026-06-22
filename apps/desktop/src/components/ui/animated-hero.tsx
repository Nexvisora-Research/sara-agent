import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'

import { SaraLogo } from './sara-logo'

const features = [
  { label: 'Code Generation', icon: '&lt;/&gt;', description: 'Write & refactor in any language' },
  { label: 'Memory', icon: '🧠', description: 'Persistent context across sessions' },
  { label: 'Terminal', icon: '▸', description: 'Native shell execution' },
  { label: 'Multi-Agent', icon: '⊕', description: 'Orchestrate swarms of agents' }
]

function FloatingParticle({ index }: { index: number }) {
  const x = 20 + (index * 17) % 60
  const y = 10 + (index * 23) % 50
  const size = 2 + (index % 3)
  const duration = 3 + (index % 4)
  const delay = index * 0.4

  return (
    <motion.div
      className="absolute rounded-full bg-(--ui-accent)"
      style={{
        left: `${x}%`,
        top: `${y}%`,
        width: size,
        height: size,
        opacity: 0.3
      }}
      animate={{
        y: [-8, 8, -8],
        opacity: [0.15, 0.4, 0.15]
      }}
      transition={{
        duration,
        repeat: Infinity,
        delay,
        ease: 'easeInOut'
      }}
    />
  )
}

function TypewriterText({ text, delay = 0 }: { text: string; delay?: number }) {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => setVisible(true), delay)
    return () => clearTimeout(timer)
  }, [delay])

  return (
    <span className="text-(--ui-text-tertiary) font-mono text-xs tracking-widest uppercase">
      {visible ? text : ''}
      <motion.span
        animate={{ opacity: [1, 0] }}
        transition={{ duration: 0.8, repeat: Infinity, repeatType: 'reverse' }}
      >
        _
      </motion.span>
    </span>
  )
}

interface AnimatedHeroProps {
  onNewChat: () => void
}

export function AnimatedHero({ onNewChat }: AnimatedHeroProps) {
  const particles = Array.from({ length: 12 }, (_, i) => i)

  return (
    <div className="relative flex h-full w-full flex-col items-center justify-center overflow-hidden bg-(--ui-bg-chrome) select-none">
      {/* Particles */}
      {particles.map(i => (
        <FloatingParticle key={i} index={i} />
      ))}

      {/* Gradient glow */}
      <div
        className="pointer-events-none absolute h-[600px] w-[600px] rounded-full opacity-[0.08] blur-[120px]"
        style={{
          background: 'radial-gradient(circle, #ff2d55 0%, transparent 70%)'
        }}
      />

      {/* Content */}
      <motion.div
        className="relative z-10 flex flex-col items-center gap-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
      >
        {/* Logo + Status */}
        <motion.div
          className="flex flex-col items-center gap-3"
          initial={{ scale: 0.9 }}
          animate={{ scale: 1 }}
          transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        >
          <div className="relative">
            <SaraLogo size={56} animated />
            <div className="absolute -right-1 -top-1 h-3 w-3 rounded-full bg-(--ui-accent) shadow-[0_0_8px_rgba(255,45,85,0.4)]" />
          </div>
          <TypewriterText text="SARA AI OS · READY" delay={300} />
        </motion.div>

        {/* Title */}
        <motion.h1
          className="font-heading text-6xl font-bold tracking-tight text-white"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
        >
          How can I help?
        </motion.h1>

        <motion.p
          className="max-w-md text-center text-(--ui-text-secondary) text-sm leading-relaxed"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.4 }}
        >
          Your AI operating system for code, automation, and multi-agent orchestration
        </motion.p>

        {/* Quick action cards */}
        <motion.div
          className="mt-4 grid grid-cols-2 gap-3"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.6 }}
        >
          {features.map((feature, i) => (
            <motion.button
              key={feature.label}
              className="glass group flex cursor-pointer items-center gap-3 rounded-xl border-(--ui-stroke-quaternary) px-4 py-3 transition-all duration-200 hover:border-(--ui-stroke-secondary) hover:bg-(--ui-bg-quaternary) hover:shadow-[0_0_20px_rgba(255,45,85,0.08)]"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={onNewChat}
            >
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-(--ui-bg-tertiary) font-mono text-sm text-(--ui-accent)">
                {feature.icon}
              </span>
              <div className="flex flex-col items-start gap-0.5">
                <span className="text-sm font-medium text-white">{feature.label}</span>
                <span className="text-xs text-(--ui-text-secondary)">{feature.description}</span>
              </div>
            </motion.button>
          ))}
        </motion.div>

        {/* Command hint */}
        <motion.div
          className="glass mt-2 flex items-center gap-2 rounded-full border-(--ui-stroke-quaternary) px-4 py-2"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 1 }}
        >
          <kbd className="flex h-5 items-center rounded bg-(--ui-bg-tertiary) px-1.5 font-mono text-[10px] text-(--ui-text-secondary)">
            ⌘K
          </kbd>
          <span className="text-xs text-(--ui-text-secondary)">Command palette</span>
          <span className="mx-1 text-(--ui-text-quaternary)">·</span>
          <kbd className="flex h-5 items-center rounded bg-(--ui-bg-tertiary) px-1.5 font-mono text-[10px] text-(--ui-text-secondary)">
            ⌘N
          </kbd>
          <span className="text-xs text-(--ui-text-secondary)">New chat</span>
        </motion.div>
      </motion.div>
    </div>
  )
}
