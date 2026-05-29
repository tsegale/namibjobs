import { avatarColor, initials as getInitials } from '../utils/company'

function LocationIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
      <circle cx="12" cy="10" r="3" />
    </svg>
  )
}

function ArrowIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="5" y1="12" x2="19" y2="12" />
      <polyline points="12 5 19 12 12 19" />
    </svg>
  )
}

function BookmarkIcon({ filled }) {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24"
      fill={filled ? 'currentColor' : 'none'}
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
    </svg>
  )
}

const MAX_SKILLS        = 4
const DESCRIPTION_LIMIT = 110

export default function JobCard({
  id,
  title       = 'Job Title',
  company     = 'Company',
  location    = '',
  description = '',
  skills      = [],
  jobType     = '',
  salary      = '',
  isNew       = false,
  isRemote    = false,
  matchScore  = null,
  sourceUrl   = '#',
  isSaved     = false,
  onBookmark,
  onApply,
}) {
  const [bg, fg] = avatarColor(company)

  const desc    = description ?? ''
  const preview = desc.length > DESCRIPTION_LIMIT
    ? desc.slice(0, DESCRIPTION_LIMIT).trimEnd() + '…'
    : desc

  const visibleSkills = skills.slice(0, MAX_SKILLS)
  const extraSkills   = skills.length - MAX_SKILLS

  function handleApply(e) {
    e.stopPropagation()
    if (onApply) onApply({ id, title, company, location, description, job_type: jobType, source_url: sourceUrl, match_score: matchScore })
    if (sourceUrl && sourceUrl !== '#') window.open(sourceUrl, '_blank', 'noopener,noreferrer')
  }

  function handleBookmark(e) {
    e.stopPropagation()
    if (onBookmark) onBookmark({ id, title, company, location, description, skills, job_type: jobType, salary, source_url: sourceUrl, match_score: matchScore })
  }

  return (
    <article className="card bg-white rounded-xl p-5 flex flex-col gap-4">

      {/* ── Top row ───────────────────────────────────────────────────── */}
      <div className="flex items-start gap-3">

        {/* Company avatar */}
        <div
          className="w-11 h-11 rounded-xl flex items-center justify-center text-sm font-bold shrink-0"
          style={{ background: bg, color: fg }}
        >
          {getInitials(company)}
        </div>

        {/* Title + meta */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <h3 className="text-base font-semibold text-gray-900 leading-snug line-clamp-1">
              {title}
            </h3>
            <div className="flex items-center gap-1.5 shrink-0">
              {isNew    && <span className="badge badge-green text-xs">New</span>}
              {isRemote && <span className="badge badge-blue text-xs">Remote</span>}
            </div>
          </div>
          <div className="flex items-center gap-2 mt-0.5 text-sm text-gray-500 flex-wrap">
            <span className="font-medium text-gray-700">{company}</span>
            {location && (
              <>
                <span className="text-gray-300">·</span>
                <span className="flex items-center gap-1"><LocationIcon />{location}</span>
              </>
            )}
            {jobType && (
              <>
                <span className="text-gray-300">·</span>
                <span className="capitalize">{jobType}</span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* ── Description preview ────────────────────────────────────────── */}
      {preview && (
        <p className="text-sm text-gray-500 leading-relaxed -mt-1">{preview}</p>
      )}

      {/* ── Skill tags ─────────────────────────────────────────────────── */}
      {skills.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {visibleSkills.map(skill => (
            <span key={skill}
              className="text-xs font-medium px-2.5 py-1 rounded-full capitalize"
              style={{ background: 'var(--color-primary-pale)', color: 'var(--color-primary-dark)' }}>
              {skill}
            </span>
          ))}
          {extraSkills > 0 && <span className="badge badge-gray text-xs">+{extraSkills}</span>}
        </div>
      )}

      {/* ── Bottom row ─────────────────────────────────────────────────── */}
      <div className="flex items-center gap-2 pt-1 border-t border-gray-100">

        {/* Match bar or salary */}
        {matchScore !== null ? (
          <div className="flex-1 flex items-center gap-2 min-w-0">
            <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${Math.min(100, Math.max(0, matchScore))}%`,
                  background: matchScore >= 70
                    ? 'var(--color-primary)'
                    : matchScore >= 40 ? 'var(--color-accent)' : 'var(--color-gray-300)',
                }} />
            </div>
            <span className="text-xs font-semibold shrink-0 tabular-nums"
              style={{ color: matchScore >= 70 ? 'var(--color-primary-dark)' : 'var(--color-gray-500)' }}>
              {matchScore}% match
            </span>
          </div>
        ) : salary ? (
          <span className="flex-1 text-sm font-medium text-gray-600">{salary}</span>
        ) : (
          <span className="flex-1" />
        )}

        {/* Bookmark button */}
        {onBookmark && (
          <button
            onClick={handleBookmark}
            className="w-8 h-8 flex items-center justify-center rounded-lg transition-colors duration-150 shrink-0"
            style={{
              color: isSaved ? 'var(--color-primary)' : 'var(--color-gray-400)',
              background: isSaved ? 'var(--color-primary-pale)' : 'transparent',
            }}
            title={isSaved ? 'Remove from saved' : 'Save job'}
            aria-label={isSaved ? 'Remove from saved jobs' : 'Save job'}
          >
            <BookmarkIcon filled={isSaved} />
          </button>
        )}

        {/* Apply button */}
        <button className="btn-primary text-sm py-2 px-4 shrink-0" onClick={handleApply}>
          Apply <ArrowIcon />
        </button>
      </div>

    </article>
  )
}
