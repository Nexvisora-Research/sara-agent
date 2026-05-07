import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

interface Props {
  onClose: () => void;
}

export default function PluginConnectModal({ onClose }: Props) {
  const [selectedPlugin, setSelectedPlugin] = useState<string | null>(null);
  const [credentials, setCredentials] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [plugins, setPlugins] = useState<Array<any>>([]);

  useEffect(() => {
    window.saraGUI?.plugins.list().then(setPlugins);
  }, []);

  const handleConnect = async () => {
    if (!selectedPlugin) return;
    setLoading(true);
    setError('');
    try {
      const result = await window.saraGUI?.plugins.activate(selectedPlugin, credentials);
      if (result) onClose();
      else setError('Connection failed. Check your credentials.');
    } catch (err: any) {
      setError(err.message || 'Connection failed');
    }
    setLoading(false);
  };

  const selected = plugins.find(p => p.id === selectedPlugin);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        className="bg-bg-card border border-white/10 rounded-2xl p-6 w-[480px] max-h-[80vh] overflow-auto"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-text-primary">Connect a Messenger</h2>
          <button onClick={onClose} className="text-text-muted hover:text-text-primary text-xl">✕</button>
        </div>

        {/* Plugin selection */}
        <div className="grid grid-cols-2 gap-3 mb-6">
          {plugins.map(p => (
            <button
              key={p.id}
              onClick={() => setSelectedPlugin(p.id)}
              className={`p-4 rounded-xl border-2 transition-all text-left ${
                selectedPlugin === p.id
                  ? 'border-primary bg-primary/10'
                  : 'border-white/5 bg-bg-surface hover:border-white/20'
              } ${p.connected ? 'opacity-60' : ''}`}
            >
              <div className="text-2xl mb-2">{p.icon === 'telegram' ? '📨' : p.icon === 'discord' ? '🎮' : '🔌'}</div>
              <p className="font-medium text-text-primary">{p.name}</p>
              <p className="text-xs text-text-muted">{p.connected ? '✓ Connected' : 'Click to connect'}</p>
            </button>
          ))}
          {/* Coming soon */}
          <div className="p-4 rounded-xl border-2 border-dashed border-white/10 bg-bg-surface opacity-50">
            <div className="text-2xl mb-2">💬</div>
            <p className="font-medium text-text-muted">WhatsApp</p>
            <p className="text-xs text-text-muted">Coming soon</p>
          </div>
          <div className="p-4 rounded-xl border-2 border-dashed border-white/10 bg-bg-surface opacity-50">
            <div className="text-2xl mb-2">🐦</div>
            <p className="font-medium text-text-muted">X / Twitter</p>
            <p className="text-xs text-text-muted">Coming soon</p>
          </div>
        </div>

        {/* Credential form */}
        {selected && !selected.connected && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} className="space-y-3 mb-4">
            <p className="text-sm text-text-secondary">Enter your {selected.name} credentials:</p>
            {(selected.manifest?.requiredCredentials || []).map((cred: any) => (
              <div key={cred.key}>
                <label className="text-xs text-text-muted block mb-1">{cred.label}</label>
                <input
                  type={cred.sensitive ? 'password' : 'text'}
                  placeholder={cred.placeholder}
                  value={credentials[cred.key] || ''}
                  onChange={e => setCredentials(prev => ({ ...prev, [cred.key]: e.target.value }))}
                  className="w-full bg-bg-surface border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-primary"
                />
              </div>
            ))}
          </motion.div>
        )}

        {error && <p className="text-error text-sm mb-4">{error}</p>}

        {/* Actions */}
        <div className="flex gap-3">
          <button onClick={onClose} className="flex-1 py-2.5 rounded-xl border border-white/10 text-text-muted hover:bg-bg-hover transition-colors">
            Cancel
          </button>
          <button
            onClick={handleConnect}
            disabled={!selectedPlugin || loading}
            className="flex-1 py-2.5 rounded-xl bg-primary hover:bg-primary-light text-white font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Connecting...' : 'Connect'}
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}