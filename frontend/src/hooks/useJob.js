import { useState, useEffect, useRef } from 'react'
import { api } from '../api/client'

export function useJob() {
  const [job, setJob] = useState(null)
  const [running, setRunning] = useState(false)
  const pollRef = useRef(null)

  // При монтировании — проверяем есть ли активный джоб
  useEffect(() => {
    api.getLatestJob().then(j => {
      if (j?.id && j.status === 'running') {
        setJob(j)
        setRunning(true)
        startPolling(j.id)
      }
    }).catch(() => {})
    return () => stopPolling()
  }, [])

  function startPolling(jobId) {
    stopPolling()
    pollRef.current = setInterval(async () => {
      try {
        const j = await api.getJobStatus(jobId)
        setJob(j)
        if (j.status !== 'running') {
          setRunning(false)
          stopPolling()
        }
      } catch {
        stopPolling()
        setRunning(false)
      }
    }, 2000)
  }

  function stopPolling() {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }

  async function triggerJob(queries = null) {
    setRunning(true)
    setJob({ status: 'running', phase: 'searching', processed: 0, total: 0, new_found: 0 })
    try {
      const { job_id } = await api.runJob(queries)
      startPolling(job_id)
    } catch (e) {
      setRunning(false)
      setJob(null)
      throw e
    }
  }

  async function triggerAgent(geo = 'all') {
    setRunning(true)
    setJob({ status: 'running', phase: 'generating_queries', processed: 0, total: 0, new_found: 0 })
    try {
      const { job_id } = await api.runAgent(geo)
      startPolling(job_id)
    } catch (e) {
      setRunning(false)
      setJob(null)
      throw e
    }
  }

  return { job, running, triggerJob, triggerAgent }
}
