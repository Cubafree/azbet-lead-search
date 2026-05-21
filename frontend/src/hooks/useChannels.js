import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'

export function useChannels(filters) {
  const [data, setData] = useState({ total: 0, items: [] })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.getChannels(filters)
      setData(res)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [JSON.stringify(filters)])

  useEffect(() => { fetch() }, [fetch])

  return { ...data, loading, error, refetch: fetch }
}

export function useStats() {
  const [stats, setStats] = useState(null)
  useEffect(() => {
    api.getStats().then(setStats).catch(() => {})
  }, [])
  return stats
}
