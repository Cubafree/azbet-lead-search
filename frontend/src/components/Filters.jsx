const PLATFORMS = ['', 'telegram', 'youtube', 'instagram', 'tiktok', 'web']
const PRIORITIES = ['', 'high', 'medium', 'low']
const NICHES = ['', 'tipster', 'sports_betting', 'casino', 'mixed', 'sports_news']
const GEOS = ['', 'egypt', 'morocco', 'algeria', 'tunisia', 'libya', 'maghreb', 'mena']

export default function Filters({ filters, onChange }) {
  const set = (key) => (e) => onChange({ ...filters, [key]: e.target.value, offset: 0 })

  return (
    <div className="flex flex-wrap gap-2 mb-4 items-center">
      <input
        className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500 w-48"
        placeholder="Search name / handle…"
        value={filters.search || ''}
        onChange={set('search')}
      />
      <Select value={filters.platform}  onChange={set('platform')}  options={PLATFORMS} placeholder="Platform" />
      <Select value={filters.priority}  onChange={set('priority')}  options={PRIORITIES} placeholder="Priority" />
      <Select value={filters.niche}     onChange={set('niche')}     options={NICHES}    placeholder="Niche" />
      <Select value={filters.geo_focus} onChange={set('geo_focus')} options={GEOS}      placeholder="Geo" />

      {/* Archive toggle */}
      <button
        onClick={() => onChange({ ...filters, show_archived: !filters.show_archived, offset: 0 })}
        className={`flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg border transition-colors ${
          filters.show_archived
            ? 'bg-orange-900/40 border-orange-700 text-orange-300'
            : 'bg-gray-900 border-gray-700 text-gray-500 hover:text-gray-300'
        }`}
      >
        {filters.show_archived ? '📦 Archived' : '📦 Show archived'}
      </button>
    </div>
  )
}

function Select({ value, onChange, options, placeholder }) {
  return (
    <select
      className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
      value={value || ''}
      onChange={onChange}
    >
      <option value="">{placeholder}</option>
      {options.filter(Boolean).map(o => (
        <option key={o} value={o}>{o}</option>
      ))}
    </select>
  )
}
