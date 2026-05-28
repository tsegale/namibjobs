import { useState, useEffect } from 'react'
import api from '../api'

export function useJobs() {
  const [jobs, setJobs]       = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    api.get('/jobs', { params: { limit: 200 } })
      .then(res => setJobs(res.data))
      .catch(err => setError(err.message ?? 'Failed to fetch jobs'))
      .finally(() => setLoading(false))
  }, [])

  return { jobs, loading, error }
}
