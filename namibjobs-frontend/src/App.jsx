import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Jobs from './pages/Jobs'
import Companies from './pages/Companies'
import Recommend from './pages/Recommend'
import Profile from './pages/Profile'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/"          element={<Jobs />} />
        <Route path="/jobs"      element={<Jobs />} />
        <Route path="/companies" element={<Companies />} />
        <Route path="/recommend" element={<Recommend />} />
        <Route path="/profile"   element={<Profile />} />
      </Route>
    </Routes>
  )
}
