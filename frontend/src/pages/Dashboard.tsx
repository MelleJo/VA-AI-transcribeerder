import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Mic, FileText, Clock, ArrowRight } from 'lucide-react'
import { getSummaries } from '../lib/api'
import { formatDate } from '../lib/utils'

interface ActionCardProps {
  icon: typeof Mic | typeof FileText
  title: string
  description: string
  path: string
  color: string
}

interface Summary {
  id: string
  file_type?: string
  original_filename?: string
  prompt_type: string
  created_at: string
  summary: string
}

function ActionCard({ icon: Icon, title, description, path, color }: ActionCardProps) {
  const navigate = useNavigate()
  
  return (
    <div
      onClick={() => navigate(path)}
      className="bg-white rounded-xl shadow-sm hover:shadow-md transition-all cursor-pointer p-6"
    >
      <div className="flex items-center justify-between mb-4">
        <Icon className={`w-8 h-8 ${color}`} />
        <ArrowRight className="w-6 h-6 text-gray-400" />
      </div>
      <h2 className="text-xl font-semibold mb-2">{title}</h2>
      <p className="text-gray-600">{description}</p>
    </div>
  )
}

export default function Dashboard() {
  const navigate = useNavigate()
  const { data: recentSummaries, isLoading } = useQuery({
    queryKey: ['recent-summaries'],
    queryFn: () => getSummaries(5),
  })

  return (
    <div className="max-w-7xl mx-auto">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Welcome to Summary App</h1>
        <p className="mt-2 text-gray-600">Choose how you'd like to create a new summary</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <ActionCard
          icon={Mic}
          title="Audio Input"
          description="Record or upload audio files for transcription and summarization"
          path="/audio"
          color="text-blue-500"
        />
        <ActionCard
          icon={FileText}
          title="Text Input"
          description="Enter or paste text directly for quick summarization"
          path="/text"
          color="text-green-500"
        />
      </div>

      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">Recent Summaries</h2>
          <button 
            onClick={() => navigate('/history')}
            className="text-blue-600 hover:text-blue-700 text-sm font-medium"
          >
            View all
          </button>
        </div>
        
        <div className="bg-white rounded-xl shadow-sm divide-y">
          {isLoading ? (
            <div className="flex items-center justify-center h-32">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
            </div>
          ) : recentSummaries?.summaries?.length ? (
            recentSummaries.summaries.map((summary: Summary) => (
              <div 
                key={summary.id}
                onClick={() => navigate(`/summary/${summary.id}`)}
                className="p-4 hover:bg-gray-50 cursor-pointer transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="flex-shrink-0">
                      {summary.file_type?.includes('audio') ? (
                        <Mic className="h-5 w-5 text-gray-400" />
                      ) : (
                        <FileText className="h-5 w-5 text-gray-400" />
                      )}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        {summary.original_filename || 'Text Input'}
                      </p>
                      <p className="text-sm text-gray-500">
                        {summary.prompt_type.replace('_', ' ').toUpperCase()}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center text-sm text-gray-500">
                    <Clock className="h-4 w-4 mr-1" />
                    {formatDate(summary.created_at)}
                  </div>
                </div>
                <div className="mt-2">
                  <p className="text-sm text-gray-600 line-clamp-2">
                    {summary.summary}
                  </p>
                </div>
              </div>
            ))
          ) : (
            <div className="flex flex-col items-center justify-center h-32 text-gray-500">
              <Clock className="h-8 w-8 mb-2" />
              <p>No recent summaries</p>
            </div>
          )}
        </div>
      </section>
    </div>
  )
}
