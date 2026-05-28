import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api'

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

function getInitials(name) {
  if (!name.trim()) return '?'
  return name.trim().split(/\s+/).map(w => w[0]).slice(0, 2).join('').toUpperCase()
}

// ── Icons ─────────────────────────────────────────────────────────────────────

function UserIcon({ size = 22 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
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

function BriefcaseIcon({ size = 15 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
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
            className="hover:opacity-60 leading-none text-base"
            aria-label={`Remove ${skill}`}>×</button>
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

// ── Profile card (read-only view) ─────────────────────────────────────────────

function ProfileCard({ profile, onEdit }) {
  const initials = getInitials(profile.fullName)

  const infoRows = [
    profile.email      && { icon: <MailIcon />,       label: profile.email },
    profile.location   && { icon: <MapPinIcon />,     label: `${profile.location}, Namibia` },
    profile.experience && { icon: <BriefcaseIcon />,  label: `${profile.experience} year${profile.experience !== '1' ? 's' : ''} of experience` },
  ].filter(Boolean)

  return (
    <div className="animate-fade-in bg-white rounded-2xl border border-gray-100 shadow-sm p-6 sm:p-8 flex flex-col gap-6">

      {/* ── Avatar + name ──────────────────────────────────────────── */}
      <div className="flex items-center gap-5">
        <div
          className="w-20 h-20 rounded-full flex items-center justify-center text-2xl font-bold text-white shrink-0 select-none"
          style={{ background: 'var(--color-primary)' }}
        >
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

      {/* ── Info rows ──────────────────────────────────────────────── */}
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

      {/* ── Skills ─────────────────────────────────────────────────── */}
      {profile.skills.length > 0 && (
        <div className="flex flex-col gap-2.5">
          <p className="text-xs font-semibold uppercase tracking-widest" style={{ color: 'var(--color-gray-400)' }}>
            Skills
          </p>
          <div className="flex flex-wrap gap-2">
            {profile.skills.map(skill => (
              <span key={skill}
                className="text-xs font-medium px-3 py-1.5 rounded-full capitalize"
                style={{ background: 'var(--color-primary-pale)', color: 'var(--color-primary-dark)' }}>
                {skill}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* ── Bio ────────────────────────────────────────────────────── */}
      {profile.bio.trim() && (
        <div className="flex flex-col gap-2">
          <p className="text-xs font-semibold uppercase tracking-widest" style={{ color: 'var(--color-gray-400)' }}>
            About
          </p>
          <p className="text-sm leading-relaxed" style={{ color: 'var(--color-gray-600)' }}>
            {profile.bio}
          </p>
        </div>
      )}

      {/* ── Edit button ────────────────────────────────────────────── */}
      <div className="pt-2 border-t border-gray-100">
        <button type="button" onClick={onEdit} className="btn-outline w-full justify-center">
          <PencilIcon /> Edit Profile
        </button>
      </div>

    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function Profile() {
  const navigate   = useNavigate()
  const [profile,  setProfile]  = useState(loadProfile)
  const [isEditing, setIsEditing] = useState(() => !hasContent(loadProfile()))
  const [saved,    setSaved]    = useState(false)
  const [finding,  setFinding]  = useState(false)
  const [findError, setFindError] = useState(null)

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
    }, 900)
  }

  async function handleFindJobs() {
    setFindError(null)
    setFinding(true)

    const profileText = [
      profile.fullName   && `My name is ${profile.fullName}.`,
      profile.location   && `I am based in ${profile.location}, Namibia.`,
      profile.experience && `I have ${profile.experience} year${profile.experience !== '1' ? 's' : ''} of experience.`,
      profile.skills.length > 0 && `My skills include: ${profile.skills.join(', ')}.`,
      profile.bio        && profile.bio,
    ].filter(Boolean).join(' ')

    try {
      const res = await api.post('/recommend', { profile_text: profileText })
      navigate('/recommend', { state: { results: res.data, profileText } })
    } catch (err) {
      setFindError(err.response?.data?.detail ?? err.message ?? 'Request failed')
    } finally {
      setFinding(false)
    }
  }

  const canFindJobs = profile.skills.length > 0 || profile.bio.trim().length > 20

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
              ? 'Fill in your details and save — we\'ll use them to find your best job matches.'
              : 'Your saved profile. Click Edit Profile to make changes.'}
          </p>
        </div>
      </section>

      {/* ── Body ────────────────────────────────────────────────────── */}
      <div className="page-container">
        <div className="max-w-2xl mx-auto flex flex-col gap-4">

          {isEditing ? (

            /* ── Edit form ─────────────────────────────────────────── */
            <form key="form" onSubmit={handleSave}
              className="animate-fade-in bg-white rounded-2xl border border-gray-100 shadow-sm p-6 sm:p-8 flex flex-col gap-6">

              {/* Personal info */}
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
                      {NAMIBIAN_CITIES.map(city => (
                        <option key={city} value={city}>{city}</option>
                      ))}
                    </select>
                  </Field>
                  <Field label="Years of Experience">
                    <input type="number" className="input" placeholder="e.g. 3"
                      min="0" max="50" value={profile.experience} onChange={set('experience')} />
                  </Field>
                </div>
              </div>

              {/* Skills */}
              <div>
                <h2 className="text-base font-semibold text-gray-800 mb-4 pb-2 border-b border-gray-100">
                  Skills
                </h2>
                <Field label="Your Skills"
                  hint="Type a skill and press Enter or comma to add it. Backspace removes the last one.">
                  <SkillsInput
                    skills={profile.skills}
                    onChange={skills => setProfile(p => ({ ...p, skills }))}
                  />
                </Field>
              </div>

              {/* Bio */}
              <div>
                <h2 className="text-base font-semibold text-gray-800 mb-4 pb-2 border-b border-gray-100">
                  About You
                </h2>
                <Field label="Bio / Summary"
                  hint="Describe your experience, goals, and what kind of role you're looking for.">
                  <textarea rows={5} className="input resize-none leading-relaxed"
                    placeholder="e.g. I am a software developer with 3 years of experience in Python and FastAPI, looking for a full-time backend role in Windhoek..."
                    value={profile.bio} onChange={set('bio')} />
                </Field>
              </div>

              {/* Save action */}
              <div className="pt-2 border-t border-gray-100">
                <button type="submit" className="btn-primary w-full justify-center">
                  {saved ? <><CheckIcon /> Saved!</> : <><CheckIcon /> Save Profile</>}
                </button>
              </div>

            </form>

          ) : (

            /* ── Profile card ──────────────────────────────────────── */
            <ProfileCard key="card" profile={profile} onEdit={() => setIsEditing(true)} />

          )}

          {/* ── Find Jobs For Me — visible in both views ───────────── */}
          <div className="flex flex-col gap-3">
            <button
              type="button"
              disabled={finding || !canFindJobs}
              onClick={handleFindJobs}
              className="w-full flex items-center justify-center gap-2 font-medium text-sm
                         py-3 px-5 rounded-xl border-none cursor-pointer transition-all duration-150
                         disabled:opacity-50 disabled:cursor-not-allowed"
              style={{
                background: canFindJobs ? 'var(--color-primary-dark)' : 'var(--color-gray-300)',
                color: '#fff',
              }}
            >
              <SparkleIcon />
              {finding ? 'Finding jobs…' : 'Find Jobs For Me'}
            </button>

            {findError && (
              <p className="text-sm text-red-500 bg-red-50 rounded-lg px-4 py-3 border border-red-100">
                {findError} — make sure the backend is running on port 8000.
              </p>
            )}

            {!canFindJobs && (
              <p className="text-xs text-center" style={{ color: 'var(--color-gray-400)' }}>
                Add some skills or a bio to enable job matching.
              </p>
            )}
          </div>

        </div>
      </div>

    </div>
  )
}
