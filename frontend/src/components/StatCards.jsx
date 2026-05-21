import { useStats } from '../hooks/useChannels'

const PLATFORM_EMOJI = {
  telegram: '✈️',
  youtube: '▶️',
  instagram: '📸',
  tiktok: '🎵',
  web: '🌐',
}

const PRIORITY_COLOR = {
  high: 'text-emerald-400',
  medium: 'text-yellow-400',
  low: 'text-gray-400',
}

export default function StatCards() {
  const stats = useStats()
  if (!stats) return null

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
      <Card label="Total leads" value={stats.total} />
      {stats.by_priority.map(r => (
        <Card
          key={r.priority}
          label={`${r.priority ?? 'unrated'} priority`}
          value={r.cnt}
          valueClass={PRIORITY_COLOR[r.priority] ?? 'text-gray-400'}
        />
      ))}
      <div className="col-span-2 md:col-span-4 bg-gray-900 rounded-xl p-4 border border-gray-800">
        <p className="text-xs text-gray-500 mb-2">By platform</p>
        <div className="flex flex-wrap gap-3">
          {stats.by_platform.map(r => (
            <span key={r.platform} className="text-sm text-gray-300">
              {PLATFORM_EMOJI[r.platform] ?? '📌'} <span className="font-medium">{r.platform}</span>{' '}
              <span className="text-gray-500">{r.cnt}</span>
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}

function Card({ label, value, valueClass = 'text-white' }) {
  return (
    <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className={`text-2xl font-bold ${valueClass}`}>{value ?? '—'}</p>
    </div>
  )
}
