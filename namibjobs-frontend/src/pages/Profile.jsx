import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import * as pdfjsLib from 'pdfjs-dist'
import pdfWorkerSrc from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
import api from '../api'
import { useSavedJobs } from '../hooks/useSavedJobs'
import { useApplications } from '../hooks/useApplications'
import JobCard from '../components/JobCard'
import { avatarColor, initials as getInitials } from '../utils/company'

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorkerSrc

// ── Constants ─────────────────────────────────────────────────────────────────

const STORAGE_KEY = 'namibjobs_profile'

const NAMIBIAN_CITIES = [
  'Windhoek', 'Walvis Bay', 'Swakopmund', 'Oshakati', 'Rundu',
  'Lüderitz', 'Tsumeb', 'Grootfontein', 'Keetmanshoop', 'Otjiwarongo',
  'Mariental', 'Katima Mulilo',
]

const EMPTY_PROFILE = {
  fullName:       '',
  email:          '',
  location:       'Windhoek',
  skills:         [],
  experience:     '',
  bio:            '',
  workExperience: [],
  education:      [],
}

const EMPTY_WORK = { company: '', title: '', duration: '', description: '' }
const EMPTY_EDU  = { institution: '', degree: '', year: '' }

// ── Helpers ───────────────────────────────────────────────────────────────────

function loadProfile() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? { ...EMPTY_PROFILE, ...JSON.parse(raw) } : { ...EMPTY_PROFILE }
  } catch { return { ...EMPTY_PROFILE } }
}

function hasContent(p) {
  return !!(p.fullName || p.email || p.skills.length > 0 || p.bio.trim() ||
            p.workExperience?.length || p.education?.length)
}

function nameInitials(name) {
  if (!name?.trim()) return '?'
  return name.trim().split(/\s+/).map(w => w[0]).slice(0, 2).join('').toUpperCase()
}

function buildProfileText(p) {
  return [
    p.fullName   && `My name is ${p.fullName}.`,
    p.location   && `I am based in ${p.location}, Namibia.`,
    p.experience && `I have ${p.experience} year${p.experience !== '1' ? 's' : ''} of experience.`,
    p.skills.length > 0 && `My skills include: ${p.skills.join(', ')}.`,
    p.bio        && p.bio,
  ].filter(Boolean).join(' ')
}

// ── PDF text extraction ───────────────────────────────────────────────────────

async function extractPdfText(arrayBuffer) {
  const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise
  const pages = []
  for (let p = 1; p <= pdf.numPages; p++) {
    const page = await pdf.getPage(p)
    const { items } = await page.getTextContent()
    pages.push(items.map(i => i.str).join(' '))
  }
  return pages.join('\n')
}

// ── Client-side CV parser ─────────────────────────────────────────────────────

