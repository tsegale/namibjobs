import { useState, useEffect } from 'react'
import api from '../api'

export function useJobs(filters = {}) {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoading(true)
    api.get('/jobs', { params: filters })
      .then(res => setJobs(res.data))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [filters.location, filters.job_type])

  return { jobs, loading, error }
}
