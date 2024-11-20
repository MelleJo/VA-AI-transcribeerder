import { useRef, useState } from 'react'
import { Upload, File, X } from 'lucide-react'

interface FileUploaderProps {
  onFileSelect: (file: File) => void
  accept?: string
  maxSize?: number // in MB
  isProcessing: boolean
}

export default function FileUploader({ 
  onFileSelect, 
  accept = "audio/*,video/*", 
  maxSize = 200,
  isProcessing 
}: FileUploaderProps) {
  const [dragActive, setDragActive] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true)
    } else if (e.type === "dragleave") {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFiles(e.dataTransfer.files[0])
    }
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault()
    if (e.target.files && e.target.files[0]) {
      handleFiles(e.target.files[0])
    }
  }

  const handleFiles = (file: File) => {
    if (file.size > maxSize * 1024 * 1024) {
      alert(`File size must be less than ${maxSize}MB`)
      return
    }
    setSelectedFile(file)
    onFileSelect(file)
  }

  const handleRemoveFile = () => {
    setSelectedFile(null)
    if (inputRef.current) {
      inputRef.current.value = ''
    }
  }

  return (
    <div className="w-full">
      <div 
        className={`relative border-2 border-dashed rounded-lg p-6 ${
          dragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300'
        } ${isProcessing ? 'opacity-50 cursor-not-allowed' : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          ref={inputRef}
          type="file"
          className="hidden"
          accept={accept}
          onChange={handleChange}
          disabled={isProcessing}
        />

        <div className="text-center">
          <Upload className="mx-auto h-12 w-12 text-gray-400" />
          <div className="mt-4">
            <button
              type="button"
              className="inline-flex text-sm font-semibold text-blue-600 hover:text-blue-500"
              onClick={() => inputRef.current?.click()}
              disabled={isProcessing}
            >
              Upload a file
            </button>
            <p className="pl-1 text-sm text-gray-500 inline">
              or drag and drop
            </p>
          </div>
          <p className="text-xs text-gray-500 mt-2">
            {`Audio or video files up to ${maxSize}MB`}
          </p>
        </div>

        {selectedFile && (
          <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-90">
            <div className="flex items-center space-x-4 p-4 bg-white rounded-lg shadow-sm">
              <File className="h-8 w-8 text-blue-500" />
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">{selectedFile.name}</p>
                <p className="text-sm text-gray-500">
                  {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
              {!isProcessing && (
                <button
                  type="button"
                  className="p-1 rounded-full hover:bg-gray-100"
                  onClick={handleRemoveFile}
                >
                  <X className="h-5 w-5 text-gray-500" />
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}