function parseResumeText(text) {
  // Email
  const emailM = text.match(/[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}/)
  const email  = emailM ? emailM[0] : ''

  // Phone
  const phoneM =
    text.match(/(\+?264[-.\s]?)?\(?\d{2,3}\)?[-.\s]?\d{3,4}[-.\s]?\d{4}/) ||
    text.match(/\b(\+\d{1,3}[\s\-]?)?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}\b/)
  const phone = phoneM ? phoneM[0].trim() : ''

  // Full name — first name-like line before email/phone
  const topEnd = Math.min(
    emailM && text.indexOf(emailM[0]) > 0 ? text.indexOf(emailM[0]) : 400,
    phoneM && text.indexOf(phoneM[0]) > 0 ? text.indexOf(phoneM[0]) : 400,
    400,
  )
  const topLines = text.slice(0, topEnd).split('\n').map(l => l.trim()).filter(Boolean)
  const full_name = topLines.find(l =>
    /^[A-Za-zÀ-ž][\wÀ-ž\s\-\.]{1,50}$/.test(l) &&
    l.split(/\s+/).length >= 2 &&
    l.split(/\s+/).length <= 4 &&
    !/@/.test(l) && !/\d/.test(l)
  ) ?? ''

  // Location — Namibian cities
  const CITIES = [
    'Windhoek','Walvis Bay','Swakopmund','Oshakati','Rundu',
    'Lüderitz','Luderitz','Keetmanshoop','Grootfontein','Otjiwarongo',
    'Mariental','Tsumeb','Gobabis','Rehoboth','Ondangwa','Katima Mulilo',
  ]
  const location = CITIES.find(c => new RegExp('\\b' + c + '\\b', 'i').test(text)) ?? ''

  // Years of experience
  const expM =
    text.match(/(\d+)\+?\s+years?(?:\s+of)?\s+(?:experience|exp|work)/i) ||
    text.match(/experience[:\s]+(\d+)\+?\s+years?/i) ||
    text.match(/(\d+)\s+years?\s+(?:professional|industry|working)/i)
  const years_of_experience = expM ? parseInt(expM[1], 10) : 0

  // Skills — 100+ keyword list
  const SKILLS = [
    // Languages
    'python','javascript','typescript','java','c++','c#','php','ruby',
    'swift','kotlin','r','matlab','sql','bash','go','rust','scala',
    // Web / frameworks
    'html','css','react','angular','vue','node.js','django','flask',
    'fastapi','spring','laravel','express','graphql','rest api',
    // Cloud / DevOps
    'git','docker','kubernetes','linux','aws','azure','gcp',
    'terraform','jenkins','ci/cd','devops',
    // Databases
    'postgresql','mysql','mongodb','oracle','redis','sqlite',
    // Data / ML
    'machine learning','deep learning','data science','data analysis',
    'power bi','tableau','excel','tensorflow','pytorch','numpy','pandas',
    'scikit-learn','spss','stata','statistics',
    // Office / ERP
    'microsoft office','word','powerpoint','outlook','sharepoint',
    'sap','erp','sage','pastel','quickbooks','xero','jira','figma',
    // Finance / accounting
    'accounting','bookkeeping','financial reporting','auditing',
    'ifrs','gaap','tax','payroll','budgeting','forecasting',
    'cost accounting','accounts payable','accounts receivable',
    'financial analysis','risk management','compliance','treasury',
    'credit analysis',
    // Business / soft skills
    'project management','leadership','communication','teamwork',
    'problem solving','time management','customer service','sales',
    'marketing','negotiation','stakeholder management',
    'strategic planning','business development','research',
    'report writing','public relations','social media',
    'content creation','digital marketing','seo','brand management',
    // HR
    'recruitment','hr management','labour law','employee relations',
    'training','performance management','compensation','benefits',
    // Supply chain
    'procurement','supply chain','logistics',
    // Engineering
    'autocad','gis','solidworks','scada','surveying',
    'civil engineering','electrical engineering','mechanical engineering',
    'structural engineering','mining','geology',
    'hse','health and safety','quality control','iso standards',
    // Healthcare
    'patient care','clinical assessment','first aid','pharmacy',
    'laboratory testing','radiology','physiotherapy',
    // Education
    'teaching','curriculum development','academic writing','lecturing',
    // Languages / misc
    'afrikaans','oshiwambo','german','agile','scrum','kanban',
    'wordpress','photoshop','illustrator','autocad',
  ]
  const skills = SKILLS.filter(skill => {
    const esc = skill.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    return new RegExp('\\b' + esc + '\\b', 'i').test(text)
  })

  // Education
  const eduRe =
    /(?:bachelor'?s?|master'?s?|diploma|certificate|degree|phd|ph\.d|doctorate|b\.?sc|m\.?sc|b\.?com|m\.?com|b\.?eng|b\.?tech|m\.?ba|llb|b\.a\.?|m\.a\.?)\s*(?:in|of)?\s*[\w\s]{2,50}/gi
  const education = []
  let eduM
  while ((eduM = eduRe.exec(text)) !== null && education.length < 4) {
    const degree  = eduM[0].replace(/\s+/g, ' ').trim().slice(0, 80)
    const around  = text.slice(Math.max(0, eduM.index - 300), eduM.index + 300)
    const instM   = around.match(
      /(?:university|college|institute|school|academy|polytechnic|nust|unam)[^\n,;]{0,60}/i
    )
    const yearM   = around.match(/\b(19|20)\d{2}\b/)
    education.push({
      degree,
      institution: instM ? instM[0].replace(/\s+/g, ' ').trim().slice(0, 80) : '',
      year:        yearM ? yearM[0] : '',
    })
  }

  // Work experience — anchored on date ranges
  const dateRe =
    /(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+)?(20\d{2}|19\d{2})\s*[-–—]\s*(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+)?(20\d{2}|19\d{2}|present|current|now)/gi
  const work_experience = []
  let workM
  while ((workM = dateRe.exec(text)) !== null && work_experience.length < 5) {
    const duration = workM[0].trim()
    const before   = text.slice(Math.max(0, workM.index - 250), workM.index)
    const after    = text.slice(workM.index + duration.length, workM.index + duration.length + 250)
    const bLines   = before.split('\n').map(l => l.trim()).filter(Boolean)
    const aLines   = after.split('\n').map(l => l.trim()).filter(Boolean)
    work_experience.push({
      title:       (bLines.at(-1) ?? '').slice(0, 80),
      company:     (bLines.at(-2) ?? '').slice(0, 80),
      duration,
      description: aLines.slice(0, 2).join(' ').slice(0, 200),
    })
  }

  return { full_name, email, phone, location, years_of_experience, skills, bio: '', work_experience, education }
}

