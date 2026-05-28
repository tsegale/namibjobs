import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import Footer from './Footer'

const NAV_LINKS = [
  { to: '/jobs',      label: 'Jobs',            end: false },
  { to: '/recommend', label: 'Recommendations', end: true  },
  { to: '/companies', label: 'Companies',       end: true  },
  { to: '/profile',   label: 'My Profile',      end: true  },
]

const USER_INITIALS = 'JP'

function BriefcaseIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
      <path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2" />
      <line x1="12" y1="12" x2="12" y2="12" />
      <path d="M2 12h20" />
    </svg>
  )
}

function MenuIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="3" y1="6"  x2="21" y2="6" />
      <line x1="3" y1="12" x2="21" y2="12" />
      <line x1="3" y1="18" x2="21" y2="18" />
    </svg>
  )
}

function CloseIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6"  x2="6"  y2="18" />
      <line x1="6"  y1="6"  x2="18" y2="18" />
    </svg>
  )
}

function navLinkClass({ isActive }) {
  const base = 'text-sm font-medium px-1 py-0.5 transition-colors duration-150 relative'
  return isActive
    ? `${base} text-primary-dark after:absolute after:bottom-[-2px] after:left-0 after:right-0 after:h-[2px] after:bg-primary after:rounded-full`
    : `${base} text-gray-500 hover:text-primary-dark`
}

function mobileNavLinkClass({ isActive }) {
  return isActive
    ? 'block px-4 py-3 text-sm font-semibold text-primary-dark bg-primary-pale rounded-lg'
    : 'block px-4 py-3 text-sm font-medium text-gray-600 hover:bg-gray-50 rounded-lg transition-colors'
}

export default function Layout() {
  const [menuOpen, setMenuOpen] = useState(false)
  const navigate = useNavigate()

  return (
    <div className="min-h-screen flex flex-col" style={{ background: 'var(--color-surface)' }}>

      {/* ── Navbar ───────────────────────────────────────────────────────── */}
      <header className="bg-white border-b border-gray-100 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="flex items-center justify-between h-16">

            {/* Logo */}
            <NavLink
              to="/"
              className="flex items-center gap-2 text-primary hover:opacity-80 transition-opacity"
              style={{ color: 'var(--color-primary)' }}
            >
              <span className="flex items-center justify-center w-8 h-8 rounded-lg text-white"
                style={{ background: 'var(--color-primary)' }}>
                <BriefcaseIcon />
              </span>
              <span className="text-lg font-bold tracking-tight"
                style={{ color: 'var(--color-gray-900)' }}>
                Namib<span style={{ color: 'var(--color-primary)' }}>Jobs</span>
              </span>
            </NavLink>

            {/* Desktop nav links */}
            <nav className="hidden md:flex items-center gap-8">
              {NAV_LINKS.map(({ to, label, end }) => (
                <NavLink key={to} to={to} end={end} className={navLinkClass}>
                  {label}
                </NavLink>
              ))}
            </nav>

            {/* Right side */}
            <div className="flex items-center gap-3">
              {/* Avatar */}
              <button
                onClick={() => navigate('/profile')}
                className="w-9 h-9 rounded-full flex items-center justify-center text-sm font-semibold text-white shadow-sm hover:opacity-90 transition-opacity cursor-pointer"
                style={{ background: 'var(--color-primary-dark)' }}
                title="My Profile"
              >
                {USER_INITIALS}
              </button>

              {/* Hamburger — mobile only */}
              <button
                className="md:hidden flex items-center justify-center w-9 h-9 rounded-lg text-gray-500 hover:bg-gray-100 transition-colors"
                onClick={() => setMenuOpen(o => !o)}
                aria-label="Toggle menu"
              >
                {menuOpen ? <CloseIcon /> : <MenuIcon />}
              </button>
            </div>

          </div>
        </div>

        {/* ── Mobile menu ──────────────────────────────────────────────── */}
        {menuOpen && (
          <div className="md:hidden border-t border-gray-100 bg-white px-4 pb-4 pt-2">
            <nav className="flex flex-col gap-1">
              {NAV_LINKS.map(({ to, label, end }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={end}
                  className={mobileNavLinkClass}
                  onClick={() => setMenuOpen(false)}
                >
                  {label}
                </NavLink>
              ))}
            </nav>

            {/* Mobile user info */}
            <div className="mt-3 pt-3 border-t border-gray-100 flex items-center gap-3 px-1">
              <div
                className="w-9 h-9 rounded-full flex items-center justify-center text-sm font-semibold text-white shrink-0"
                style={{ background: 'var(--color-primary-dark)' }}
              >
                {USER_INITIALS}
              </div>
              <div>
                <p className="text-sm font-medium text-gray-800">James Parata</p>
                <p className="text-xs text-gray-400">jamesparata453@gmail.com</p>
              </div>
            </div>
          </div>
        )}
      </header>

      {/* ── Page content ─────────────────────────────────────────────────── */}
      <main className="flex-1">
        <Outlet />
      </main>

      <Footer />

    </div>
  )
}
