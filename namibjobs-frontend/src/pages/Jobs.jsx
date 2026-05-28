import { useState, useMemo } from 'react'
import { useJobs } from '../hooks/useJobs'
import JobCard from '../components/JobCard'

function SearchIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  )
}

function BriefcaseIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="7" width="20" height="14" rx="2" />
      <path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2" />
      <path d="M2 12h20" />
    </svg>
  )
}

function BuildingIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
      <polyline points="9 22 9 12 15 12 15 22" />
    </svg>
  )
}

function SparkleIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
    </svg>
  )
}

function LocationIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
      <circle cx="12" cy="10" r="3" />
    </svg>
  )
}

function Spinner() {
  return (
    <div className="flex justify-center py-24">
      <div
        className="w-9 h-9 rounded-full border-2 border-gray-200 animate-spin"
        style={{ borderTopColor: 'var(--color-primary)' }}
      />
    </div>
  )
}

function StatCard({ icon, value, label, color }) {
  return (
    <div className="bg-white rounded-xl border border-gray-100 px-5 py-4 flex items-center gap-4 shadow-sm">
      <div className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
        style={{ background: color + '22', color }}>
        {icon}
      </div>
      <div>
        <p className="text-2xl font-bold text-gray-900 leading-none">{value}</p>
        <p className="text-xs text-gray-400 mt-1">{label}</p>
      </div>
    </div>
  )
}

function filterJobs(jobs, keyword, location) {
  const kw  = keyword.trim().toLowerCase()
  const loc = location.trim().toLowerCase()
  return jobs.filter(job => {
    const matchesKw = !kw || [job.title, job.company, job.description, ...(job.skills ?? [])]
      .some(f => f?.toLowerCase().includes(kw))
    const matchesLoc = !loc ||
      job.location?.toLowerCase().includes(loc) ||
      job.description?.toLowerCase().includes(loc)
    return matchesKw && matchesLoc
  })
}

export default function Jobs() {
  const { jobs, loading, error } = useJobs()

  const [keyword,  setKeyword]  = useState('')
  const [location, setLocation] = useState('Windhoek')
  const [applied,  setApplied]  = useState({ keyword: '', location: 'Windhoek' })

  const filtered = useMemo(
    () => filterJobs(jobs, applied.keyword, applied.location),
    [jobs, applied],
  )

  const totalCompanies = useMemo(
    () => new Set(jobs.map(j => j.company)).size,
    [jobs],
  )

  function handleSearch(e) {
    e.preventDefault()
    setApplied({ keyword, location })
  }

  return (
    <div>

      {/* ── Search hero ───────────────────────────────────────────────── */}
      <section className="border-b border-gray-100 bg-white">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10">
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 mb-1">
            Find Your Next Job in{' '}
            <span style={{ color: 'var(--color-primary)' }}>Namibia</span>
          </h1>
          <p className="text-gray-400 text-sm mb-6">
            Explore {jobs.length} opportunities across Namibia
          </p>

          <form onSubmit={handleSearch}
            className="flex flex-col sm:flex-row gap-3">

            {/* Keyword */}
            <div className="relative flex-1">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
                <SearchIcon />
              </span>
              <input
                type="text"
                placeholder="Job title, skill, or keyword"
                value={keyword}
                onChange={e => setKeyword(e.target.value)}
                className="input pl-9"
              />
            </div>

            {/* Location */}
            <div className="relative sm:w-52">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
                <LocationIcon />
              </span>
              <input
                type="text"
                placeholder="Location"
                value={location}
                onChange={e => setLocation(e.target.value)}
                className="input pl-9"
              />
            </div>

            {/* Search button */}
            <button type="submit" className="btn-primary sm:w-auto w-full justify-center">
              <SearchIcon />
              Search
            </button>
          </form>
        </div>
      </section>

      {/* ── Page body ─────────────────────────────────────────────────── */}
      <div className="page-container">

        {/* ── Stats row ─────────────────────────────────────────────── */}
        {!loading && !error && (
          <div className="grid grid-cols-3 gap-3 mb-8">
            <StatCard
              icon={<BriefcaseIcon />}
              value={jobs.length}
              label="Jobs listed"
              color="var(--color-primary)"
            />
            <StatCard
              icon={<BuildingIcon />}
              value={totalCompanies}
              label="Companies"
              color="var(--color-accent)"
            />
            <StatCard
              icon={<SparkleIcon />}
              value={filtered.length}
              label="Your matches"
              color="#F59E0B"
            />
          </div>
        )}

        {/* ── Results header ────────────────────────────────────────── */}
        {!loading && !error && (
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-gray-500">
              {filtered.length === jobs.length
                ? `Showing all ${jobs.length} jobs`
                : `${filtered.length} result${filtered.length !== 1 ? 's' : ''} found`}
              {applied.location && (
                <span className="ml-1">
                  in <span className="font-medium text-gray-700">{applied.location}</span>
                </span>
              )}
            </p>
            {applied.keyword && (
              <button
                onClick={() => { setKeyword(''); setApplied(a => ({ ...a, keyword: '' })) }}
                className="text-xs text-gray-400 hover:text-gray-600 underline"
              >
                Clear search
              </button>
            )}
          </div>
        )}

        {/* ── States ───────────────────────────────────────────────── */}
        {loading && <Spinner />}

        {error && (
          <div className="rounded-xl p-4 text-sm text-red-600 bg-red-50 border border-red-100">
            <strong>Could not load jobs.</strong> Make sure the backend is running on port 8000.
            <br />
            <span className="text-red-400">{error}</span>
          </div>
        )}

        {!loading && !error && filtered.length === 0 && (
          <div className="text-center py-20">
            <p className="text-4xl mb-3">🔍</p>
            <p className="text-gray-700 font-medium">No jobs matched your search</p>
            <p className="text-gray-400 text-sm mt-1">
              Try a different keyword or location
            </p>
          </div>
        )}

        {/* ── Job grid ─────────────────────────────────────────────── */}
        {!loading && !error && filtered.length > 0 && (
          <div className="grid gap-4 lg:grid-cols-2">
            {filtered.map((job, i) => (
              <JobCard
                key={job.id}
                id={job.id}
                title={job.title}
                company={job.company}
                location={job.location}
                description={job.description}
                skills={job.skills ?? []}
                jobType={job.job_type}
                salary={job.salary}
                sourceUrl={job.source_url}
                isNew={i < 3}
                isRemote={job.location?.toLowerCase().includes('remote')}
              />
            ))}
          </div>
        )}

      </div>
    </div>
  )
}
