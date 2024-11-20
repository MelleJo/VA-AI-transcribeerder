import { useState } from 'react'
import { Download, Copy, CheckCircle2 } from 'lucide-react'

interface SummaryProps {
  content: string
  onCopy?: () => void
  onDownload?: () => void
  showActions?: boolean
}

export default function Summary({ content, onCopy, onDownload, showActions = true }: SummaryProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
    onCopy?.()
  }

  return (
    <div className="bg-white rounded-xl shadow-sm">
      <div className="p-6">
        {showActions && (
          <div className="flex justify-end space-x-2 mb-4">
            <button
              onClick={handleCopy}
              className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              {copied ? (
                <CheckCircle2 className="h-4 w-4 mr-2 text-green-500" />
              ) : (
                <Copy className="h-4 w-4 mr-2" />
              )}
              {copied ? 'Copied!' : 'Copy'}
            </button>
            {onDownload && (
              <button
                onClick={onDownload}
                className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                <Download className="h-4 w-4 mr-2" />
                Download
              </button>
            )}
          </div>
        )}
        <div className="prose max-w-none">
          <div 
            className="whitespace-pre-wrap"
            dangerouslySetInnerHTML={{ 
              __html: content.replace(/\n/g, '<br>') 
            }} 
          />
        </div>
      </div>
    </div>
  )
}
