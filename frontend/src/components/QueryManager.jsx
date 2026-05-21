import { useState, useEffect } from 'react'
import { Plus, Trash2, RotateCcw } from 'lucide-react'
import { api } from '../api/client'

const SOURCE_TYPES = ['telegram', 'youtube', 'seo']
const GEOS = ['all', 'egypt', 'morocco', 'algeria', 'tunisia', 'libya']
const LANGS = ['en', 'ar', 'fr']

const STATUS_COLOR = {
  pending: 'text-yellow-400',
  done:    'text-emerald-400',
  running: 'text-blue-400',
  error:   'text-red-400',
}

export default function QueryManager() {
  const [queries, setQueries] = useState([])
  const [form, setForm] = useState({ query_text: '', source_type: 'telegram', geo: 'all', language: 'en' })
  const [loading, setLoading] = useState(false)

  const load = () => api.getQueries().then(setQueries).catch(() => {})
  useEffect(() => { load() }, [])

  async function add() {
    if (!form.query_text.trim()) return
    setLoading(true)
    try {
      await api.createQuery(form)
      setForm(f => ({ ...f, query_text: '' }))
      await load()
    } finally {
      setLoading(false)
    }
  }

  async function remove(id) {
    await api.deleteQuery(id)
    setQueries(q => q.filter(x => x.id !== id))
  }

  async function reset(id) {
    await api.resetQuery(id)
    await load()
  }

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
      <h2 className="text-sm font-semibold text-gray-300 mb-3">Search Queries</h2>

      {/* Add form */}
      <div className="flex flex-wrap gap-2 mb-4">
        <input
          className="flex-1 min-w-48 bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500"
          placeholder='e.g. "site:t.me betting tips egypt"'
          value={form.query_text}
          onChange={e => setForm(f => ({ ...f, query_text: e.target.value }))}
          onKeyDown={e => e.key === 'Enter' && add()}
        />
        <select
          className="bg-gray-800 border border-gray-700 rounded-lg px-2 py-1.5 text-sm text-gray-200 focus:outline-none"
          value={form.source_type}
          onChange={e => setForm(f => ({ ...f, source_type: e.target.value }))}
        >
          {SOURCE_TYPES.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <select
          className="bg-gray-800 border border-gray-700 rounded-lg px-2 py-1.5 text-sm text-gray-200 focus:outline-none"
          value={form.geo}
          onChange={e => setForm(f => ({ ...f, geo: e.target.value }))}
        >
          {GEOS.map(g => <option key={g} value={g}>{g}</option>)}
        </select>
        <select
          className="bg-gray-800 border border-gray-700 rounded-lg px-2 py-1.5 text-sm text-gray-200 focus:outline-none"
          value={form.language}
          onChange={e => setForm(f => ({ ...f, language: e.target.value }))}
        >
          {LANGS.map(l => <option key={l} value={l}>{l}</option>)}
        </select>
        <button
          onClick={add}
          disabled={loading || !form.query_text.trim()}
          className="flex items-center gap-1 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm px-3 py-1.5 rounded-lg"
        >
          <Plus size={14} /> Add
        </button>
      </div>

      {/* List */}
      <div className="space-y-1 max-h-64 overflow-y-auto">
        {queries.length === 0 && (
          <p className="text-xs text-gray-600 text-center py-4">No queries yet</p>
        )}
        {queries.map(q => (
          <div key={q.id} className="flex items-center gap-2 px-3 py-2 bg-gray-800/60 rounded-lg text-sm">
            <span className={`text-xs w-14 flex-shrink-0 ${STATUS_COLOR[q.status] ?? 'text-gray-400'}`}>
              {q.status}
            </span>
            <span className="text-gray-300 flex-1 truncate">{q.query_text}</span>
            <span className="text-xs text-gray-600 flex-shrink-0">{q.source_type} · {q.geo} · {q.language}</span>
            {q.result_count > 0 && (
              <span className="text-xs text-gray-500">{q.result_count} found</span>
            )}
            <button
              onClick={() => reset(q.id)}
              className="text-gray-600 hover:text-yellow-400 flex-shrink-0"
              title="Reset to pending"
            >
              <RotateCcw size={13} />
            </button>
            <button
              onClick={() => remove(q.id)}
              className="text-gray-600 hover:text-red-400 flex-shrink-0"
            >
              <Trash2 size={13} />
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
