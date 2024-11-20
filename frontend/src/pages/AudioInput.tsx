import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { CloudLightning } from 'lucide-react'
import toast from 'react-hot-toast'
import AudioRecorder from '../components/AudioRecorder'
import FileUploader from '../components/FileUploader'
import ProgressBar from '../components/ProgressBar'
import { uploadAudio, summarizeText } from '../lib/api'

export default function AudioInput() {
  const [transcription, setTranscription] = useState('')
  const [selectedPromptType, setSelectedPromptType] = useState('telefoongesprek')
  const navigate = useNavigate()

  const audioMutation = useMutation({
    mutationFn: async (file: File) => {
      const result = await uploadAudio(file)
      return result
    },
    onSuccess: (data) => {
      setTranscription(data.transcript)
      toast.success('Audio processed successfully!')
    },
    onError: (error) => {
      console.error('Audio processing error:', error)
      toast.error('Failed to process audio. Please try again.')
    },
  })

  const summaryMutation = useMutation({
    mutationFn: async ({ text, prompt_type }: { text: string; prompt_type: string }) => {
      const result = await summarizeText({
        text,
        prompt_type,
      })
      return result
    },
    onSuccess: (data) => {
      toast.success('Summary generated successfully!')
      navigate(`/summary/${data.summary_id}`)
    },
    onError: (error) => {
      console.error('Summary generation error:', error)
      toast.error('Failed to generate summary. Please try again.')
    },
  })

  const handleAudioUpload = async (file: File) => {
    audioMutation.mutate(file)
  }

  const handleRecordingComplete = async (blob: Blob) => {
    const file = new File([blob], 'recording.wav', { type: 'audio/wav' })
    audioMutation.mutate(file)
  }

  const handleGenerateSummary = () => {
    if (!transcription) {
      toast.error('Please record or upload audio first')
      return
    }
    
    summaryMutation.mutate({
      text: transcription,
      prompt_type: selectedPromptType,
    })
  }

  const isProcessing = audioMutation.isPending || summaryMutation.isPending

  return (
    <div className="max-w-7xl mx-auto">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Audio Input</h1>
        <p className="mt-2 text-gray-600">
          Record audio or upload an audio file for transcription and summarization
        </p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Recording Section */}
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h2 className="text-xl font-semibold mb-6">Record Audio</h2>
          <AudioRecorder
            onRecordingComplete={handleRecordingComplete}
            isProcessing={isProcessing}
          />
        </div>

        {/* Upload Section */}
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h2 className="text-xl font-semibold mb-6">Upload Audio</h2>
          <FileUploader
            onFileSelect={handleAudioUpload}
            accept="audio/*,video/*"
            isProcessing={isProcessing}
          />
        </div>
      </div>

      {isProcessing && (
        <div className="mt-6">
          <ProgressBar
            progress={75}
            status={
              audioMutation.isPending
                ? 'Processing audio...'
                : 'Generating summary...'
            }
          />
        </div>
      )}

      {transcription && (
        <div className="mt-6">
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-xl font-semibold mb-4">Transcription</h2>
            
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Summary Type
              </label>
              <select
                value={selectedPromptType}
                onChange={(e) => setSelectedPromptType(e.target.value)}
                className="w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              >
                <option value="telefoongesprek">Phone Call</option>
                <option value="hypotheek">Mortgage</option>
                <option value="pensioen">Pension</option>
                <option value="aov">Disability Insurance</option>
              </select>
            </div>

            <div className="mb-4">
              <textarea
                value={transcription}
                onChange={(e) => setTranscription(e.target.value)}
                className="w-full h-48 rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                placeholder="Transcription will appear here..."
                readOnly={isProcessing}
              />
            </div>

            <button
              onClick={handleGenerateSummary}
              disabled={isProcessing || !transcription}
              className="w-full flex items-center justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {summaryMutation.isPending ? (
                <CloudLightning className="animate-spin -ml-1 mr-2 h-5 w-5" />
              ) : null}
              Generate Summary
            </button>
          </div>
        </div>
      )}
    </div>
  )
}