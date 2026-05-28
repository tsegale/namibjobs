import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api'
import { useSavedJobs } from '../hooks/useSavedJobs'
import { useApplications } from '../hooks/useApplications'
import JobCard from '../components/JobCard'
import { avatarColor, initials as getInitials } from '../utils/company'

const STORAGE_KEY = 'namibjobs_profile'

const NAMIBIAN_CITIES = [
  'Windhoek', 'Walvis Bay', 'Swakopmund', 'Oshakati', 'Rundu',
  'Lüderitz', 'Tsumeb', 'Grootfontein', 'Keetmanshoop', 'Otjiwarongo',
  'Mariental', 'Katima Mulilo',
]

const EMPTY_PROFILE = {
  fullName:   '',
  email:      '',
  location:   'Windhoek',
  skills:     [],
  experience: '',
  bio:        '',
}

function loadProfile() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? { ...EMPTY_PROFILE, ...JSON.parse(raw) } : { ...EMPTY_PROFILE }
  } catch {
    return { ...EMPTY_PROFILE }
  }
}

function hasContent(p) {
  return !!(p.fullName || p.email || p.skills.length > 0 || p.bio.trim())
}

function nameInitials(name) {
  if (!name.trim()) return '?'
  return name.trim().split(/\s+/).map(w => w[0]).slice(0, 2).join('').toUpperCase()
}

// ── Icons ─────────────────────────────────────────────────────────────────────

function UserIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  )
}

function MailIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="4" width="20" height="16" rx="2" />
      <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
    </svg>
  )
}

function MapPinIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
      <circle cx="12" cy="10" r="3" />
    </svg>
  )
}

function BriefcaseIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="7" width="20" height="14" rx="2" />
      <path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2" />
      <path d="M2 12h20" />
    </svg>
  )
}

function PencilIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z" />
    </svg>
  )
}

function CheckIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  )
}

function SparkleIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
    </svg>
  )
}

function ArrowIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="5" y1="12" x2="19" y2="12" />
      <polyline points="12 5 19 12 12 19" />
    </svg>
  )
}

function RefreshIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23 4 23 10 17 10" />
      <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
    </svg>
  )
}

function Spinner() {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-3">
      <div className="w-9 h-9 rounded-full border-2 border-gray-200 animate-spin"
        style={{ borderTopColor: 'var(--color-primary)' }} />
      <p className="text-sm text-gray-400">Finding your matches…</p>
    </div>
  )
}

// ── Skills tag input ──────────────────────────────────────────────────────────

function SkillsInput({ skills, onChange }) {
  const [input, setInput] = useState('')
  const inputRef = useRef(null)

  function addSkill(raw) {
    const skill = raw.trim().toLowerCase()
    if (skill && !skills.includes(skill)) onChange([...skills, skill])
    setInput('')
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault()
      addSkill(input)
    } else if (e.key === 'Backspace' && !input && skills.length > 0) {
      onChange(skills.slice(0, -1))
    }
  }

  return (
    <div
      className="flex flex-wrap gap-1.5 p-2 rounded-lg bg-white cursor-text min-h-[44px]"
      style={{ border: '1.5px solid var(--color-gray-200)' }}
      onClick={() => inputRef.current?.focus()}
    >
      {skills.map(skill => (
        <span key={skill}
          className="flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-full capitalize"
          style={{ background: 'var(--color-primary-pale)', color: 'var(--color-primary-dark)' }}>
          {skill}
          <button type="button"
            onClick={e => { e.stopPropagation(); onChange(skills.filter(s => s !== skill)) }}
            className="hover:opacity-60 leading-none text-base" aria-label={`Remove ${skill}`}>×</button>
        </span>
      ))}
      <input ref={inputRef} type="text" value={input}
        onChange={e => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={() => input.trim() && addSkill(input)}
        placeholder={skills.length === 0 ? 'Type a skill and press Enter…' : ''}
        className="flex-1 min-w-[140px] text-sm outline-none bg-transparent text-gray-700 placeholder:text-gray-300 py-0.5"
      />
    </div>
  )
}

