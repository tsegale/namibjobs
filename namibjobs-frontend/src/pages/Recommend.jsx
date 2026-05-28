import { useState } from 'react'
import { useLocation } from 'react-router-dom'
import { useRecommend } from '../hooks/useRecommend'
import { useSavedJobs } from '../hooks/useSavedJobs'
import { useApplications } from '../hooks/useApplications'
import JobCard from '../components/JobCard'

const PLACEHOLDER = `Example:
I am a software developer with 3 years of experience in Python, FastAPI and PostgreSQL. I have built REST APIs and data pipelines. I am looking for a full-time role in Windhoek.`

const EXAMPLE_PROFILES = [
  {
    label: 'Software Developer',
    text: 'I am a software developer with 3 years of experience in Python, FastAPI and PostgreSQL. I have built REST APIs and data pipelines. Looking for a full-time role in Windhoek.',
  },
  {
    label: 'Data Analyst',
    text: 'Experienced data analyst skilled in Excel, Power BI, SQL and Python. I have worked on financial reporting and business intelligence dashboards. Seeking a role in Windhoek.',
  },
  {
    label: 'Accountant',
    text: 'Qualified accountant with 5 years experience in financial reporting, auditing and tax compliance. Proficient in Sage and Excel. Looking for a permanent position in Windhoek.',
  },
]

function SparkleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
    </svg>
  )
}

function Spinner() {
  return (
    <div className="flex flex-col items-center justify-center py-24 gap-4">
      <div
        className="w-10 h-10 rounded-full border-2 border-gray-200 animate-spin"
        style={{ borderTopColor: 'var(--color-primary)' }}
      />
      <p className="text-sm text-gray-400">Analysing your profile…</p>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="text-center py-20">
      <div className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4"
        style={{ background: 'var(--color-primary-pale)', color: 'var(--color-primary)' }}>
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
      </div>
      <p className="text-gray-700 font-medium">No matching jobs found</p>
      <p className="text-gray-400 text-sm mt-1">Try describing your skills in more detail</p>
    </div>
  )
}

export default function Recommend() {
  const routerState = useLocation().state   // results passed from Profile page

  const [profile, setProfile] = useState(routerState?.profileText ?? '')
  const { results: hookResults, loading, error, recommend } = useRecommend()
  const { isSaved, toggle } = useSavedJobs()
  const { apply } = useApplications()

  // Use router-state results (from Profile page) if available, else hook results
  const results = routerState?.results ?? hookResults

  const charCount = profile.trim().length

  function handleSubmit(e) {
    e.preventDefault()
    if (charCount < 20) return
    recommend(profile.trim())
  }

  function applyExample(text) {
    setProfile(text)
  }

  const sorted = results
    ? [...results].sort((a, b) => b.match_score - a.match_score)
    : null

  return (
    <div>

      {/* ── Hero ──────────────────────────────────────────────────────── */}
      <section className="border-b border-gray-100 bg-white">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10">

          <div className="flex items-center gap-2 mb-1">
            <span style={{ color: 'var(--color-primary)' }}><SparkleIcon /></span>
            <span className="text-xs font-semibold uppercase tracking-widest"
              style={{ color: 'var(--color-primary)' }}>
              AI-Powered
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 mb-1">
            Get Personalised Job Matches
          </h1>
          <p className="text-gray-400 text-sm mb-6">
            Describe your skills and experience in plain text — we'll find the best-matching jobs for you.
          </p>

          {/* Example chips */}
          <div className="flex flex-wrap gap-2 mb-4">
            <span className="text-xs text-gray-400 self-center">Try an example:</span>
            {EXAMPLE_PROFILES.map(ex => (
              <button
                key={ex.label}
                onClick={() => applyExample(ex.text)}
                className="text-xs px-3 py-1.5 rounded-full border border-gray-200 text-gray-600
                           hover:border-primary hover:text-primary-dark transition-colors"
                style={{ '--tw-border-opacity': 1 }}
              >
                {ex.label}
              </button>
            ))}
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="flex flex-col gap-3">
            <div className="relative">
              <textarea
                rows={5}
                placeholder={PLACEHOLDER}
                value={profile}
                onChange={e => setProfile(e.target.value)}
                className="input resize-none leading-relaxed"
                style={{ paddingBottom: '2rem' }}
              />
              {/* Char count */}
              <span className="absolute bottom-2.5 right-3 text-xs text-gray-300 select-none">
                {charCount} chars
              </span>
            </div>

            <div className="flex items-center justify-between gap-3">
              {charCount > 0 && charCount < 20 && (
                <p className="text-xs text-amber-500">Add a bit more detail for better matches</p>
              )}
              <span className="flex-1" />
              {profile.trim() && (
                <button
                  type="button"
                  onClick={() => setProfile('')}
                  className="text-sm text-gray-400 hover:text-gray-600 transition-colors"
                >
                  Clear
                </button>
              )}
              <button
                type="submit"
                disabled={loading || charCount < 20}
                className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <SparkleIcon />
                {loading ? 'Searching…' : 'Find Jobs'}
              </button>
            </div>
          </form>

        </div>
      </section>

      {/* ── Results ───────────────────────────────────────────────────── */}
      <div className="page-container">

        {loading && <Spinner />}

        {error && (
          <div className="rounded-xl p-4 text-sm text-red-600 bg-red-50 border border-red-100">
            <strong>Something went wrong.</strong> Make sure the backend is running on port 8000.
            <br /><span className="text-red-400">{error}</span>
          </div>
        )}

        {/* From-profile banner */}
        {!loading && routerState?.results && (
          <div className="flex items-center gap-2 mb-5 px-4 py-3 rounded-xl text-sm font-medium"
            style={{ background: 'var(--color-primary-pale)', color: 'var(--color-primary-dark)' }}>
            <SparkleIcon />
            Showing results based on your saved profile
          </div>
        )}

        {/* Results header */}
        {!loading && sorted && sorted.length > 0 && (
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                Top {sorted.length} matches for your profile
              </h2>
              <p className="text-sm text-gray-400 mt-0.5">
                Sorted by relevance — highest match first
              </p>
            </div>
            {/* Top match score badge */}
            <div className="hidden sm:flex flex-col items-end">
              <span className="text-2xl font-bold" style={{ color: 'var(--color-primary)' }}>
                {sorted[0].match_score}%
              </span>
              <span className="text-xs text-gray-400">best match</span>
            </div>
          </div>
        )}

        {!loading && sorted && sorted.length === 0 && <EmptyState />}

        {/* Job grid */}
        {!loading && sorted && sorted.length > 0 && (
          <div className="grid gap-4 lg:grid-cols-2">
            {sorted.map(job => (
              <JobCard
                key={job.id}
                id={job.id}
                title={job.title}
                company={job.company}
                location={job.location}
                skills={job.skills ?? []}
                jobType={job.job_type}
                matchScore={job.match_score}
                sourceUrl={job.source_url}
                isSaved={isSaved(job.id)}
                onBookmark={toggle}
                onApply={apply}
              />
            ))}
          </div>
        )}

        {/* Pre-search prompt */}
        {!loading && !error && sorted === null && (
          <div className="text-center py-20 text-gray-400">
            <p className="text-4xl mb-3">✦</p>
            <p className="font-medium text-gray-600">Your matches will appear here</p>
            <p className="text-sm mt-1">Paste your CV summary or describe your skills above</p>
          </div>
        )}

      </div>
    </div>
  )
}
