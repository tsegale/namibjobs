import { useState } from 'react'
import api from '../api'

export function useRecommend() {
  const [results, setResults]   = useState(null)   // null = not yet searched
  const [loading, setLoading]   = useState(false)
  const [error,   setError]     = useState(null)

  async function recommend(profileText) {
    setLoading(true)
    setError(null)
    try {
      const res = await api.post('/recommend', { profile_text: profileText })
      setResults(res.data)
    } catch (err) {
      setError(err.response?.data?.detail ?? err.message ?? 'Request failed')
      setResults(null)
    } finally {
      setLoading(false)
    }
  }

  return { results, loading, error, recommend }
}
