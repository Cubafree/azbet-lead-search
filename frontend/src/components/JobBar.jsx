const PHASE_LABEL = {
  searching: 'Searching…',
  parsing: 'Parsing results…',
  enriching: 'Enriching channels…',
  qualifying: 'AI qualifying…',
  done: 'Done',
  error: 'Error',
}

export default function JobBar({ job }) {
  if (!job) return null

  const pct = job.total > 0 ? Math.round((job.processed / job.total) * 100) : 0
  const isDone = job.status === 'done'
  const isError = job.status === 'error'

  return (
    <div className={`rounded-xl p-4 border mb-4 ${
      isError ? 'bg-red-950 border-red-800' :
      isDone  ? 'bg-emerald-950 border-emerald-800' :
                'bg-blue-950 border-blue-800'
    }`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {!isDone && !isError && (
            <span className="inline-block w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
          )}
          <span className="text-sm font-medium">
            {isError ? `Error: ${job.error_msg}` : PHASE_LABEL[job.phase] ?? job.phase}
          </span>
        </div>
        <div className="flex gap-4 text-xs text-gray-400">
          {job.total > 0 && (
            <span>{job.processed}/{job.total} queries</span>
          )}
          {job.new_found > 0 && (
            <span className="text-emerald-400">+{job.new_found} new</span>
          )}
        </div>
      </div>

      {job.total > 0 && !isDone && (
        <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-500 rounded-full transition-all duration-500"
            style={{ width: `${pct}%` }}
          />
        </div>
      )}

      {isDone && (
        <p className="text-xs text-emerald-400">
          ✓ Completed — found {job.new_found} new channels
        </p>
      )}
    </div>
  )
}