// ── Icons ─────────────────────────────────────────────────────────────────────

const icon = (d, size = 15, extra = '') => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
    dangerouslySetInnerHTML={{ __html: d }} className={extra} />
)

function UserIcon()     { return icon('<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>', 22) }
function MailIcon()     { return icon('<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>') }
function MapPinIcon()   { return icon('<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>') }
function BriefcaseIcon(){ return icon('<rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/><path d="M2 12h20"/>') }
function PencilIcon()   { return icon('<path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/>') }
function CheckIcon()    { return icon('<polyline points="20 6 9 17 4 12"/>', 16) }
function SparkleIcon()  { return icon('<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>', 16) }
function ArrowIcon()    { return icon('<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>') }
function RefreshIcon()  { return icon('<polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>') }
function PrinterIcon()  { return icon('<polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/>') }
function UploadIcon()   { return icon('<polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/>', 22) }
function FileIcon()     { return icon('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>', 22) }
function PlusIcon()     { return icon('<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>') }
function TrashIcon()    { return icon('<polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>') }

function Spinner({ label = 'Loading…' }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-3">
      <div className="w-9 h-9 rounded-full border-2 border-gray-200 animate-spin"
        style={{ borderTopColor: 'var(--color-primary)' }} />
      <p className="text-sm text-gray-400">{label}</p>
    </div>
  )
}

// ── Small shared components ───────────────────────────────────────────────────

function ResumeSection({ title, children }) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-3">
        <h3 className="text-xs font-semibold uppercase tracking-widest shrink-0"
          style={{ color: 'var(--color-primary-dark)' }}>{title}</h3>
        <div className="flex-1 h-px" style={{ background: 'var(--color-primary-light)' }} />
      </div>
      {children}
    </div>
  )
}

function InfoChip({ icon: Ic, text }) {
  return (
    <span className="flex items-center gap-1.5 text-xs" style={{ color: 'var(--color-gray-500)' }}>
      <span style={{ color: 'var(--color-primary)' }}><Ic /></span>
      {text}
    </span>
  )
}

// ── Skills tag input ──────────────────────────────────────────────────────────

function SkillsInput({ skills, onChange }) {
  const [input, setInput] = useState('')
  const ref = useRef(null)

  function addSkill(raw) {
    const s = raw.trim().toLowerCase()
    if (s && !skills.includes(s)) onChange([...skills, s])
    setInput('')
  }

  function onKeyDown(e) {
    if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); addSkill(input) }
    else if (e.key === 'Backspace' && !input && skills.length > 0) onChange(skills.slice(0, -1))
  }

  return (
    <div className="flex flex-wrap gap-1.5 p-2 rounded-lg bg-white cursor-text min-h-[44px]"
      style={{ border: '1.5px solid var(--color-gray-200)' }}
      onClick={() => ref.current?.focus()}>
      {skills.map(s => (
        <span key={s} className="flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-full capitalize"
          style={{ background: 'var(--color-primary-pale)', color: 'var(--color-primary-dark)' }}>
          {s}
          <button type="button" onClick={e => { e.stopPropagation(); onChange(skills.filter(x => x !== s)) }}
            className="hover:opacity-60 leading-none text-base" aria-label={`Remove ${s}`}>×</button>
        </span>
      ))}
      <input ref={ref} type="text" value={input} onChange={e => setInput(e.target.value)}
        onKeyDown={onKeyDown} onBlur={() => input.trim() && addSkill(input)}
        placeholder={skills.length === 0 ? 'Type a skill and press Enter…' : ''}
        className="flex-1 min-w-[140px] text-sm outline-none bg-transparent text-gray-700 placeholder:text-gray-300 py-0.5" />
    </div>
  )
}

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
          }}>
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

// ── Resume drop zone ──────────────────────────────────────────────────────────

const ACCEPTED_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
]

