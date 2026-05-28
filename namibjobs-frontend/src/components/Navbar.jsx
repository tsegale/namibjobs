import { Link } from 'react-router-dom'

export default function Navbar() {
  return (
    <nav className="bg-white border-b px-6 py-4 flex items-center gap-6">
      <Link to="/" className="text-xl font-bold text-blue-600">NamibJobs</Link>
      <Link to="/jobs" className="text-gray-600 hover:text-blue-600">Browse Jobs</Link>
      <Link to="/recommend" className="text-gray-600 hover:text-blue-600">Get Recommendations</Link>
    </nav>
  )
}
