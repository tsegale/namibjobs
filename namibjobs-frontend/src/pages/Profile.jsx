import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api'

const STORAGE_KEY = 'namibjobs_profile'

const NAMIBIAN_CITIES = [
  'Windhoek',
  'Walvis Bay',
  'Swakopmund',
  'Oshakati',
  'Rundu',
  'Lüderitz',
  'Tsumeb',
  'Grootfontein',
  'Keetmanshoop',
  'Otjiwarongo',
  'Mariental',
  'Katima Mulilo',
]

const EMPTY_PROFILE = {
  fullName:    '',
  email:       '',
  location:    'Windhoek',
  skills:      [],
  experience:  '',
  bio:         '',
}

function loadProfile() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? { ...EMPTY_PROFILE, ...JSON.parse(raw) } : { ...EMPTY_PROFILE }
  } catch {
    return { ...EMPTY_PROFILE }
  }
}

// ── Icons ────────────────────────────────────────────────────────────────────

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

function UserIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  )
}

// ── Skills tag input ──────────────────────────────────────────────────────────

function SkillsInput({ skills, onChange }) {
  const [input, setInput] = useState('')
  const inputRef = useRef(null)

  function addSkill(raw) {
    const skill = raw.trim().toLowerCase()
    if (skill && !skills.includes(skill)) {
      onChange([...skills, skill])
    }
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

  function removeSkill(skill) {
    onChange(skills.filter(s => s !== skill))
  }

  return (
    <div
      className="flex flex-wrap gap-1.5 p-2 rounded-lg border-1.5 border-gray-200 bg-white cursor-text min-h-[44px]"
      style={{ border: '1.5px solid var(--color-gray-200)' }}
      onClick={() => inputRef.current?.focus()}
    >
      {skills.map(skill => (
        <span
          key={skill}
          className="flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-full capitalize"
          style={{ background: 'var(--color-primary-pale)', color: 'var(--color-primary-dark)' }}
        >
          {skill}
          <button
            type="button"
            onClick={e => { e.stopPropagation(); removeSkill(skill) }}
            className="hover:opacity-60 leading-none text-base"
            aria-label={`Remove ${skill}`}
          >
            ×
          </button>
        </span>
      ))}
      <input
        ref={inputRef}
        type="text"
        value={input}
        onChange={e => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={() => input.trim() && addSkill(input)}
        placeholder={skills.length === 0 ? 'Type a skill and press Enter…' : ''}
        className="flex-1 min-w-[140px] text-sm outline-none bg-transparent text-gray-700
                   placeholder:text-gray-300 py-0.5"
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

// ── Page ──────────────────────────────────────────────────────────────────────

export default function Profile() {
  const navigate  = useNavigate()
  const [profile, setProfile] = useState(loadProfile)
  const [saved,   setSaved]   = useState(false)
  const [finding, setFinding] = useState(false)
  const [findError, setFindError] = useState(null)

  // Persist to localStorage on every change
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
    setTimeout(() => setSaved(false), 2500)
  }

  async function handleFindJobs(e) {
    e.preventDefault()
    setFindError(null)
    setFinding(true)

    const profileText = [
      profile.fullName && `My name is ${profile.fullName}.`,
      profile.location && `I am based in ${profile.location}, Namibia.`,
      profile.experience && `I have ${profile.experience} year${profile.experience !== '1' ? 's' : ''} of experience.`,
      profile.skills.length > 0 && `My skills include: ${profile.skills.join(', ')}.`,
      profile.bio && profile.bio,
    ]
      .filter(Boolean)
      .join(' ')

    try {
      const res = await api.post('/recommend', { profile_text: profileText })
      navigate('/recommend', {
        state: { results: res.data, profileText },
      })
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
          <p className="text-gray-400 text-sm">
            Your details are saved locally and used to find matching jobs.
          </p>
        </div>
      </section>

      {/* ── Form ────────────────────────────────────────────────────── */}
      <div className="page-container">
        <div className="max-w-2xl mx-auto">
          <form onSubmit={handleSave} className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 sm:p-8 flex flex-col gap-6">

            {/* Personal info */}
            <div>
              <h2 className="text-base font-semibold text-gray-800 mb-4 pb-2 border-b border-gray-100">
                Personal Information
              </h2>
              <div className="grid sm:grid-cols-2 gap-4">
                <Field label="Full Name">
                  <input
                    type="text"
                    className="input"
                    placeholder="e.g. James Parata"
                    value={profile.fullName}
                    onChange={set('fullName')}
                  />
                </Field>

                <Field label="Email">
                  <input
                    type="email"
                    className="input"
                    placeholder="you@example.com"
                    value={profile.email}
                    onChange={set('email')}
                  />
                </Field>

                <Field label="Location">
                  <select
                    className="input bg-white"
                    value={profile.location}
                    onChange={set('location')}
                  >
                    {NAMIBIAN_CITIES.map(city => (
                      <option key={city} value={city}>{city}</option>
                    ))}
                  </select>
                </Field>

                <Field label="Years of Experience">
                  <input
                    type="number"
                    className="input"
                    placeholder="e.g. 3"
                    min="0"
                    max="50"
                    value={profile.experience}
                    onChange={set('experience')}
                  />
                </Field>
              </div>
            </div>

            {/* Skills */}
            <div>
              <h2 className="text-base font-semibold text-gray-800 mb-4 pb-2 border-b border-gray-100">
                Skills
              </h2>
              <Field
                label="Your Skills"
                hint="Type a skill and press Enter or comma to add it. Backspace to remove the last one."
              >
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
              <Field
                label="Bio / Summary"
                hint="Describe your experience, goals, and what kind of role you're looking for."
              >
                <textarea
                  rows={5}
                  className="input resize-none leading-relaxed"
                  placeholder="e.g. I am a software developer with 3 years of experience in Python and FastAPI, looking for a full-time backend role in Windhoek..."
                  value={profile.bio}
                  onChange={set('bio')}
                />
              </Field>
            </div>

            {/* Actions */}
            <div className="flex flex-col sm:flex-row gap-3 pt-2 border-t border-gray-100">
              <button
                type="submit"
                className="btn-primary flex-1 justify-center"
              >
                {saved ? <><CheckIcon /> Saved!</> : <><CheckIcon /> Save Profile</>}
              </button>

              <button
                type="button"
                disabled={finding || !canFindJobs}
                onClick={handleFindJobs}
                className="flex-1 justify-center flex items-center gap-2 font-medium text-sm
                           py-2.5 px-5 rounded-lg border-none cursor-pointer transition-all duration-150
                           disabled:opacity-50 disabled:cursor-not-allowed"
                style={{
                  background: canFindJobs ? 'var(--color-primary-dark)' : 'var(--color-gray-200)',
                  color: '#fff',
                }}
              >
                <SparkleIcon />
                {finding ? 'Finding jobs…' : 'Find Jobs For Me'}
              </button>
            </div>

            {findError && (
              <p className="text-sm text-red-500 bg-red-50 rounded-lg px-4 py-3 border border-red-100">
                {findError} — make sure the backend is running on port 8000.
              </p>
            )}

            {!canFindJobs && (
              <p className="text-xs text-gray-400 text-center -mt-3">
                Add some skills or a bio to enable job matching.
              </p>
            )}

          </form>
        </div>
      </div>
    </div>
  )
}