function ResumeDropZone({ onParsed }) {
  const [file,    setFile]    = useState(null)
  const [drag,    setDrag]    = useState(false)
  const [parsing, setParsing] = useState(false)
  const [err,     setErr]     = useState(null)
  const [ok,      setOk]      = useState(false)
  const inputRef = useRef(null)

  function acceptFile(f) {
    const valid = ACCEPTED_TYPES.includes(f.type) ||
                  f.name.match(/\.(pdf|docx)$/i)
    if (!valid) { setErr('Only PDF and DOCX files are accepted.'); return }
    setFile(f); setErr(null); setOk(false)
  }

  function onDrop(e) {
    e.preventDefault(); setDrag(false)
    if (e.dataTransfer.files[0]) acceptFile(e.dataTransfer.files[0])
  }

  async function handleParse() {
    if (!file) return
    setParsing(true); setErr(null)
    try {
      const isPdf = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')
      let text

      if (isPdf) {
        const arrayBuffer = await file.arrayBuffer()
        text = await extractPdfText(arrayBuffer)
      } else {
        const arrayBuffer = await file.arrayBuffer()
        const { default: mammoth } = await import('mammoth')
        const { value } = await mammoth.extractRawText({ arrayBuffer })
        text = value
      }

      if (!text?.trim()) throw new Error('Could not extract text from this file.')
      const parsed = parseResumeText(text)
      onParsed(parsed)
      setOk(true)
    } catch (e) {
      setErr(e.message ?? 'Failed to parse resume')
    } finally {
      setParsing(false)
    }
  }

  const sizeKB = file ? `${(file.size / 1024).toFixed(0)} KB` : ''

  return (
    <div className="flex flex-col gap-3">
      {/* Drop zone */}
      <div
        onDragOver={e => { e.preventDefault(); setDrag(true) }}
        onDragLeave={() => setDrag(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className="flex flex-col items-center justify-center gap-2 p-8 rounded-xl border-2 border-dashed cursor-pointer transition-all duration-150 select-none"
        style={{
          borderColor: drag ? 'var(--color-primary)' : 'var(--color-gray-200)',
          background:  drag ? 'var(--color-primary-pale)' : 'var(--color-gray-50)',
        }}>
        <input ref={inputRef} type="file" className="hidden"
          accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          onChange={e => e.target.files[0] && acceptFile(e.target.files[0])} />

        {file ? (
          <>
            <span style={{ color: 'var(--color-primary)' }}><FileIcon /></span>
            <p className="text-sm font-medium text-gray-700 text-center break-all">{file.name}</p>
            <p className="text-xs text-gray-400">
              {sizeKB} ·{' '}
              <button type="button" className="underline" onClick={e => { e.stopPropagation(); setFile(null); setOk(false) }}>
                Remove
              </button>
            </p>
          </>
        ) : (
          <>
            <span style={{ color: 'var(--color-gray-400)' }}><UploadIcon /></span>
            <div className="text-center">
              <p className="text-sm font-medium text-gray-700">Drag & drop your resume</p>
              <p className="text-xs text-gray-400 mt-0.5">
                or <span className="underline" style={{ color: 'var(--color-primary-dark)' }}>click to browse</span>
              </p>
            </div>
            <p className="text-xs text-gray-400">PDF or DOCX · max 10 MB</p>
          </>
        )}
      </div>

      {err && (
        <p className="text-xs text-red-500 bg-red-50 rounded-lg px-3 py-2 border border-red-100">{err}</p>
      )}

      {ok && (
        <div className="flex items-center gap-2 text-xs font-medium px-3 py-2 rounded-lg"
          style={{ background: 'var(--color-primary-pale)', color: 'var(--color-primary-dark)' }}>
          <CheckIcon /> Profile built from your CV — review and save below.
        </div>
      )}

      {file && !ok && (
        <button type="button" onClick={handleParse} disabled={parsing}
          className="btn-primary w-full justify-center disabled:opacity-50">
          {parsing ? (
            <>
              <div className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
              Analysing resume…
            </>
          ) : (
            <><SparkleIcon /> Build Profile From Resume</>
          )}
        </button>
      )}
    </div>
  )
}

// ── Overview tab (resume view) ────────────────────────────────────────────────

function OverviewTab({ profile, onEdit, onFindJobs, finding, findError, canFindJobs }) {
  const initials = nameInitials(profile.fullName)

  return (
    <div className="flex flex-col gap-8">

      {/* ── Print-friendly resume ────────────────────────────────────── */}
      <div id="resume-print-area">

        {/* Header */}
        <div className="flex items-start gap-5 pb-6 border-b border-gray-100">
          <div className="w-16 h-16 rounded-full flex items-center justify-center text-xl font-bold text-white shrink-0 select-none no-print"
            style={{ background: 'var(--color-primary)' }}>
            {initials}
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="text-2xl font-bold text-gray-900 leading-snug">
              {profile.fullName || <span className="font-normal italic text-base text-gray-400">No name set</span>}
            </h2>
            <div className="flex flex-wrap gap-x-5 gap-y-1.5 mt-2">
              {profile.email     && <InfoChip icon={MailIcon}       text={profile.email} />}
              {profile.location  && <InfoChip icon={MapPinIcon}     text={`${profile.location}, Namibia`} />}
              {profile.experience && <InfoChip icon={BriefcaseIcon} text={`${profile.experience} yr${profile.experience !== '1' ? 's' : ''} experience`} />}
            </div>
          </div>
        </div>

        {/* Professional Summary */}
        {profile.bio?.trim() && (
          <div className="mt-6">
            <ResumeSection title="Professional Summary">
              <p className="text-sm leading-relaxed" style={{ color: 'var(--color-gray-600)' }}>{profile.bio}</p>
            </ResumeSection>
          </div>
        )}

        {/* Skills */}
        {profile.skills?.length > 0 && (
          <div className="mt-6">
            <ResumeSection title="Skills">
              <div className="flex flex-wrap gap-2">
                {profile.skills.map(s => (
                  <span key={s} className="text-xs font-medium px-3 py-1.5 rounded-full capitalize"
                    style={{ background: 'var(--color-primary-pale)', color: 'var(--color-primary-dark)' }}>
                    {s}
                  </span>
                ))}
              </div>
            </ResumeSection>
          </div>
        )}

        {/* Work Experience */}
        {profile.workExperience?.length > 0 && (
          <div className="mt-6">
            <ResumeSection title="Work Experience">
              <div className="flex flex-col gap-5 mt-1">
                {profile.workExperience.map((exp, i) => (
                  <div key={i} className="relative pl-5 border-l-2"
                    style={{ borderColor: 'var(--color-primary-light)' }}>
                    <div className="absolute -left-[5px] top-1.5 w-2.5 h-2.5 rounded-full"
                      style={{ background: 'var(--color-primary)' }} />
                    <div className="flex items-start justify-between gap-2 flex-wrap">
                      <div>
                        <p className="text-sm font-semibold text-gray-900">{exp.title}</p>
                        <p className="text-sm font-medium mt-0.5" style={{ color: 'var(--color-primary-dark)' }}>
                          {exp.company}
                        </p>
                      </div>
                      {exp.duration && (
                        <span className="text-xs shrink-0 mt-0.5" style={{ color: 'var(--color-gray-400)' }}>
                          {exp.duration}
                        </span>
                      )}
                    </div>
                    {exp.description && (
                      <p className="text-sm mt-1.5 leading-relaxed" style={{ color: 'var(--color-gray-500)' }}>
                        {exp.description}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </ResumeSection>
          </div>
        )}

        {/* Education */}
        {profile.education?.length > 0 && (
          <div className="mt-6">
            <ResumeSection title="Education">
              <div className="flex flex-col gap-4 mt-1">
                {profile.education.map((edu, i) => (
                  <div key={i} className="flex items-start justify-between gap-2">
                    <div>
                      <p className="text-sm font-semibold text-gray-900">{edu.degree}</p>
                      <p className="text-sm mt-0.5" style={{ color: 'var(--color-gray-500)' }}>
                        {edu.institution}
                      </p>
                    </div>
                    {edu.year && (
                      <span className="text-xs shrink-0 mt-0.5" style={{ color: 'var(--color-gray-400)' }}>
                        {edu.year}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </ResumeSection>
          </div>
        )}

        {/* Empty state */}
        {!hasContent(profile) && (
          <div className="text-center py-10 text-gray-400">
            <p className="font-medium text-gray-600 mb-1">Your profile is empty</p>
            <p className="text-sm">Click Edit Profile to fill in your details.</p>
          </div>
        )}

      </div>{/* end #resume-print-area */}

      {/* ── Actions ─────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-3 pt-4 border-t border-gray-100 no-print">

        <button type="button" onClick={() => window.print()}
          className="btn-outline w-full justify-center">
          <PrinterIcon /> Download Resume View
        </button>

        <button type="button" onClick={onFindJobs} disabled={finding || !canFindJobs}
          className="w-full flex items-center justify-center gap-2 font-medium text-sm py-3 px-5 rounded-xl border-none cursor-pointer transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
          style={{ background: canFindJobs ? 'var(--color-primary-dark)' : 'var(--color-gray-300)', color: '#fff' }}>
          <SparkleIcon /> {finding ? 'Finding jobs…' : 'Find Jobs For Me'}
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
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
          </svg>
        </div>
        <div>
          <p className="font-medium text-gray-700">No saved jobs yet</p>
          <p className="text-sm text-gray-400 mt-1">Browse jobs and click the bookmark icon to save them.</p>
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
        <JobCard key={job.id} id={job.id} title={job.title} company={job.company}
          location={job.location} description={job.description} skills={job.skills ?? []}
          jobType={job.job_type} salary={job.salary} sourceUrl={job.source_url}
          matchScore={job.match_score ?? null} isSaved={true} onBookmark={toggle} onApply={apply} />
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
          <p className="text-sm text-gray-400 mt-1">Jobs you apply for will appear here.</p>
        </div>
      </div>
    )
  }
  return (
    <div className="flex flex-col gap-3">
      {[...applications].reverse().map(app => {
        const [bg, fg] = avatarColor(app.company ?? '')
        const dateStr  = new Date(app.appliedAt).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
        return (
          <div key={app.id} className="flex items-center gap-4 p-4 bg-white rounded-xl border border-gray-100 shadow-sm">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center text-sm font-bold shrink-0"
              style={{ background: bg, color: fg }}>{getInitials(app.company ?? '')}</div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-gray-900 truncate">{app.title}</p>
              <p className="text-xs text-gray-500 mt-0.5 truncate">{app.company}</p>
              <p className="text-xs mt-1" style={{ color: 'var(--color-gray-400)' }}>Applied {dateStr}</p>
            </div>
            <span className="badge badge-green shrink-0">Applied</span>
          </div>
        )
      })}
    </div>
  )
}

// ── Recommendations tab ───────────────────────────────────────────────────────

function RecommendationsTab({ profile, isSaved, toggle, apply }) {
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState(null)

  const canRefresh = profile.skills.length > 0 || profile.bio.trim().length > 20

  async function handleRefresh() {
    setLoading(true); setError(null)
    const profileText = buildProfileText(profile)
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
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-gray-100">
        <div>
          <p className="text-sm font-semibold text-gray-800">AI-Powered Matches</p>
          <p className="text-xs mt-0.5" style={{ color: 'var(--color-gray-400)' }}>Based on your profile skills and bio</p>
        </div>
        <button onClick={handleRefresh} disabled={loading || !canRefresh}
          className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed">
          <RefreshIcon /> {loading ? 'Searching…' : 'Refresh My Recommendations'}
        </button>
      </div>
      {!canRefresh && (
        <p className="text-xs text-center" style={{ color: 'var(--color-gray-400)' }}>
          Add skills or a bio to your profile to enable recommendations.
        </p>
      )}
      {loading && <Spinner label="Finding your matches…" />}
      {error && (
        <div className="rounded-xl p-4 text-sm text-red-600 bg-red-50 border border-red-100">
          <strong>Something went wrong.</strong> Make sure the backend is running on port 8000.
          <br /><span className="text-red-400">{error}</span>
        </div>
      )}
      {!loading && sorted?.length === 0 && (
        <p className="text-center py-10 text-sm text-gray-400">No matching jobs found. Try updating your profile.</p>
      )}
      {!loading && sorted?.length > 0 && (
        <>
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-gray-700">Top {sorted.length} matches</p>
            <span className="text-2xl font-bold" style={{ color: 'var(--color-primary)' }}>
              {sorted[0].match_score}%<span className="text-xs font-normal text-gray-400 ml-1">best match</span>
            </span>
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            {sorted.map(job => (
              <JobCard key={job.id} id={job.id} title={job.title} company={job.company}
                location={job.location} skills={job.skills ?? []} jobType={job.job_type}
                matchScore={job.match_score} sourceUrl={job.source_url}
                isSaved={isSaved(job.id)} onBookmark={toggle} onApply={apply} />
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
  const navigate = useNavigate()

  const [profile,   setProfile]   = useState(loadProfile)
  const [isEditing, setIsEditing] = useState(() => !hasContent(loadProfile()))
  const [activeTab, setActiveTab] = useState('overview')
  const [saved,     setSaved]     = useState(false)
  const [finding,   setFinding]   = useState(false)
  const [findError, setFindError] = useState(null)

  const { saved: savedJobs, toggle, isSaved } = useSavedJobs()
  const { applications, apply }               = useApplications()

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(profile))
  }, [profile])

  // ── Field setters ──────────────────────────────────────────────────────────

  function set(field) { return e => setProfile(p => ({ ...p, [field]: e.target.value })) }

  function updateWorkExp(i, field, val) {
    setProfile(p => {
      const list = [...(p.workExperience ?? [])]
      list[i] = { ...list[i], [field]: val }
      return { ...p, workExperience: list }
    })
  }
  function addWorkExp()    { setProfile(p => ({ ...p, workExperience: [...(p.workExperience ?? []), { ...EMPTY_WORK }] })) }
  function removeWorkExp(i){ setProfile(p => ({ ...p, workExperience: (p.workExperience ?? []).filter((_, idx) => idx !== i) })) }

  function updateEdu(i, field, val) {
    setProfile(p => {
      const list = [...(p.education ?? [])]
      list[i] = { ...list[i], [field]: val }
      return { ...p, education: list }
    })
  }
  function addEdu()    { setProfile(p => ({ ...p, education: [...(p.education ?? []), { ...EMPTY_EDU }] })) }
  function removeEdu(i){ setProfile(p => ({ ...p, education: (p.education ?? []).filter((_, idx) => idx !== i) })) }

  // ── Apply parsed resume ────────────────────────────────────────────────────

  function applyParsed(parsed) {
    setProfile(p => ({
      ...p,
      fullName:       parsed.full_name        || p.fullName,
      email:          parsed.email            || p.email,
      location:       parsed.location         || p.location,
      experience:     parsed.years_of_experience != null
                        ? String(parsed.years_of_experience) : p.experience,
      skills:         parsed.skills?.length
                        ? parsed.skills.map(s => s.toLowerCase().trim()) : p.skills,
      bio:            parsed.bio              || p.bio,
      workExperience: parsed.work_experience?.length
                        ? parsed.work_experience.map(w => ({
                            company:     w.company     ?? '',
                            title:       w.title       ?? '',
                            duration:    w.duration    ?? '',
                            description: w.description ?? '',
                          }))
                        : p.workExperience,
      education:      parsed.education?.length
                        ? parsed.education.map(e => ({
                            institution: e.institution ?? '',
                            degree:      e.degree      ?? '',
                            year:        String(e.year ?? ''),
                          }))
                        : p.education,
    }))
  }

  // ── Handlers ──────────────────────────────────────────────────────────────

  function handleSave(e) {
    e.preventDefault()
    localStorage.setItem(STORAGE_KEY, JSON.stringify(profile))
    setSaved(true)
    setTimeout(() => { setSaved(false); setIsEditing(false); setActiveTab('overview') }, 900)
  }

  async function handleFindJobs() {
    setFinding(true); setFindError(null)
    const profileText = buildProfileText(profile)
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

  const TABS = [
    { id: 'overview',        label: 'Overview' },
    { id: 'saved',           label: 'Saved Jobs',   count: savedJobs.length },
    { id: 'applications',    label: 'Applications', count: applications.length },
    { id: 'recommendations', label: 'Recommendations' },
  ]

  // ── Section heading ────────────────────────────────────────────────────────

  function SectionH({ children }) {
    return (
      <h2 className="text-base font-semibold text-gray-800 mb-4 pb-2 border-b border-gray-100">
        {children}
      </h2>
    )
  }

  function AddBtn({ onClick, children }) {
    return (
      <button type="button" onClick={onClick}
        className="text-sm font-medium flex items-center gap-1.5 px-4 py-2.5 rounded-xl border border-dashed w-full justify-center transition-colors duration-150"
        style={{ borderColor: 'var(--color-primary-light)', color: 'var(--color-primary-dark)' }}
        onMouseEnter={e => e.currentTarget.style.background = 'var(--color-primary-pale)'}
        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
        <PlusIcon /> {children}
      </button>
    )
  }

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
              ? 'Fill in your details or upload your resume — we\'ll use them to find your best matches.'
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
              className="animate-fade-in bg-white rounded-2xl border border-gray-100 shadow-sm p-6 sm:p-8 flex flex-col gap-8">

              {/* Resume upload */}
              <div>
                <SectionH>Resume Upload</SectionH>
                <ResumeDropZone onParsed={applyParsed} />
              </div>

              {/* Personal info */}
              <div>
                <SectionH>Personal Information</SectionH>
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
                      {NAMIBIAN_CITIES.map(c => <option key={c} value={c}>{c}</option>)}
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
                <SectionH>Skills</SectionH>
                <Field label="Your Skills"
                  hint="Type a skill and press Enter or comma to add it.">
                  <SkillsInput skills={profile.skills}
                    onChange={skills => setProfile(p => ({ ...p, skills }))} />
                </Field>
              </div>

              {/* Bio */}
              <div>
                <SectionH>Professional Summary</SectionH>
                <Field label="Bio / Summary"
                  hint="Describe your experience, goals, and what kind of role you're looking for.">
                  <textarea rows={4} className="input resize-none leading-relaxed"
                    placeholder="e.g. I am a software developer with 3 years of experience in Python and FastAPI, looking for a full-time backend role in Windhoek..."
                    value={profile.bio} onChange={set('bio')} />
                </Field>
              </div>

              {/* Work Experience */}
              <div>
                <SectionH>Work Experience</SectionH>
                <div className="flex flex-col gap-4">
                  {(profile.workExperience ?? []).map((exp, i) => (
                    <div key={i} className="p-4 rounded-xl border border-gray-200 flex flex-col gap-3">
                      <div className="flex items-center justify-between">
                        <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Role {i + 1}</p>
                        <button type="button" onClick={() => removeWorkExp(i)}
                          className="text-xs text-red-400 hover:text-red-600 flex items-center gap-1 transition-colors">
                          <TrashIcon /> Remove
                        </button>
                      </div>
                      <div className="grid sm:grid-cols-2 gap-3">
                        <Field label="Job Title">
                          <input type="text" className="input" placeholder="e.g. Software Engineer"
                            value={exp.title} onChange={e => updateWorkExp(i, 'title', e.target.value)} />
                        </Field>
                        <Field label="Company">
                          <input type="text" className="input" placeholder="e.g. Telecom Namibia"
                            value={exp.company} onChange={e => updateWorkExp(i, 'company', e.target.value)} />
                        </Field>
                      </div>
                      <Field label="Duration">
                        <input type="text" className="input" placeholder="e.g. Jan 2020 – Present"
                          value={exp.duration} onChange={e => updateWorkExp(i, 'duration', e.target.value)} />
                      </Field>
                      <Field label="Description">
                        <textarea rows={2} className="input resize-none leading-relaxed"
                          placeholder="Brief description of your role and achievements..."
                          value={exp.description} onChange={e => updateWorkExp(i, 'description', e.target.value)} />
                      </Field>
                    </div>
                  ))}
                  <AddBtn onClick={addWorkExp}>Add Work Experience</AddBtn>
                </div>
              </div>

              {/* Education */}
              <div>
                <SectionH>Education</SectionH>
                <div className="flex flex-col gap-4">
                  {(profile.education ?? []).map((edu, i) => (
                    <div key={i} className="p-4 rounded-xl border border-gray-200 flex flex-col gap-3">
                      <div className="flex items-center justify-between">
                        <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Education {i + 1}</p>
                        <button type="button" onClick={() => removeEdu(i)}
                          className="text-xs text-red-400 hover:text-red-600 flex items-center gap-1 transition-colors">
                          <TrashIcon /> Remove
                        </button>
                      </div>
                      <Field label="Institution">
                        <input type="text" className="input" placeholder="e.g. University of Namibia"
                          value={edu.institution} onChange={e => updateEdu(i, 'institution', e.target.value)} />
                      </Field>
                      <div className="grid sm:grid-cols-2 gap-3">
                        <Field label="Degree / Qualification">
                          <input type="text" className="input" placeholder="e.g. BSc Computer Science"
                            value={edu.degree} onChange={e => updateEdu(i, 'degree', e.target.value)} />
                        </Field>
                        <Field label="Year">
                          <input type="text" className="input" placeholder="e.g. 2022"
                            value={edu.year} onChange={e => updateEdu(i, 'year', e.target.value)} />
                        </Field>
                      </div>
                    </div>
                  ))}
                  <AddBtn onClick={addEdu}>Add Education</AddBtn>
                </div>
              </div>

              {/* Save / Cancel */}
              <div className="flex flex-col sm:flex-row gap-3 pt-2 border-t border-gray-100">
                {hasContent(profile) && (
                  <button type="button" onClick={() => setIsEditing(false)}
                    className="btn-outline flex-1 justify-center">Cancel</button>
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
                  <OverviewTab profile={profile} onEdit={() => setIsEditing(true)}
                    onFindJobs={handleFindJobs} finding={finding}
                    findError={findError} canFindJobs={canFindJobs} />
                )}
                {activeTab === 'saved' && (
                  <SavedJobsTab savedJobs={savedJobs} toggle={toggle} apply={apply} />
                )}
                {activeTab === 'applications' && (
                  <ApplicationsTab applications={applications} />
                )}
                {activeTab === 'recommendations' && (
                  <RecommendationsTab profile={profile} isSaved={isSaved} toggle={toggle} apply={apply} />
                )}
              </div>
            </div>

          )}
        </div>
      </div>
    </div>
  )
}
