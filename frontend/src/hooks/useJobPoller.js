import { useState, useEffect, useRef } from 'react'
import { api } from '../api/client'

export function useJobPoller(onComplete) {
  const [job, setJob] = useState(null)
  const intervalRef = useRef(null)

  const start = async (queries) => {
    const { job_id } = await api.runJob(queries)
    pollJob(job_id)
  }

  const pollJob = (jobId) => {
    intervalRef.current = setInterval(async () => {
      try {
        const data = await api.getJobStatus(jobId)
        setJob(data)
        if (data.status === 'done' || data.status === 'error') {
          clearInterval(intervalRef.current)
          onComplete?.()
        }
      } catch {
        clearInterval(intervalRef.current)
      }
    }, 2000)
  }

  // При маунте — проверяем есть ли незавершённый джоб
  useEffect(() => {
    api.getLatestJob().then((data) => {
      if (data?.status === 'running') {
        setJob(data)
        pollJob(data.id)
      }
    }).catch(() => {})

    return () => clearInterval(intervalRef.current)
  }, [])

  return { job, start, isRunning: job?.status === 'running' }
}