// ── Field wrapper ─────────────────────────────────────────────────────────────

function Field({ label, hint, children }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-sm font-medium text-gray-700">{label}</label>
      {children}
      {hint && <p className="text-xs text-gray-400">{hint}</p>}
    </div>
  )
}

// ── Tab bar ───────────────────────────────────────────────────────────────────

function TabBar({ tabs, active, onChange }) {
  return (
    <div className="flex overflow-x-auto border-b border-gray-200 bg-white rounded-t-2xl">
      {tabs.map(tab => (
        <button key={tab.id} onClick={() => onChange(tab.id)}
          className="flex items-center gap-1.5 px-4 sm:px-5 py-3 text-sm font-medium whitespace-nowrap -mb-px border-b-2 transition-colors duration-150"
          style={{
            color: active === tab.id ? 'var(--color-primary-dark)' : 'var(--color-gray-500)',
            borderBottomColor: active === tab.id ? 'var(--color-primary)' : 'transparent',
          }}
        >
          {tab.label}
          {tab.count > 0 && (
            <span className="text-xs font-semibold px-1.5 py-0.5 rounded-full"
              style={{ background: 'var(--color-primary-pale)', color: 'var(--color-primary-dark)' }}>
              {tab.count}
            </span>
          )}
        </button>
      ))}
    </div>
  )
}

// ── Overview tab ──────────────────────────────────────────────────────────────

