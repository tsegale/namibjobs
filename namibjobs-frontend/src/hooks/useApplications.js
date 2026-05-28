import { useState, useCallback } from 'react'

const KEY = 'namibjobs_applications'

function load() {
  try { return JSON.parse(localStorage.getItem(KEY)) ?? [] }
  catch { return [] }
}

export function useApplications() {
  const [applications, setApplications] = useState(load)

  const apply = useCallback((job) => {
    setApplications(prev => {
      if (prev.some(a => a.id === job.id)) return prev
      const next = [...prev, { ...job, appliedAt: new Date().toISOString() }]
      localStorage.setItem(KEY, JSON.stringify(next))
      return next
    })
  }, [])

  const hasApplied = useCallback((id) => applications.some(a => a.id === id), [applications])

  return { applications, apply, hasApplied }
}
