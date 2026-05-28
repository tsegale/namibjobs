import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useJobs } from '../hooks/useJobs'
import { avatarColor, initials } from '../utils/company'

function ArrowIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" />
    </svg>
  )
}

function BuildingIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
      <polyline points="9 22 9 12 15 12 15 22" />
    </svg>
  )
}

function Spinner() {
  return (
    <div className="flex justify-center py-24">
      <div className="w-9 h-9 rounded-full border-2 border-gray-200 animate-spin"
        style={{ borderTopColor: 'var(--color-primary)' }} />
    </div>
  )
}

function CompanyCard({ name, jobCount }) {
  const navigate = useNavigate()
  const [bg, fg] = avatarColor(name)

  function handleViewJobs() {
    navigate(`/jobs?company=${encodeURIComponent(name)}`)
  }

  return (
    <div className="card bg-white rounded-xl p-5 flex items-center gap-4">

      {/* Avatar */}
      <div
        className="w-14 h-14 rounded-2xl flex items-center justify-center text-lg font-bold shrink-0"
        style={{ background: bg, color: fg }}
      >
        {initials(name)}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <h3 className="text-base font-semibold text-gray-900 leading-snug truncate">
          {name}
        </h3>
        <div className="flex items-center gap-1.5 mt-1">
          <span
            className="badge badge-green text-xs"
            style={{ background: 'var(--color-primary-pale)', color: 'var(--color-primary-dark)' }}
          >
            {jobCount} {jobCount === 1 ? 'listing' : 'listings'}
          </span>
        </div>
      </div>

      {/* Action */}
      <button
        onClick={handleViewJobs}
        className="btn-outline text-sm py-2 px-4 shrink-0 flex items-center gap-1.5"
      >
        View Jobs <ArrowIcon />
      </button>
    </div>
  )
}

export default function Companies() {
  const { jobs, loading, error } = useJobs()

  const companies = useMemo(() => {
    const map = {}
    jobs.forEach(job => {
      if (!job.company) return
      map[job.company] = (map[job.company] ?? 0) + 1
    })
    return Object.entries(map)
      .map(([name, jobCount]) => ({ name, jobCount }))
      .sort((a, b) => b.jobCount - a.jobCount || a.name.localeCompare(b.name))
  }, [jobs])

  return (
    <div>
      {/* ── Header ──────────────────────────────────────────────────── */}
      <section className="border-b border-gray-100 bg-white">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10">
          <div className="flex items-center gap-3 mb-1">
            <span style={{ color: 'var(--color-primary)' }}><BuildingIcon /></span>
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">Companies</h1>
          </div>
          <p className="text-gray-400 text-sm">
            {loading ? 'Loading…' : `${companies.length} companies hiring in Namibia`}
          </p>
        </div>
      </section>

      {/* ── Body ────────────────────────────────────────────────────── */}
      <div className="page-container">

        {loading && <Spinner />}

        {error && (
          <div className="rounded-xl p-4 text-sm text-red-600 bg-red-50 border border-red-100">
            <strong>Could not load companies.</strong> Make sure the backend is running on port 8000.
            <br /><span className="text-red-400">{error}</span>
          </div>
        )}

        {!loading && !error && companies.length === 0 && (
          <p className="text-center text-gray-400 py-20">No companies found.</p>
        )}

        {!loading && !error && companies.length > 0 && (
          <>
            {/* Stats strip */}
            <div className="flex flex-wrap items-center gap-6 mb-6 p-4 bg-white rounded-xl border border-gray-100 shadow-sm">
              <div>
                <span className="text-2xl font-bold text-gray-900">{companies.length}</span>
                <span className="text-sm text-gray-400 ml-2">companies</span>
              </div>
              <div className="w-px h-8 bg-gray-100" />
              <div>
                <span className="text-2xl font-bold" style={{ color: 'var(--color-primary)' }}>
                  {jobs.length}
                </span>
                <span className="text-sm text-gray-400 ml-2">total listings</span>
              </div>
              <div className="w-px h-8 bg-gray-100" />
              <div>
                <span className="text-2xl font-bold text-gray-900">
                  {companies[0]?.jobCount ?? 0}
                </span>
                <span className="text-sm text-gray-400 ml-2">most listings</span>
              </div>
            </div>

            {/* Company grid */}
            <div className="grid gap-3 sm:grid-cols-1 lg:grid-cols-2">
              {companies.map(({ name, jobCount }) => (
                <CompanyCard key={name} name={name} jobCount={jobCount} />
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
