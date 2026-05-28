import { useJobs } from '../hooks/useJobs'
import JobCard from '../components/JobCard'

export default function Jobs() {
  const { jobs, loading, error } = useJobs()

  return (
    <div className="page-container">
      <h1 className="section-title">Browse Jobs</h1>

      {loading && (
        <div className="flex justify-center py-20">
          <div className="w-8 h-8 rounded-full border-2 border-gray-200 animate-spin"
            style={{ borderTopColor: 'var(--color-primary)' }} />
        </div>
      )}

      {error && (
        <div className="rounded-xl p-4 text-sm text-red-600 bg-red-50 border border-red-100">
          Failed to load jobs: {error}
        </div>
      )}

      {!loading && !error && jobs.length === 0 && (
        <p className="text-gray-400 text-center py-20">No jobs found.</p>
      )}

      <div className="grid gap-4 sm:grid-cols-1 lg:grid-cols-2">
        {jobs.map((job, i) => (
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
            isNew={i < 3}
          />
        ))}
      </div>
    </div>
  )
}
