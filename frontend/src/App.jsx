import { useState } from 'react'
import { Bot, RefreshCw, Zap, Sparkles } from 'lucide-react'
import { api } from './api/client'
import StatCards from './components/StatCards'
import JobBar from './components/JobBar'
import Filters from './components/Filters'
import ChannelTable from './components/ChannelTable'
import QueryManager from './components/QueryManager'
import { useChannels } from './hooks/useChannels'
import { useJob } from './hooks/useJob'

const GEOS = ['all', 'egypt', 'morocco', 'algeria', 'tunisia', 'libya']
const DEFAULT_FILTERS = { limit: 50, offset: 0 }

const PHASE_LABEL = {
  generating_queries: '🤖 Generating queries…',
  searching:          '🔍 Searching…',
  enriching:          '⚡ Enriching channels…',
  qualifying:         '🧠 AI qualifying…',
  done:               '✅ Done',
}

export default function App() {
  const [filters, setFilters] = useState(DEFAULT_FILTERS)
  const [tab, setTab] = useState('leads')
  const [agentGeo, setAgentGeo] = useState('all')
  const [enriching, setEnriching] = useState(false)
  const [enrichJob, setEnrichJob] = useState(null)

  const { items, total, loading, refetch } = useChannels(filters)
  const { job, running, triggerAgent } = useJob()

  async function handleRunAgent() {
    try {
      await triggerAgent(agentGeo)
    } catch (e) {
      alert(`Failed to start agent: ${e.message}`)
    }
  }

  async function handleEnrich() {
    setEnriching(true)
    try {
      const { job_id } = await api.runEnrich()
      setEnrichJob({ id: job_id, status: 'running' })
      // Poll until done
      const poll = setInterval(async () => {
        try {
          const j = await api.getJobStatus(job_id)
          setEnrichJob(j)
          if (j.status !== 'running') {
            clearInterval(poll)
            setEnriching(false)
            if (j.status === 'done') refetch()
          }
        } catch { clearInterval(poll); setEnriching(false) }
      }, 2500)
    } catch (e) {
      setEnriching(false)
      alert(`Enrich failed: ${e.message}`)
    }
  }

  return (
    <div className="min-h-screen bg-gray-950">
      <div className="max-w-7xl mx-auto px-4 py-6">

        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div>
            <h1 className="text-xl font-bold text-white">AzBet Lead Search</h1>
            <p className="text-xs text-gray-500 mt-0.5">Affiliate channel discovery · MENA</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleEnrich}
              disabled={enriching || running}
              title="Deep contact search + generate email drafts for non-archived leads without contacts"
              className="flex items-center gap-1.5 px-3 py-2 text-sm bg-violet-700 hover:bg-violet-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg font-medium"
            >
              <Sparkles size={14} />
              {enriching
                ? `Enriching… ${enrichJob?.processed ?? 0}/${enrichJob?.total ?? '?'}`
                : 'Enrich Leads'}
            </button>
            <button
              onClick={refetch}
              className="flex items-center gap-1.5 px-3 py-2 text-sm bg-gray-800 hover:bg-gray-700 border border-gray-700 text-gray-300 rounded-lg"
            >
              <RefreshCw size={14} /> Refresh
            </button>
          </div>
        </div>

        {/* Agent Control Panel */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 mb-5">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2 flex-1 min-w-0">
              <Bot size={20} className="text-indigo-400 flex-shrink-0" />
              <div className="min-w-0">
                <p className="text-sm font-semibold text-white">Autonomous Agent</p>
                <p className="text-xs text-gray-500 truncate">
                  Generates queries · searches all sources · filters MENA · drafts outreach emails
                </p>
              </div>
            </div>

            <select
              value={agentGeo}
              onChange={e => setAgentGeo(e.target.value)}
              disabled={running}
              className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none disabled:opacity-50"
            >
              {GEOS.map(g => <option key={g} value={g}>{g === 'all' ? '🌍 All MENA' : g.charAt(0).toUpperCase() + g.slice(1)}</option>)}
            </select>

            <button
              onClick={handleRunAgent}
              disabled={running}
              className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium px-5 py-2 rounded-lg transition-colors"
            >
              <Zap size={15} />
              {running ? 'Agent running…' : 'Run Agent'}
            </button>
          </div>

          {/* Live status */}
          {job && (
            <div className="mt-3 pt-3 border-t border-gray-800 flex items-center gap-3 text-xs text-gray-400">
              <span className={`font-medium ${job.status === 'done' ? 'text-emerald-400' : job.status === 'error' ? 'text-red-400' : 'text-indigo-400'}`}>
                {PHASE_LABEL[job.phase] ?? job.phase ?? job.status}
              </span>
              {job.total > 0 && (
                <span>{job.processed}/{job.total}</span>
              )}
              {job.new_found > 0 && (
                <span className="text-emerald-400 font-medium">+{job.new_found} new leads</span>
              )}
              {job.status === 'done' && (
                <button onClick={refetch} className="text-blue-400 hover:text-blue-300 underline ml-auto">
                  Refresh table
                </button>
              )}
              {job.error_msg && (
                <span className="text-red-400 truncate">{job.error_msg}</span>
              )}
            </div>
          )}
        </div>

        {/* Job progress bar */}
        <JobBar job={job} />

        {/* Tabs */}
        <div className="flex gap-1 mb-5 border-b border-gray-800">
          {[['leads', 'Leads'], ['queries', 'Query Manager']].map(([key, label]) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`px-4 py-2 text-sm border-b-2 -mb-px transition-colors ${
                tab === key
                  ? 'border-blue-500 text-white font-medium'
                  : 'border-transparent text-gray-500 hover:text-gray-300'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {tab === 'leads' && (
          <>
            <StatCards />
            <Filters filters={filters} onChange={setFilters} />
            {loading
              ? <div className="text-center py-16 text-gray-600 text-sm">Loading…</div>
              : <ChannelTable
                  items={items}
                  total={total}
                  filters={filters}
                  onFilterChange={setFilters}
                  onArchiveChange={refetch}
                />
            }
          </>
        )}

        {tab === 'queries' && <QueryManager />}
      </div>
    </div>
  )
}
