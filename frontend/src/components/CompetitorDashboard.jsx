import { useState, useEffect, useCallback } from 'react'
import { ExternalLink, Zap, AlertTriangle, TrendingUp, Lightbulb, RefreshCw, Users, Shield } from 'lucide-react'
import { api } from '../api/client'

const SIGNAL_ICON = {
  new_affiliate:  { icon: '👤', color: 'text-sky-400' },
  new_promo:      { icon: '🎁', color: 'text-yellow-400' },
  lead_switched:  { icon: '⚠️', color: 'text-red-400' },
  growth:         { icon: '📈', color: 'text-emerald-400' },
  new_geo:        { icon: '🌍', color: 'text-purple-400' },
}

const INSIGHT_ICON = {
  opportunity: <Lightbulb size={14} className="text-emerald-400 flex-shrink-0" />,
  threat:      <AlertTriangle size={14} className="text-red-400 flex-shrink-0" />,
  trend:       <TrendingUp size={14} className="text-sky-400 flex-shrink-0" />,
  action:      <Zap size={14} className="text-yellow-400 flex-shrink-0" />,
}

const PRIORITY_DOT = {
  high:   'bg-red-500',
  medium: 'bg-yellow-500',
  low:    'bg-gray-600',
}

function fmt(n) {
  if (!n) return '—'
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(0) + 'K'
  return String(n)
}

