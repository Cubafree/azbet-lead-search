import { useState } from 'react'
import { ExternalLink, Mail, MessageCircle, ChevronDown, ChevronUp, Archive, ArchiveRestore } from 'lucide-react'
import { api } from '../api/client'

const PRIORITY_BADGE = {
  high:   'bg-emerald-900 text-emerald-300 border-emerald-700',
  medium: 'bg-yellow-900 text-yellow-300 border-yellow-700',
  low:    'bg-gray-800 text-gray-400 border-gray-700',
}

const PLATFORM_ICON = {
  telegram:  '✈️',
  youtube:   '▶️',
  instagram: '📸',
  tiktok:    '🎵',
  web:       '🌐',
}

function fmt(n) {
  if (!n) return '—'
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(0) + 'K'
  return n.toLocaleString()
}

export default function ChannelTable({ items, total, filters, onFilterChange, onArchiveChange }) {
  const [expanded, setExpanded] = useState(null)
  const [archiving, setArchiving] = useState(null)

  async function toggleArchive(ch) {
    setArchiving(ch.id)
    try {
      if (ch.is_archived) {
        await api.unarchiveChannel(ch.id)
      } else {
        await api.archiveChannel(ch.id)
      }
      onArchiveChange?.()
    } finally {
      setArchiving(null)
    }
  }

  const page = Math.floor((filters.offset || 0) / (filters.limit || 50))
  const pageSize = filters.limit || 50
  const totalPages = Math.ceil(total / pageSize)

  return (
    <div>
      {/* Table header */}
      <div className="text-xs text-gray-500 mb-2">{total} channels found</div>

      <div className="rounded-xl border border-gray-800 overflow-hidden">
        {/* Header row */}
        <div className="grid grid-cols-[2fr_1fr_1fr_1fr_1fr_1fr_auto] gap-2 px-4 py-2 bg-gray-900 text-xs text-gray-500 border-b border-gray-800">
          <span>Channel</span>
          <span>Platform</span>
          <span>Followers</span>
          <span>Geo</span>
          <span>Niche</span>
          <span>Priority</span>
          <span className="w-6" />
        </div>

        {items.length === 0 && (
          <div className="px-4 py-8 text-center text-gray-600 text-sm">No channels yet</div>
        )}

        {items.map(ch => (
          <div key={ch.id}>
            {/* Main row */}
            <div
              className={`grid grid-cols-[2fr_1fr_1fr_1fr_1fr_1fr_auto] gap-2 px-4 py-3 border-b border-gray-800/60 hover:bg-gray-900/50 cursor-pointer items-center ${ch.is_archived ? 'opacity-50' : ''}`}
              onClick={() => setExpanded(expanded === ch.id ? null : ch.id)}
            >
              {/* Name + handle */}
              <div className="min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="font-medium text-sm text-gray-100 truncate">
                    {ch.name || ch.handle}
                  </span>
                  {ch.url && (
                    <a
                      href={ch.url}
                      target="_blank"
                      rel="noreferrer"
                      onClick={e => e.stopPropagation()}
                      className="text-gray-500 hover:text-blue-400 flex-shrink-0"
                    >
                      <ExternalLink size={12} />
                    </a>
                  )}
                </div>
                <div className="text-xs text-gray-500">@{ch.handle}</div>
              </div>

              <span className="text-sm">
                {PLATFORM_ICON[ch.platform] ?? '📌'} {ch.platform}
              </span>

              <span className="text-sm text-gray-300">
                {ch.platform === 'web' && ch.estimated_monthly_visits
                  ? <span title="Est. monthly visits">{fmt(ch.estimated_monthly_visits)}/mo</span>
                  : fmt(ch.followers)
                }
              </span>

              <span className="text-xs text-gray-400">{ch.geo_focus || '—'}</span>

              <span className="text-xs text-gray-400">{ch.niche || '—'}</span>

              <div className="flex items-center gap-2">
                <span className={`text-xs px-2 py-0.5 rounded-full border ${PRIORITY_BADGE[ch.priority] ?? PRIORITY_BADGE.low}`}>
                  {ch.priority || 'unrated'}
                </span>
                {expanded === ch.id
                  ? <ChevronUp size={14} className="text-gray-500" />
                  : <ChevronDown size={14} className="text-gray-500" />
                }
              </div>

              {/* Archive button */}
              <button
                onClick={e => { e.stopPropagation(); toggleArchive(ch) }}
                disabled={archiving === ch.id}
                title={ch.is_archived ? 'Unarchive' : 'Archive'}
                className={`flex-shrink-0 p-1 rounded transition-colors ${
                  ch.is_archived
                    ? 'text-orange-500 hover:text-orange-300'
                    : 'text-gray-600 hover:text-orange-400'
                } disabled:opacity-40`}
              >
                {ch.is_archived
                  ? <ArchiveRestore size={14} />
                  : <Archive size={14} />
                }
              </button>
            </div>

            {/* Expanded detail */}
            {expanded === ch.id && (
              <div className="px-6 py-4 bg-gray-900/70 border-b border-gray-800 grid md:grid-cols-2 gap-4 text-sm">
                {/* AI Summary */}
                {ch.ai_summary && (
                  <div className="md:col-span-2">
                    <p className="text-xs text-gray-500 mb-1">AI Summary</p>
                    <p className="text-gray-300">{ch.ai_summary}</p>
                  </div>
                )}

                {/* Description */}
                {ch.description && (
                  <div className="md:col-span-2">
                    <p className="text-xs text-gray-500 mb-1">Description</p>
                    <p className="text-gray-400 text-xs leading-relaxed">{ch.description}</p>
                  </div>
                )}

                {/* Contacts */}
                <div>
                  <p className="text-xs text-gray-500 mb-2">Contacts</p>
                  <div className="flex flex-wrap gap-2">
                    {ch.contact_email && (
                      <a href={`mailto:${ch.contact_email}`}
                        className="flex items-center gap-1 text-xs bg-gray-800 hover:bg-gray-700 px-2 py-1 rounded-lg text-blue-400">
                        <Mail size={11} /> {ch.contact_email}
                      </a>
                    )}
                    {ch.contact_telegram && (
                      <a href={`https://t.me/${ch.contact_telegram}`} target="_blank" rel="noreferrer"
                        className="flex items-center gap-1 text-xs bg-gray-800 hover:bg-gray-700 px-2 py-1 rounded-lg text-sky-400">
                        <MessageCircle size={11} /> @{ch.contact_telegram}
                      </a>
                    )}
                    {ch.contact_other && (
                      <a href={ch.contact_other} target="_blank" rel="noreferrer"
                        className="text-xs bg-gray-800 hover:bg-gray-700 px-2 py-1 rounded-lg text-gray-300">
                        {ch.contact_other}
                      </a>
                    )}
                    {!ch.contact_email && !ch.contact_telegram && !ch.contact_other && (
                      <span className="text-xs text-gray-600">No contacts found</span>
                    )}
                  </div>
                </div>

                {/* Traffic estimate (web only) */}
                {ch.platform === 'web' && ch.estimated_monthly_visits && (
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Est. Monthly Traffic</p>
                    <p className="text-sm text-teal-400 font-medium">{fmt(ch.estimated_monthly_visits)} visits/mo</p>
                  </div>
                )}

                {/* Traffic estimate (web only) */}
                {ch.platform === 'web' && ch.estimated_monthly_visits && (
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Est. Monthly Traffic</p>
                    <p className="text-sm text-teal-400 font-medium">{fmt(ch.estimated_monthly_visits)} visits/mo</p>
                  </div>
                )}

                {/* Competitor info */}
                <div>
                  <p className="text-xs text-gray-500 mb-2">Competitor signals</p>
                  {ch.mentioned_competitors
                    ? <p className="text-xs text-orange-400">{ch.mentioned_competitors}</p>
                    : <p className="text-xs text-gray-600">None detected</p>
                  }
                  {ch.competitor_promo && (
                    <p className="text-xs text-red-400 mt-1">Promo: {ch.competitor_promo}</p>
                  )}
                </div>

                {/* Outreach draft */}
                {ch.outreach_draft && (
                  <div className="md:col-span-2">
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-xs text-gray-500">Outreach Draft</p>
                      <button
                        onClick={() => navigator.clipboard.writeText(ch.outreach_draft)}
                        className="text-xs text-gray-500 hover:text-blue-400 transition-colors"
                      >
                        Copy
                      </button>
                    </div>
                    <pre className="text-xs text-gray-300 bg-gray-800/60 rounded-lg p-3 whitespace-pre-wrap font-sans leading-relaxed border border-gray-700/50">
                      {ch.outreach_draft}
                    </pre>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-2 mt-4">
          <button
            disabled={page === 0}
            onClick={() => onFilterChange({ ...filters, offset: (page - 1) * pageSize })}
            className="px-3 py-1.5 text-sm bg-gray-900 border border-gray-700 rounded-lg disabled:opacity-40 hover:bg-gray-800"
          >
            ← Prev
          </button>
          <span className="px-3 py-1.5 text-sm text-gray-400">
            {page + 1} / {totalPages}
          </span>
          <button
            disabled={page >= totalPages - 1}
            onClick={() => onFilterChange({ ...filters, offset: (page + 1) * pageSize })}
            className="px-3 py-1.5 text-sm bg-gray-900 border border-gray-700 rounded-lg disabled:opacity-40 hover:bg-gray-800"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  )
}
