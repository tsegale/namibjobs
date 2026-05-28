import { useNavigate } from 'react-router-dom'

// Generates a consistent bg color per company name
const AVATAR_COLORS = [
  ['#D1FAE5', '#065F46'], // green
  ['#DBEAFE', '#1E40AF'], // blue
  ['#FEF3C7', '#92400E'], // amber
  ['#FCE7F3', '#9D174D'], // pink
  ['#EDE9FE', '#5B21B6'], // violet
  ['#FFEDD5', '#9A3412'], // orange
  ['#F0FDF4', '#14532D'], // emerald
  ['#E0F2FE', '#075985'], // sky
]

function avatarColor(name = '') {
  let hash = 0
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash)
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length]
}

function initials(name = '') {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map(w => w[0].toUpperCase())
    .join('')
}

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

const MAX_SKILLS = 4
const DESCRIPTION_LIMIT = 110

export default function JobCard({
  id,
  title        = 'Job Title',
  company      = 'Company',
  location     = '',
  description  = '',
  skills       = [],
  jobType      = '',
  salary       = '',
  isNew        = false,
  isRemote     = false,
  matchScore   = null,   // 0–100 or null to hide
  sourceUrl    = '#',
  onApply,
}) {
  const navigate = useNavigate()
  const [bg, fg] = avatarColor(company)

  const preview = description.length > DESCRIPTION_LIMIT
    ? description.slice(0, DESCRIPTION_LIMIT).trimEnd() + '…'
    : description

  const visibleSkills = skills.slice(0, MAX_SKILLS)
  const extraSkills   = skills.length - MAX_SKILLS

  function handleApply(e) {
    e.stopPropagation()
    if (onApply) return onApply(id)
    window.open(sourceUrl, '_blank', 'noopener,noreferrer')
  }

  return (
    <article
      className="card bg-white rounded-xl p-5 cursor-pointer flex flex-col gap-4"
      onClick={() => navigate(`/jobs/${id}`)}
      role="button"
      tabIndex={0}
      onKeyDown={e => e.key === 'Enter' && navigate(`/jobs/${id}`)}
    >

      {/* ── Top row ───────────────────────────────────────────────────── */}
      <div className="flex items-start gap-3">

        {/* Company avatar */}
        <div
          className="w-11 h-11 rounded-xl flex items-center justify-center text-sm font-bold shrink-0"
          style={{ background: bg, color: fg }}
        >
          {initials(company)}
        </div>

        {/* Title + meta */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <h3 className="text-base font-semibold text-gray-900 leading-snug line-clamp-1">
              {title}
            </h3>

            {/* Badges */}
            <div className="flex items-center gap-1.5 shrink-0">
              {isNew && (
                <span className="badge badge-green text-xs">New</span>
              )}
              {isRemote && (
                <span className="badge badge-blue text-xs">Remote</span>
              )}
            </div>
          </div>

          {/* Company · location */}
          <div className="flex items-center gap-2 mt-0.5 text-sm text-gray-500 flex-wrap">
            <span className="font-medium text-gray-700">{company}</span>
            {location && (
              <>
                <span className="text-gray-300">·</span>
                <span className="flex items-center gap-1">
                  <LocationIcon />
                  {location}
                </span>
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
        <p className="text-sm text-gray-500 leading-relaxed -mt-1">
          {preview}
        </p>
      )}

      {/* ── Skill tags ─────────────────────────────────────────────────── */}
      {skills.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {visibleSkills.map(skill => (
            <span
              key={skill}
              className="text-xs font-medium px-2.5 py-1 rounded-full capitalize"
              style={{
                background: 'var(--color-primary-pale)',
                color: 'var(--color-primary-dark)',
              }}
            >
              {skill}
            </span>
          ))}
          {extraSkills > 0 && (
            <span className="badge badge-gray text-xs">+{extraSkills}</span>
          )}
        </div>
      )}

      {/* ── Bottom row: match bar + apply ──────────────────────────────── */}
      <div className="flex items-center gap-4 pt-1 border-t border-gray-100">

        {/* Match score */}
        {matchScore !== null ? (
          <div className="flex-1 flex items-center gap-2 min-w-0">
            <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${Math.min(100, Math.max(0, matchScore))}%`,
                  background: matchScore >= 70
                    ? 'var(--color-primary)'
                    : matchScore >= 40
                    ? 'var(--color-accent)'
                    : 'var(--color-gray-300)',
                }}
              />
            </div>
            <span
              className="text-xs font-semibold shrink-0 tabular-nums"
              style={{ color: matchScore >= 70 ? 'var(--color-primary-dark)' : 'var(--color-gray-500)' }}
            >
              {matchScore}% match
            </span>
          </div>
        ) : (
          /* Salary fallback when no match score */
          salary ? (
            <span className="flex-1 text-sm font-medium text-gray-600">{salary}</span>
          ) : (
            <span className="flex-1" />
          )
        )}

        {/* Apply button */}
        <button
          className="btn-primary text-sm py-2 px-4 shrink-0"
          onClick={handleApply}
        >
          Apply <ArrowIcon />
        </button>
      </div>

    </article>
  )
}