function OverviewTab({ profile, onEdit }) {
  const initials = nameInitials(profile.fullName)

  const infoRows = [
    profile.email      && { icon: <MailIcon />,      label: profile.email },
    profile.location   && { icon: <MapPinIcon />,    label: `${profile.location}, Namibia` },
    profile.experience && { icon: <BriefcaseIcon />, label: `${profile.experience} year${profile.experience !== '1' ? 's' : ''} of experience` },
  ].filter(Boolean)

  return (
    <div className="flex flex-col gap-6">

      {/* Avatar + name */}
      <div className="flex items-center gap-5">
        <div className="w-20 h-20 rounded-full flex items-center justify-center text-2xl font-bold text-white shrink-0 select-none"
          style={{ background: 'var(--color-primary)' }}>
          {initials}
        </div>
        <div>
          <h2 className="text-xl font-bold text-gray-900 leading-snug">
            {profile.fullName || <span className="text-gray-400 font-normal italic">No name set</span>}
          </h2>
          {profile.location && (
            <p className="text-sm mt-0.5" style={{ color: 'var(--color-gray-500)' }}>
              {profile.location}, Namibia
            </p>
          )}
        </div>
      </div>

      {/* Info rows */}
      {infoRows.length > 0 && (
        <div className="flex flex-col gap-3 py-4 border-y border-gray-100">
          {infoRows.map((row, i) => (
            <div key={i} className="flex items-center gap-3 text-sm" style={{ color: 'var(--color-gray-600)' }}>
              <span className="shrink-0" style={{ color: 'var(--color-primary)' }}>{row.icon}</span>
              {row.label}
            </div>
          ))}
        </div>
      )}

      {/* Skills */}
      {profile.skills.length > 0 && (
        <div className="flex flex-col gap-2.5">
          <p className="text-xs font-semibold uppercase tracking-widest" style={{ color: 'var(--color-gray-400)' }}>Skills</p>
          <div className="flex flex-wrap gap-2">
            {profile.skills.map(skill => (
              <span key={skill} className="text-xs font-medium px-3 py-1.5 rounded-full capitalize"
                style={{ background: 'var(--color-primary-pale)', color: 'var(--color-primary-dark)' }}>
                {skill}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Bio */}
      {profile.bio.trim() && (
        <div className="flex flex-col gap-2">
          <p className="text-xs font-semibold uppercase tracking-widest" style={{ color: 'var(--color-gray-400)' }}>About</p>
          <p className="text-sm leading-relaxed" style={{ color: 'var(--color-gray-600)' }}>{profile.bio}</p>
        </div>
      )}

      {/* Empty state */}
      {!hasContent(profile) && (
        <div className="text-center py-8 text-gray-400">
          <p className="font-medium text-gray-600 mb-1">Your profile is empty</p>
          <p className="text-sm">Click Edit Profile to fill in your details.</p>
        </div>
      )}

      {/* Edit button */}
      <div className="pt-2 border-t border-gray-100">
        <button type="button" onClick={onEdit} className="btn-outline w-full justify-center">
          <PencilIcon /> Edit Profile
        </button>
      </div>

    </div>
  )
}

// ── Saved Jobs tab ────────────────────────────────────────────────────────────

function SavedJobsTab({ savedJobs, toggle, apply }) {
  const navigate = useNavigate()

  if (savedJobs.length === 0) {
    return (
      <div className="text-center py-14 flex flex-col items-center gap-4">
        <div className="w-14 h-14 rounded-2xl flex items-center justify-center"
          style={{ background: 'var(--color-primary-pale)', color: 'var(--color-primary)' }}>
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
          </svg>
        </div>
        <div>
          <p className="font-medium text-gray-700">No saved jobs yet</p>
          <p className="text-sm text-gray-400 mt-1">
            Browse jobs and click the bookmark icon to save them.
          </p>
        </div>
        <button onClick={() => navigate('/jobs')} className="btn-primary mt-2">
          Browse Jobs <ArrowIcon />
        </button>
      </div>
    )
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {savedJobs.map(job => (
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
          matchScore={job.match_score ?? null}
          isSaved={true}
          onBookmark={toggle}
          onApply={apply}
        />
      ))}
    </div>
  )
}

// ── Applications tab ──────────────────────────────────────────────────────────

function ApplicationsTab({ applications }) {
  if (applications.length === 0) {
    return (
      <div className="text-center py-14 flex flex-col items-center gap-3">
        <div className="w-14 h-14 rounded-2xl flex items-center justify-center"
          style={{ background: 'var(--color-primary-pale)', color: 'var(--color-primary)' }}>
          <BriefcaseIcon />
        </div>
        <div>
          <p className="font-medium text-gray-700">No applications yet</p>
          <p className="text-sm text-gray-400 mt-1">
            Jobs you apply for will appear here.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      {[...applications].reverse().map(app => {
        const [bg, fg] = avatarColor(app.company ?? '')
        const dateStr  = new Date(app.appliedAt).toLocaleDateString('en-GB', {
          day: 'numeric', month: 'short', year: 'numeric',
        })
        return (
          <div key={app.id}
            className="flex items-center gap-4 p-4 bg-white rounded-xl border border-gray-100 shadow-sm">

            {/* Company avatar */}
            <div className="w-10 h-10 rounded-xl flex items-center justify-center text-sm font-bold shrink-0"
              style={{ background: bg, color: fg }}>
              {getInitials(app.company ?? '')}
            </div>

            {/* Info */}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-gray-900 truncate">{app.title}</p>
              <p className="text-xs text-gray-500 mt-0.5 truncate">{app.company}</p>
              <p className="text-xs mt-1" style={{ color: 'var(--color-gray-400)' }}>
                Applied {dateStr}
              </p>
            </div>

            {/* Status badge */}
            <span className="badge badge-green shrink-0">Applied</span>
          </div>
        )
      })}
    </div>
  )
}

// ── Recommendations tab ───────────────────────────────────────────────────────

function RecommendationsTab({ profile, isSaved, toggle, apply }) {
  const [results,  setResults]  = useState(null)
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState(null)

  const canRefresh = profile.skills.length > 0 || profile.bio.trim().length > 20

  async function handleRefresh() {
    setLoading(true)
    setError(null)

    const profileText = [
      profile.fullName   && `My name is ${profile.fullName}.`,
      profile.location   && `I am based in ${profile.location}, Namibia.`,
      profile.experience && `I have ${profile.experience} year${profile.experience !== '1' ? 's' : ''} of experience.`,
      profile.skills.length > 0 && `My skills include: ${profile.skills.join(', ')}.`,
      profile.bio        && profile.bio,
    ].filter(Boolean).join(' ')

    try {
      const res = await api.post('/recommend', { profile_text: profileText })
      setResults(res.data)
    } catch (err) {
      setError(err.response?.data?.detail ?? err.message ?? 'Request failed')
    } finally {
      setLoading(false)
    }
  }

  const sorted = results ? [...results].sort((a, b) => b.match_score - a.match_score) : null

  return (
    <div className="flex flex-col gap-5">

      {/* Header + button */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-gray-100">
        <div>
          <p className="text-sm font-semibold text-gray-800">AI-Powered Matches</p>
          <p className="text-xs mt-0.5" style={{ color: 'var(--color-gray-400)' }}>
            Based on your profile skills and bio
          </p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={loading || !canRefresh}
          className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <RefreshIcon />
          {loading ? 'Searching…' : 'Refresh My Recommendations'}
        </button>
      </div>

      {!canRefresh && (
        <p className="text-xs text-center" style={{ color: 'var(--color-gray-400)' }}>
          Add skills or a bio to your profile to enable recommendations.
        </p>
      )}

      {loading && <Spinner />}

      {error && (
        <div className="rounded-xl p-4 text-sm text-red-600 bg-red-50 border border-red-100">
          <strong>Something went wrong.</strong> Make sure the backend is running on port 8000.
          <br /><span className="text-red-400">{error}</span>
        </div>
      )}

      {!loading && sorted && sorted.length === 0 && (
        <p className="text-center py-10 text-gray-400 text-sm">No matching jobs found. Try updating your profile.</p>
      )}

      {!loading && sorted && sorted.length > 0 && (
        <>
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-gray-700">
              Top {sorted.length} matches
            </p>
            <span className="text-2xl font-bold" style={{ color: 'var(--color-primary)' }}>
              {sorted[0].match_score}%
              <span className="text-xs font-normal text-gray-400 ml-1">best match</span>
            </span>
          </div>
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
        </>
      )}

      {!loading && !sorted && canRefresh && (
        <div className="text-center py-14 text-gray-400">
          <p className="text-3xl mb-3">✦</p>
          <p className="font-medium text-gray-600">Your matches will appear here</p>
          <p className="text-sm mt-1">Click "Refresh My Recommendations" to get started</p>
        </div>
      )}

    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function Profile() {
  const [profile,   setProfile]   = useState(loadProfile)
  const [isEditing, setIsEditing] = useState(() => !hasContent(loadProfile()))
  const [activeTab, setActiveTab] = useState('overview')
  const [saved,     setSaved]     = useState(false)

  const { saved: savedJobs, toggle, isSaved } = useSavedJobs()
  const { applications, apply }               = useApplications()

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(profile))
  }, [profile])

  function set(field) {
    return e => setProfile(p => ({ ...p, [field]: e.target.value }))
  }

  function handleSave(e) {
    e.preventDefault()
    localStorage.setItem(STORAGE_KEY, JSON.stringify(profile))
    setSaved(true)
    setTimeout(() => {
      setSaved(false)
      setIsEditing(false)
      setActiveTab('overview')
    }, 900)
  }

  const TABS = [
    { id: 'overview',        label: 'Overview' },
    { id: 'saved',           label: 'Saved Jobs',   count: savedJobs.length },
    { id: 'applications',    label: 'Applications', count: applications.length },
    { id: 'recommendations', label: 'Recommendations' },
  ]

  return (
    <div>

      {/* ── Header ──────────────────────────────────────────────────── */}
      <section className="border-b border-gray-100 bg-white">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10">
          <div className="flex items-center gap-3 mb-1">
            <span style={{ color: 'var(--color-primary)' }}><UserIcon /></span>
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">My Profile</h1>
          </div>
          <p className="text-sm" style={{ color: 'var(--color-gray-400)' }}>
            {isEditing
              ? 'Fill in your details — we\'ll use them to find your best job matches.'
              : 'Your saved profile, bookmarked jobs, and applications.'}
          </p>
        </div>
      </section>

      {/* ── Body ────────────────────────────────────────────────────── */}
      <div className="page-container">
        <div className="max-w-2xl mx-auto">

          {isEditing ? (

            /* ── Edit form ─────────────────────────────────────────── */
            <form key="form" onSubmit={handleSave}
              className="animate-fade-in bg-white rounded-2xl border border-gray-100 shadow-sm p-6 sm:p-8 flex flex-col gap-6">

              <div>
                <h2 className="text-base font-semibold text-gray-800 mb-4 pb-2 border-b border-gray-100">
                  Personal Information
                </h2>
                <div className="grid sm:grid-cols-2 gap-4">
                  <Field label="Full Name">
                    <input type="text" className="input" placeholder="e.g. James Parata"
                      value={profile.fullName} onChange={set('fullName')} />
                  </Field>
                  <Field label="Email">
                    <input type="email" className="input" placeholder="you@example.com"
                      value={profile.email} onChange={set('email')} />
                  </Field>
                  <Field label="Location">
                    <select className="input bg-white" value={profile.location} onChange={set('location')}>
                      {NAMIBIAN_CITIES.map(city => <option key={city} value={city}>{city}</option>)}
                    </select>
                  </Field>
                  <Field label="Years of Experience">
                    <input type="number" className="input" placeholder="e.g. 3"
                      min="0" max="50" value={profile.experience} onChange={set('experience')} />
                  </Field>
                </div>
              </div>

              <div>
                <h2 className="text-base font-semibold text-gray-800 mb-4 pb-2 border-b border-gray-100">Skills</h2>
                <Field label="Your Skills"
                  hint="Type a skill and press Enter or comma to add it. Backspace removes the last one.">
                  <SkillsInput skills={profile.skills} onChange={skills => setProfile(p => ({ ...p, skills }))} />
                </Field>
              </div>

              <div>
                <h2 className="text-base font-semibold text-gray-800 mb-4 pb-2 border-b border-gray-100">About You</h2>
                <Field label="Bio / Summary"
                  hint="Describe your experience, goals, and what kind of role you're looking for.">
                  <textarea rows={5} className="input resize-none leading-relaxed"
                    placeholder="e.g. I am a software developer with 3 years of experience in Python and FastAPI, looking for a full-time backend role in Windhoek..."
                    value={profile.bio} onChange={set('bio')} />
                </Field>
              </div>

              <div className="flex flex-col sm:flex-row gap-3 pt-2 border-t border-gray-100">
                {hasContent(profile) && (
                  <button type="button" onClick={() => setIsEditing(false)}
                    className="btn-outline flex-1 justify-center">
                    Cancel
                  </button>
                )}
                <button type="submit" className="btn-primary flex-1 justify-center">
                  {saved ? <><CheckIcon /> Saved!</> : <><CheckIcon /> Save Profile</>}
                </button>
              </div>

            </form>

          ) : (

            /* ── Tabbed view ────────────────────────────────────────── */
            <div className="animate-fade-in flex flex-col rounded-2xl border border-gray-100 shadow-sm overflow-hidden">

              <TabBar tabs={TABS} active={activeTab} onChange={setActiveTab} />

              <div key={activeTab} className="animate-fade-in bg-white p-6 sm:p-8">
                {activeTab === 'overview' && (
                  <OverviewTab profile={profile} onEdit={() => setIsEditing(true)} />
                )}
                {activeTab === 'saved' && (
                  <SavedJobsTab savedJobs={savedJobs} toggle={toggle} apply={apply} />
                )}
                {activeTab === 'applications' && (
                  <ApplicationsTab applications={applications} />
                )}
                {activeTab === 'recommendations' && (
                  <RecommendationsTab
                    profile={profile}
                    isSaved={isSaved}
                    toggle={toggle}
                    apply={apply}
                  />
                )}
              </div>

            </div>

          )}

        </div>
      </div>

    </div>
  )
}