function timeAgo(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const mins = Math.floor((Date.now() - d) / 60000)
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

// ── Sub-views ──────────────────────────────────────────────────────────────

function CompetitorCard({ comp, onClick, selected }) {
  return (
    <button
      onClick={onClick}
      className={`text-left p-4 rounded-xl border transition-colors ${
        selected
          ? 'bg-indigo-950 border-indigo-700'
          : 'bg-gray-900 border-gray-800 hover:border-gray-700'
      }`}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="font-semibold text-white">{comp.display_name || comp.name}</span>
        {comp.last_scanned_at
          ? <span className="text-xs text-gray-600">{timeAgo(comp.last_scanned_at)}</span>
          : <span className="text-xs text-gray-700">never scanned</span>
        }
      </div>
      <div className="flex gap-4 text-xs text-gray-400">
        <span title="Known affiliates"><Users size={11} className="inline mr-0.5" />{comp.affiliate_count ?? 0}</span>
        <span title="Our leads that promote them"><Shield size={11} className="inline mr-0.5" />{comp.our_overlap ?? 0} overlap</span>
        <span title="Signals last 30d" className={comp.signals_30d > 0 ? 'text-yellow-400' : ''}>
          ⚡ {comp.signals_30d ?? 0} signals
        </span>
      </div>
    </button>
  )
}

function SignalFeed({ signals }) {
  if (!signals?.length) return (
    <p className="text-sm text-gray-600 py-4">No signals yet — run a scan first.</p>
  )
  return (
    <div className="space-y-2">
      {signals.map(s => {
        const meta = SIGNAL_ICON[s.signal_type] || { icon: '📌', color: 'text-gray-400' }
        return (
          <div key={s.id} className="flex gap-3 p-3 bg-gray-900/60 rounded-lg border border-gray-800">
            <span className="text-base flex-shrink-0">{meta.icon}</span>
            <div className="min-w-0 flex-1">
              <p className={`text-xs font-medium ${meta.color}`}>{s.signal_type.replace('_', ' ')}</p>
              <p className="text-sm text-gray-300 mt-0.5">{s.description}</p>
              {s.geo && <span className="text-xs text-gray-600">{s.geo}</span>}
            </div>
            <span className="text-xs text-gray-600 flex-shrink-0">{timeAgo(s.created_at)}</span>
          </div>
        )
      })}
    </div>
  )
}

function OverlapTable({ channels, aiNote }) {
  if (!channels?.length) return (
    <p className="text-sm text-gray-600 py-4">No overlap found — none of your leads promote competitors yet.</p>
  )
  return (
    <div>
      {aiNote && (
        <div className="mb-4 p-3 bg-indigo-950/50 border border-indigo-800 rounded-xl text-sm text-gray-300 leading-relaxed">
          <p className="text-xs text-indigo-400 mb-1 font-medium">AI Strategic Note</p>
          {aiNote}
        </div>
      )}
      <div className="rounded-xl border border-gray-800 overflow-hidden">
        <div className="grid grid-cols-[2fr_1fr_1fr_1fr_2fr] gap-2 px-4 py-2 bg-gray-900 text-xs text-gray-500 border-b border-gray-800">
          <span>Channel</span><span>Platform</span><span>Followers</span><span>Priority</span><span>Competitor</span>
        </div>
        {channels.map(ch => (
          <div key={ch.id} className="grid grid-cols-[2fr_1fr_1fr_1fr_2fr] gap-2 px-4 py-3 border-b border-gray-800/60 text-sm items-center">
            <div>
              <span className="text-gray-200 font-medium">{ch.name || ch.handle}</span>
              <div className="text-xs text-gray-500">@{ch.handle}</div>
            </div>
            <span className="text-gray-400">{ch.platform}</span>
            <span className="text-gray-300">{fmt(ch.followers)}</span>
            <span>
              <span className={`inline-block w-2 h-2 rounded-full mr-1 ${PRIORITY_DOT[ch.priority] ?? 'bg-gray-700'}`} />
              <span className="text-xs text-gray-400">{ch.priority || '—'}</span>
            </span>
            <span className="text-xs text-orange-400">
              {ch.mentioned_competitors}
              {ch.competitor_promo && <span className="ml-1 text-red-400">({ch.competitor_promo})</span>}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

function InsightsList({ insights }) {
  if (!insights?.length) return (
    <p className="text-sm text-gray-600 py-4">No insights yet — need at least one scan first.</p>
  )
  return (
    <div className="space-y-3">
      {insights.map((ins, i) => (
        <div key={i} className="p-4 bg-gray-900 rounded-xl border border-gray-800">
          <div className="flex items-start gap-2 mb-2">
            {INSIGHT_ICON[ins.type] || <Zap size={14} className="text-gray-400" />}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-semibold text-white text-sm">{ins.title}</span>
                {ins.geo && ins.geo !== 'all' && (
                  <span className="text-xs bg-gray-800 text-gray-400 px-2 py-0.5 rounded-full">{ins.geo}</span>
                )}
                <span className={`text-xs px-2 py-0.5 rounded-full border ${
                  ins.priority === 'high' ? 'border-red-800 text-red-400 bg-red-950/30' :
                  ins.priority === 'medium' ? 'border-yellow-800 text-yellow-400 bg-yellow-950/30' :
                  'border-gray-700 text-gray-500'
                }`}>{ins.priority}</span>
              </div>
              <p className="text-sm text-gray-400 mt-1 leading-relaxed">{ins.body}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Main dashboard ─────────────────────────────────────────────────────────

export default function CompetitorDashboard() {
  const [competitors, setCompetitors] = useState([])
  const [selected, setSelected] = useState(null)   // competitor name
  const [tab, setTab] = useState('signals')         // signals | overlap | insights
  const [signals, setSignals] = useState([])
  const [overlap, setOverlap] = useState({ channels: [], ai_note: '' })
  const [insights, setInsights] = useState([])
  const [loadingInsights, setLoadingInsights] = useState(false)
  const [scanning, setScanning] = useState(false)
  const [scanStatus, setScanStatus] = useState(null)
  const [loading, setLoading] = useState(true)

  const loadCompetitors = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.getCompetitors()
      setCompetitors(data)
      if (!selected && data.length) setSelected(data[0].name)
    } finally {
      setLoading(false)
    }
  }, [selected])

  useEffect(() => { loadCompetitors() }, [])

  // Load signals when selected competitor changes
  useEffect(() => {
    if (!selected) return
    api.getCompetitorSignals(selected, 30).then(setSignals).catch(() => {})
  }, [selected])

  // Load overlap (not per-competitor — global)
  useEffect(() => {
    if (tab !== 'overlap') return
    api.getCompetitorOverlap().then(setOverlap).catch(() => {})
  }, [tab])

  async function loadInsights() {
    setLoadingInsights(true)
    try {
      const data = await api.getCompetitorInsights()
      setInsights(data.insights || [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoadingInsights(false)
    }
  }

  useEffect(() => {
    if (tab === 'insights' && !insights.length) loadInsights()
  }, [tab])

  async function handleScan(competitorName = null) {
    setScanning(true)
    setScanStatus(competitorName ? `Scanning ${competitorName}…` : 'Scanning all…')
    try {
      const r = await api.scanCompetitors('all', competitorName)
      setScanStatus(`✅ Job started: ${r.job_id?.slice(0, 8)}`)
      setTimeout(() => {
        setScanStatus(null)
        loadCompetitors()
      }, 3000)
    } catch (e) {
      setScanStatus(`❌ ${e.message}`)
    } finally {
      setScanning(false)
    }
  }

  const tabs = [
    ['signals', 'Signals'],
    ['overlap', 'Overlap'],
    ['insights', 'AI Insights'],
  ]

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h2 className="text-lg font-semibold text-white">Competitor Intelligence</h2>
          <p className="text-xs text-gray-500 mt-0.5">MENA affiliate activity · promo codes · discovered lead candidates · <span title="6 competitors × 2 geos × 1 lang × 2 query types">24 Serper credits/scan</span></p>
        </div>
        <div className="flex items-center gap-2">
          {scanStatus && <span className="text-xs text-gray-400">{scanStatus}</span>}
          {selected && (
            <button
              onClick={() => handleScan(selected)}
              disabled={scanning}
              title={`Scan only ${selected}`}
              className="flex items-center gap-1.5 px-3 py-2 text-sm bg-gray-800 hover:bg-gray-700 disabled:opacity-50 border border-gray-700 text-gray-300 rounded-lg transition-colors"
            >
              <RefreshCw size={13} className={scanning ? 'animate-spin' : ''} />
              Scan {selected}
            </button>
          )}
          <button
            onClick={() => handleScan(null)}
            disabled={scanning}
            title="Scan all 6 competitors"
            className="flex items-center gap-1.5 px-4 py-2 text-sm bg-indigo-700 hover:bg-indigo-600 disabled:opacity-50 text-white rounded-lg transition-colors"
          >
            <RefreshCw size={13} className={scanning ? 'animate-spin' : ''} />
            {scanning ? 'Scanning…' : 'Scan all'}
          </button>
        </div>
      </div>

      {/* Competitor grid */}
      {loading ? (
        <div className="text-center py-8 text-gray-600 text-sm">Loading…</div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2 mb-6">
          {competitors.map(comp => (
            <CompetitorCard
              key={comp.name}
              comp={comp}
              selected={selected === comp.name}
              onClick={() => setSelected(comp.name)}
            />
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 mb-4 border-b border-gray-800">
        {tabs.map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`px-4 py-2 text-sm border-b-2 -mb-px transition-colors ${
              tab === key
                ? 'border-indigo-500 text-white font-medium'
                : 'border-transparent text-gray-500 hover:text-gray-300'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div>
        {tab === 'signals' && (
          <div>
            <p className="text-xs text-gray-500 mb-3">
              Last 30 days · {selected && <span className="text-indigo-400">{selected}</span>}
            </p>
            <SignalFeed signals={signals} />
          </div>
        )}

        {tab === 'overlap' && (
          <div>
            <p className="text-xs text-gray-500 mb-3">
              Discovered candidates in your DB that are already promoting competitors — not yet contacted, sorted by priority
            </p>
            <OverlapTable channels={overlap.channels} aiNote={overlap.ai_note} />
          </div>
        )}

        {tab === 'insights' && (
          <div>
            <div className="flex items-center justify-between mb-3">
              <p className="text-xs text-gray-500">AI-generated competitive intelligence</p>
              <button
                onClick={loadInsights}
                disabled={loadingInsights}
                className="text-xs text-indigo-400 hover:text-indigo-300 disabled:opacity-50"
              >
                {loadingInsights ? 'Generating…' : '↻ Regenerate'}
              </button>
            </div>
            {loadingInsights
              ? <div className="text-center py-8 text-gray-600 text-sm">Generating insights…</div>
              : <InsightsList insights={insights} />
            }
          </div>
        )}
      </div>
    </div>
  )
}
