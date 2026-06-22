import { useEffect, useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import Layout from '@theme/Layout';
import Link from '@docusaurus/Link';
import useBaseUrl from '@docusaurus/useBaseUrl';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';

const QUICK_LINKS = [
  { icon: '🚀', label: 'Installation', desc: 'Get started with Sara Agent in minutes', href: '/getting-started/installation' },
  { icon: '📚', label: 'Quickstart', desc: 'Your first session with Sara', href: '/getting-started/quickstart' },
  { icon: '🧠', label: 'Memory', desc: 'Persistent context across sessions', href: '/user-guide/features/memory' },
  { icon: '⚡', label: 'Skills', desc: 'Extend Sara with reusable skills', href: '/user-guide/features/skills' },
  { icon: '🔧', label: 'Integrations', desc: 'Connect to your tools and platforms', href: '/integrations' },
  { icon: '💬', label: 'Messaging', desc: 'Multi-platform messaging gateway', href: '/user-guide/messaging' },
  { icon: '🖥️', label: 'CLI', desc: 'Command-line interface reference', href: '/user-guide/cli' },
  { icon: '📖', label: 'User Stories', desc: 'See what others are building', href: '/user-stories' },
  { icon: '🎯', label: 'API Reference', desc: 'Complete API documentation', href: '/reference/cli-commands' },
];

function QuickLinkCard({ icon, label, desc, href, index }: typeof QUICK_LINKS[0] & { index: number }) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-40px' });

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 20 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.4, delay: index * 0.06, ease: [0.16, 1, 0.3, 1] }}
    >
      <Link to={href} className="sara-quick-link-card">
        <div className="sara-quick-link-icon">{icon}</div>
        <div className="sara-quick-link-name">{label}</div>
        <p className="sara-quick-link-desc">{desc}</p>
      </Link>
    </motion.div>
  );
}

function HeroSection() {
  const logoUrl = useBaseUrl('/img/logo.png');

  return (
    <section className="sara-hero">
      <div className="sara-hero-glow" />
      <div className="sara-hero-inner">
        <motion.div
          className="sara-hero-left"
          initial={{ opacity: 0, x: -30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        >
          <motion.div
            className="sara-hero-badge"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.4, delay: 0.1 }}
          >
            <span className="sara-hero-badge-dot" />
            Sara Agent v2.1.0
          </motion.div>

          <motion.h1
            className="sara-hero-title"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.15, ease: [0.16, 1, 0.3, 1] }}
          >
            The Self-Improving<br />
            <span>Autonomous AI Agent</span>
          </motion.h1>

          <motion.p
            className="sara-hero-subtitle"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.25, ease: [0.16, 1, 0.3, 1] }}
          >
            Build skills. Learn from experience. Remember everything. Evolve continuously.
          </motion.p>

          <motion.div
            className="sara-hero-cta"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.35, ease: [0.16, 1, 0.3, 1] }}
          >
            <Link to="/getting-started/quickstart" className="sara-hero-cta-primary">
              Get Started →
            </Link>
            <Link to="https://github.com/NexvisoraResearch/sara-agent" className="sara-hero-cta-secondary">
              GitHub ↗
            </Link>
          </motion.div>
        </motion.div>

        <motion.div
          className="sara-hero-right"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.7, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
        >
          <div className="sara-hero-logo-wrapper">
            <div className="sara-hero-logo-ring" />
            <div className="sara-hero-logo-ring" />
            <div className="sara-hero-logo-ring" />
            <img src={logoUrl} alt="Sara Agent" className="sara-hero-logo-img" />
          </div>
        </motion.div>
      </div>
    </section>
  );
}

function QuickLinksSection() {
  return (
    <section className="sara-quick-links">
      <motion.h2
        className="sara-quick-links-title"
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: '-60px' }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      >
        Everything you need to build with Sara
      </motion.h2>
      <div className="sara-quick-links-grid">
        {QUICK_LINKS.map((link, i) => (
          <QuickLinkCard key={link.label} {...link} index={i} />
        ))}
      </div>
    </section>
  );
}

export default function Home(): JSX.Element {
  const { siteConfig } = useDocusaurusContext();

  return (
    <Layout
      title="Home"
      description={siteConfig.tagline}
    >
      <HeroSection />
      <QuickLinksSection />
    </Layout>
  );
}
