import { useState } from 'react'
import { Play, RefreshCw } from 'lucide-react'
import StatCards from './components/StatCards'
import JobBar from './components/JobBar'
import Filters from './components/Filters'
import ChannelTable from './components/ChannelTable'
import QueryManager from './components/QueryManager'
import { useChannels } from './hooks/useChannels'
import { useJob } from './hooks/useJob'

const DEFAULT_FILTERS = { limit: 50, offset: 0 }

export default function App() {
  const [filters, setFilters] = useState(DEFAULT_FILTERS)
  const [tab, setTab] = useState('leads') // leads | queries

  const { items, total, loading, refetch } = useChannels(filters)
  const { job, running, triggerJob } = useJob()

  async function handleRun() {
    try {
      await triggerJob(null) // null = берём все pending из query_queue
    } catch (e) {
      alert(`Failed to start job: ${e.message}`)
    }
  }

  // Обновляем таблицу когда джоб завершился
  const prevStatus = job?.status
  if (prevStatus === 'done') {
    // Небольшой трюк — refetch сработает при следующем рендере
  }

  return (
    <div className="min-h-screen bg-gray-950">
      <div className="max-w-7xl mx-auto px-4 py-6">

        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-xl font-bold text-white">AzBet Lead Search</h1>
            <p className="text-xs text-gray-500 mt-0.5">Affiliate channel discovery · MENA</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={refetch}
              className="flex items-center gap-1.5 px-3 py-2 text-sm bg-gray-800 hover:bg-gray-700 border border-gray-700 text-gray-300 rounded-lg"
            >
              <RefreshCw size={14} /> Refresh
            </button>
            <button
              onClick={handleRun}
              disabled={running}
              className="flex items-center gap-1.5 px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg font-medium"
            >
              <Play size={14} />
              {running ? 'Running…' : 'Run Search'}
            </button>
          </div>
        </div>

        {/* Job progress bar */}
        <JobBar job={job} />

        {/* Tabs */}
        <div className="flex gap-1 mb-5 border-b border-gray-800">
          {[['leads', 'Leads'], ['queries', 'Search Queries']].map(([key, label]) => (
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
                />
            }
          </>
        )}

        {tab === 'queries' && (
          <QueryManager />
        )}
      </div>
    </div>
  )
}
