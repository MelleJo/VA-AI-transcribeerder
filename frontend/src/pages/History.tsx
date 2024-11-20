import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { FileText, Mic, Clock, ChevronRight, Search, Filter } from 'lucide-react'
import { getSummaries } from '../lib/api'
import { formatDate } from '../lib/utils'

const ITEMS_PER_PAGE = 10

interface Summary {
  id: string
  input_text: string
  file_type?: string
  original_filename?: string
  prompt_type: string
  created_at: string
  summary: string
}

export default function History() {
  const navigate = useNavigate()
  const [currentPage, setCurrentPage] = useState(1)
  const [searchTerm, setSearchTerm] = useState('')
  const [filterType, setFilterType] = useState('all')

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['summaries', currentPage, filterType],
    queryFn: () => getSummaries(ITEMS_PER_PAGE, (currentPage - 1) * ITEMS_PER_PAGE),
  })

  const filteredSummaries = data?.summaries?.filter((summary: Summary) => {
    const matchesSearch = searchTerm
      ? summary.input_text.toLowerCase().includes(searchTerm.toLowerCase()) ||
        summary.summary.toLowerCase().includes(searchTerm.toLowerCase())
      : true

    const matchesType = filterType === 'all' ? true : summary.prompt_type === filterType

    return matchesSearch && matchesType
  })

  const totalPages = Math.ceil((data?.total || 0) / ITEMS_PER_PAGE)

  return (
    <div className="max-w-7xl mx-auto">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Summary History</h1>
        <p className="mt-2 text-gray-600">
          View and manage your previous summaries
        </p>
      </header>

      <div className="mb-6 flex flex-col sm:flex-row gap-4">
        <div className="flex-1">
          <div className="relative">
            <input
              type="text"
              placeholder="Search summaries..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <Search className="absolute left-3 top-2.5 h-5 w-5 text-gray-400" />
          </div>
        </div>
        <div className="sm:w-48">
          <div className="relative">
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="w-full pl-10 pr-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent appearance-none"
            >
              <option value="all">All Types</option>
              <option value="telefoongesprek">Phone Call</option>
              <option value="hypotheek">Mortgage</option>
              <option value="pensioen">Pension</option>
              <option value="aov">Disability Insurance</option>
            </select>
            <Filter className="absolute left-3 top-2.5 h-5 w-5 text-gray-400" />
          </div>
        </div>
      </div>

      <div className="bg-white shadow-sm rounded-lg divide-y divide-gray-200">
        {isLoading ? (
          <div className="flex items-center justify-center h-32">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
          </div>
        ) : filteredSummaries?.length ? (
          <>
            {filteredSummaries.map((summary: Summary) => (
              <div
                key={summary.id}
                onClick={() => navigate(`/summary/${summary.id}`)}
                className="p-6 hover:bg-gray-50 cursor-pointer transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    {summary.file_type?.includes('audio') ? (
                      <Mic className="h-5 w-5 text-gray-400" />
                    ) : (
                      <FileText className="h-5 w-5 text-gray-400" />
                    )}
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        {summary.original_filename || 'Text Input'}
                      </p>
                      <p className="text-sm text-gray-500">
                        {summary.prompt_type.replace('_', ' ').toUpperCase()}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center">
                    <Clock className="h-4 w-4 text-gray-400 mr-1" />
                    <span className="text-sm text-gray-500">
                      {formatDate(summary.created_at)}
                    </span>
                    <ChevronRight className="h-5 w-5 text-gray-400 ml-4" />
                  </div>
                </div>
                <div className="mt-2">
                  <p className="text-sm text-gray-600 line-clamp-2">
                    {summary.summary}
                  </p>
                </div>
              </div>
            ))}

            {totalPages > 1 && (
              <div className="px-6 py-4 flex items-center justify-between border-t border-gray-200">
                <button
                  onClick={() => setCurrentPage(page => Math.max(1, page - 1))}
                  disabled={currentPage === 1 || isFetching}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
                >
                  Previous
                </button>
                <span className="text-sm text-gray-700">
                  Page {currentPage} of {totalPages}
                </span>
                <button
                  onClick={() => setCurrentPage(page => Math.min(totalPages, page + 1))}
                  disabled={currentPage === totalPages || isFetching}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            )}
          </>
        ) : (
          <div className="flex flex-col items-center justify-center h-32 text-gray-500">
            <FileText className="h-8 w-8 mb-2" />
            <p>No summaries found</p>
          </div>
        )}
      </div>
    </div>
  )
}
