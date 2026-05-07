import React from 'react';
import { motion } from 'framer-motion';

export default function VoiceIndicator() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }}
      className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50"
    >
      <div className="glass rounded-2xl px-6 py-4 flex items-center gap-4 glow">
        <div className="flex items-center gap-1">
          {[1,2,3,4,5].map(i => (
            <motion.div
              key={i}
              animate={{ height: [8, 24, 8] }}
              transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.1 }}
              className="w-1 bg-accent rounded-full"
            />
          ))}
        </div>
        <div>
          <p className="text-sm font-medium text-text-primary">🎤 Listening...</p>
          <p className="text-xs text-text-muted">Say a command like "Open Telegram"</p>
        </div>
      </div>
    </motion.div>
  );
}