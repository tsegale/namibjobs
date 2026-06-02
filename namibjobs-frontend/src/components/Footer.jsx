import { Link } from 'react-router-dom'
import logo from '../assets/namibjobslogo.png'

function SparkleIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
    </svg>
  )
}

const COLUMNS = [
  {
    heading: 'Platform',
    links: [
      { label: 'Jobs',            to: '/jobs' },
      { label: 'Companies',       to: '/companies' },
      { label: 'Recommendations', to: '/recommend' },
    ],
  },
  {
    heading: 'Account',
    links: [
      { label: 'My Profile',  to: '/profile' },
      { label: 'Saved Jobs',  to: '/profile' },
    ],
  },
  {
    heading: 'About',
    links: [
      { label: 'About NamibJobs', to: '/' },
      { label: 'Contact',         to: '/' },
    ],
  },
]

export default function Footer() {
  return (
    <footer
      style={{
        background: 'var(--color-surface)',
        borderTop: '1.5px solid #9FE1CB',
      }}
    >
      {/* ── Main content ──────────────────────────────────────────────── */}
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-12">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-10">

          {/* Brand column */}
          <div className="sm:col-span-2 lg:col-span-1 flex flex-col gap-3">
            <Link to="/" className="w-fit hover:opacity-80 transition-opacity">
              <img src={logo} alt="NamibJobs" className="h-12 w-auto" />
            </Link>

            <p className="text-xs mt-1" style={{ color: 'var(--color-gray-400)' }}>
              Connecting Namibia's talent with<br />the country's best employers.
            </p>
          </div>

          {/* Link columns */}
          {COLUMNS.map(col => (
            <div key={col.heading} className="flex flex-col gap-3">
              <h4
                className="text-xs font-semibold uppercase tracking-widest"
                style={{ color: 'var(--color-primary-dark)' }}
              >
                {col.heading}
              </h4>
              <ul className="flex flex-col gap-2.5 list-none p-0 m-0">
                {col.links.map(link => (
                  <li key={link.label}>
                    <Link
                      to={link.to}
                      className="text-sm transition-colors duration-150"
                      style={{ color: 'var(--color-gray-500)' }}
                      onMouseEnter={e => e.currentTarget.style.color = 'var(--color-primary-dark)'}
                      onMouseLeave={e => e.currentTarget.style.color = 'var(--color-gray-500)'}
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}

        </div>
      </div>

      {/* ── Bottom bar ────────────────────────────────────────────────── */}
      <div style={{ borderTop: '1px solid #C8F0E2' }}>
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span className="text-xs" style={{ color: 'var(--color-gray-400)' }}>
            © 2025 NamibJobs. Built for Namibia.
          </span>
          <span
            className="flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full"
            style={{
              background: 'var(--color-primary-pale)',
              color: 'var(--color-primary-dark)',
            }}
          >
            <SparkleIcon />
            Powered by AI
          </span>
        </div>
      </div>
    </footer>
  )
}
