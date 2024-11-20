import { useState, useRef, useEffect } from 'react'
import { Mic, StopCircle, Loader2 } from 'lucide-react'

interface AudioRecorderProps {
  onRecordingComplete: (blob: Blob) => void
  isProcessing: boolean
}

export default function AudioRecorder({ onRecordingComplete, isProcessing }: AudioRecorderProps) {
  const [isRecording, setIsRecording] = useState(false)
  const [audioTime, setAudioTime] = useState(0)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const timerRef = useRef<NodeJS.Timeout>()

  useEffect(() => {
    // Cleanup timer on unmount
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current)
      }
    }
  }, [])

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      mediaRecorderRef.current = new MediaRecorder(stream)
      chunksRef.current = []

      mediaRecorderRef.current.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data)
        }
      }

      mediaRecorderRef.current.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/wav' })
        onRecordingComplete(blob)
      }

      mediaRecorderRef.current.start()
      setIsRecording(true)
      setAudioTime(0)
      
      // Start timer
      timerRef.current = setInterval(() => {
        setAudioTime(prev => prev + 1)
      }, 1000)

    } catch (error) {
      console.error('Error accessing microphone:', error)
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop())
      setIsRecording(false)
      
      // Clear timer
      if (timerRef.current) {
        clearInterval(timerRef.current)
      }
    }
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className="flex flex-col items-center space-y-4">
      <div className="relative">
        <button
          onClick={isRecording ? stopRecording : startRecording}
          disabled={isProcessing}
          className={`p-4 rounded-full transition-colors ${
            isRecording 
              ? 'bg-red-100 hover:bg-red-200' 
              : 'bg-blue-100 hover:bg-blue-200'
          } disabled:opacity-50 disabled:cursor-not-allowed`}
        >
          {isProcessing ? (
            <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
          ) : isRecording ? (
            <StopCircle className="w-8 h-8 text-red-600" />
          ) : (
            <Mic className="w-8 h-8 text-blue-600" />
          )}
        </button>
        
        {isRecording && (
          <div className="absolute -bottom-6 left-1/2 transform -translate-x-1/2 text-sm font-medium text-gray-500">
            {formatTime(audioTime)}
          </div>
        )}
      </div>
      
      {isRecording && (
        <div className="w-full max-w-md h-2 bg-gray-200 rounded-full overflow-hidden">
          <div 
            className="h-full bg-red-500 animate-pulse"
            style={{ width: '100%' }}
          />
        </div>
      )}
      
      {isProcessing && (
        <p className="text-sm text-gray-500">Processing recording...</p>
      )}
    </div>
  )
}