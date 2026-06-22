import { useCallback, useEffect, useState } from 'react'

import { PageLoader } from '@/components/page-loader'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { TextTab, TextTabMeta } from '@/components/ui/text-tab'
import { getMemoryConversations, getMemoryEntries, getMemoryGraph, getMemoryProfile } from '@/Sara'
import { useI18n } from '@/i18n'
import { cn } from '@/lib/utils'
import type { ConversationSummary, MemoryEntry, MemoryGraphResponse, MemoryProfileResponse } from '@/types/Sara'

import { useRefreshHotkey } from '../hooks/use-refresh-hotkey'
import { PAGE_INSET_X } from '../layout-constants'
import { PageSearchShell } from '../page-search-shell'
import type { SetStatusbarItemGroup } from '../shell/statusbar-controls'

const MEMORY_TABS = ['graph', 'entries', 'profile', 'conversations'] as const
type MemoryTab = (typeof MEMORY_TABS)[number]

interface MemoryViewProps {
  setStatusbarItemGroup?: SetStatusbarItemGroup
}

export function MemoryView({ setStatusbarItemGroup }: MemoryViewProps) {
  const { t } = useI18n()
  const [tab, setTab] = useState<MemoryTab>('graph')
  const [graph, setGraph] = useState<MemoryGraphResponse | null>(null)
  const [entries, setEntries] = useState<MemoryEntry[]>([])
  const [profiles, setProfiles] = useState<MemoryProfileResponse | null>(null)
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchAll = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [graphRes, entriesRes, profileRes, convRes] = await Promise.all([
        getMemoryGraph(),
        getMemoryEntries(50),
        getMemoryProfile(),
        getMemoryConversations(50),
      ])
      setGraph(graphRes)
      setEntries(entriesRes.entries)
      setProfiles(profileRes)
      setConversations(convRes.conversations)
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchAll() }, [fetchAll])
  useRefreshHotkey(fetchAll)

  const tabs: TextTabMeta<MemoryTab>[] = MEMORY_TABS.map(id => ({
    id,
    label: id.charAt(0).toUpperCase() + id.slice(1),
  }))

  return (
    <div className="flex h-full flex-col">
      <header className={cn('flex items-center gap-3 py-3', PAGE_INSET_X)}>
        <Codicon name="database" className="size-5 shrink-0 text-accent-foreground" />
        <h1 className="text-lg font-semibold">Memory</h1>
        <div className="flex-1" />
        <Button variant="ghost" size="sm" onClick={fetchAll} disabled={loading}>
          <Codicon name="refresh" className={cn('size-4', loading && 'animate-spin')} />
        </Button>
      </header>

      <TextTab value={tab} onChange={setTab} items={tabs} className={PAGE_INSET_X} />

      <div className="flex-1 overflow-y-auto">
        {loading && !graph ? (
          <PageLoader />
        ) : error ? (
          <div className="p-6 text-danger">{error}</div>
        ) : tab === 'graph' ? (
          <GraphPanel graph={graph} />
        ) : tab === 'entries' ? (
          <EntriesPanel entries={entries} />
        ) : tab === 'profile' ? (
          <ProfilePanel profiles={profiles} />
        ) : (
          <ConversationsPanel conversations={conversations} />
        )}
      </div>
    </div>
  )
}

// ── Graph panel ─────────────────────────────────────────────────────────────

