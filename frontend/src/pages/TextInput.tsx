import { useState, useEffect } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { FileText, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { getPrompts, summarizeText } from '../lib/api'

interface Prompt {
  id: string
  label: string
  description: string
}

export default function TextInput() {
  const [inputText, setInputText] = useState('')
  const [promptType, setPromptType] = useState<string>('')
  const navigate = useNavigate()

  // Fetch available prompts
  const { data: promptsData } = useQuery({
    queryKey: ['prompts'],
    queryFn: async () => {
      const response = await getPrompts()
      return response
    }
  })

  // Set initial prompt type when prompts are loaded
  useEffect(() => {
    if (promptsData?.prompts?.length > 0 && !promptType) {
      setPromptType(promptsData.prompts[0].id)
    }
  }, [promptsData])

  const summarizeMutation = useMutation({
    mutationFn: async ({ text, type }: { text: string; type: string }) => {
      const response = await summarizeText({
        text,
        prompt_type: type,
      })
      return response
    },
    onSuccess: (data) => {
      toast.success('Summary generated successfully!')
      navigate(`/summary/${data.summary_id}`)
    },
    onError: (error) => {
      console.error('Summarization error:', error)
      toast.error('Failed to generate summary. Please try again.')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputText.trim()) {
      toast.error('Please enter some text to summarize')
      return
    }
    summarizeMutation.mutate({ text: inputText, type: promptType })
  }

  return (
    <div className="max-w-7xl mx-auto">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Text Input</h1>
        <p className="mt-2 text-gray-600">
          Enter or paste your text below to generate a summary
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-4">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Summary Type
              </label>
              <select
                value={promptType}
                onChange={(e) => setPromptType(e.target.value)}
                className="w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              >
                {promptsData?.prompts?.map((prompt: Prompt) => (
                  <option key={prompt.id} value={prompt.id}>
                    {prompt.label}
                  </option>
                ))}
              </select>
              {promptsData?.prompts?.find((p: Prompt) => p.id === promptType)?.description && (
                <p className="mt-2 text-sm text-gray-500">
                  {promptsData.prompts.find((p: Prompt) => p.id === promptType)?.description}
                </p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Input Text
              </label>
              <textarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                rows={12}
                className="w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                placeholder="Paste your text here..."
              />
            </div>

            <button
              type="submit"
              disabled={summarizeMutation.isPending || !inputText.trim()}
              className="w-full flex items-center justify-center py-3 px-4 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {summarizeMutation.isPending ? (
                <>
                  <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                  Generating Summary...
                </>
              ) : (
                <>
                  <FileText className="w-5 h-5 mr-2" />
                  Generate Summary
                </>
              )}
            </button>
          </form>
        </div>

        <div className="bg-white rounded-xl shadow-sm p-6">
          <h2 className="text-xl font-semibold mb-4">Instructions</h2>
          <div className="prose max-w-none">
            <p>To get the best results:</p>
            <ul className="list-disc pl-5 space-y-2">
              <li>Choose the appropriate summary type for your content</li>
              <li>Paste the complete text you want to summarize</li>
              <li>Make sure all relevant information is included</li>
              <li>Check that names and numbers are correctly formatted</li>
            </ul>
            <div className="mt-4 p-4 bg-blue-50 rounded-lg">
              <p className="text-sm text-blue-700">
                Tip: The summary will be structured based on the selected type, ensuring all important details are captured appropriately.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}