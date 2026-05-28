import { useState, useCallback } from 'react'

const KEY = 'namibjobs_saved'

function load() {
  try { return JSON.parse(localStorage.getItem(KEY)) ?? [] }
  catch { return [] }
}

export function useSavedJobs() {
  const [saved, setSaved] = useState(load)

  const toggle = useCallback((job) => {
    setSaved(prev => {
      const exists = prev.some(j => j.id === job.id)
      const next = exists ? prev.filter(j => j.id !== job.id) : [...prev, job]
      localStorage.setItem(KEY, JSON.stringify(next))
      return next
    })
  }, [])

  const isSaved = useCallback((id) => saved.some(j => j.id === id), [saved])

  return { saved, toggle, isSaved }
}