function GraphPanel({ graph }: { graph: MemoryGraphResponse | null }) {
  const nodes = graph?.graph?.nodes ?? []
  const edges = graph?.graph?.edges ?? []

  if (!nodes.length) {
    return (
      <div className="flex flex-col items-center gap-3 p-12 text-muted-foreground">
        <Codicon name="info" className="size-10" />
        <p className="text-sm">No graph data yet. Start a conversation to build your memory graph.</p>
      </div>
    )
  }

  return (
    <div className={cn('space-y-4 py-4', PAGE_INSET_X)}>
      <div className="flex items-center gap-3">
        <Badge variant="outline">{nodes.length} nodes</Badge>
        <Badge variant="outline">{edges.length} edges</Badge>
      </div>

      <div className="space-y-1">
        <p className="text-xs font-medium text-muted-foreground">Nodes</p>
        <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-3 md:grid-cols-4">
          {nodes.map(n => (
            <div
              key={n.id}
              className="truncate rounded border bg-card px-2 py-1 text-xs"
              title={`${n.label} (${n.type})`}
            >
              <span className="text-muted-foreground">{n.type}: </span>
              {n.label}
            </div>
          ))}
        </div>
      </div>

      <div className="space-y-1">
        <p className="text-xs font-medium text-muted-foreground">Edges</p>
        <div className="space-y-0.5">
          {edges.map((e, i) => (
            <div key={i} className="truncate rounded border bg-card px-2 py-1 text-xs">
              {e.source} <span className="text-accent-foreground">&mdash;{e.predicate}&rarr;</span> {e.target}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Entries panel ───────────────────────────────────────────────────────────

function EntriesPanel({ entries }: { entries: MemoryEntry[] }) {
  if (!entries.length) {
    return (
      <div className="flex flex-col items-center gap-3 p-12 text-muted-foreground">
        <Codicon name="note" className="size-10" />
        <p className="text-sm">No memory entries yet. Memories are created when the agent writes notes.</p>
      </div>
    )
  }

  return (
    <div className={cn('space-y-3 py-4', PAGE_INSET_X)}>
      {entries.map(e => (
        <div key={e.id} className="rounded-lg border bg-card p-3">
          <div className="mb-1 flex items-center gap-2">
            <Badge variant="secondary" className="text-[10px]">{e.source}</Badge>
            <span className="text-[10px] text-muted-foreground">{e.char_count} chars</span>
          </div>
          <p className="whitespace-pre-wrap break-words text-sm">{e.content.slice(0, 500)}</p>
          {e.content.length > 500 && (
            <p className="mt-1 text-[10px] text-muted-foreground">...truncated</p>
          )}
        </div>
      ))}
    </div>
  )
}

// ── Profile panel ───────────────────────────────────────────────────────────

function ProfilePanel({ profiles }: { profiles: MemoryProfileResponse | null }) {
  const list = profiles?.profiles ?? []

  if (!list.length) {
    return (
      <div className="flex flex-col items-center gap-3 p-12 text-muted-foreground">
        <Codicon name="person" className="size-10" />
        <p className="text-sm">No profile data yet.</p>
      </div>
    )
  }

  return (
    <div className={cn('space-y-3 py-4', PAGE_INSET_X)}>
      {list.map((p, i) => (
        <div key={i} className="rounded-lg border bg-card p-3">
          <pre className="overflow-x-auto text-xs">{JSON.stringify(p, null, 2)}</pre>
        </div>
      ))}
    </div>
  )
}

// ── Conversations panel ─────────────────────────────────────────────────────

function ConversationsPanel({ conversations }: { conversations: ConversationSummary[] }) {
  if (!conversations.length) {
    return (
      <div className="flex flex-col items-center gap-3 p-12 text-muted-foreground">
        <Codicon name="comment" className="size-10" />
        <p className="text-sm">No conversations yet.</p>
      </div>
    )
  }

  return (
    <div className={cn('space-y-2 py-4', PAGE_INSET_X)}>
      {conversations.map(c => (
        <div key={c.id} className="rounded-lg border bg-card p-3">
          <div className="flex items-center gap-2">
            <span className="flex-1 truncate text-sm font-medium">{c.preview || c.file}</span>
            <Badge variant="outline" className="text-[10px]">{c.message_count} msgs</Badge>
          </div>
          {c.updated_at && (
            <p className="mt-0.5 text-[10px] text-muted-foreground">{c.updated_at}</p>
          )}
        </div>
      ))}
    </div>
  )
}
