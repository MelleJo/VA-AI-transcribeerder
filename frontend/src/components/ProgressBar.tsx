interface ProgressBarProps {
    progress: number
    status: string
  }
  
  export default function ProgressBar({ progress, status }: ProgressBarProps) {
    return (
      <div className="w-full">
        <div className="flex justify-between mb-1">
          <span className="text-sm font-medium text-gray-700">{status}</span>
          <span className="text-sm font-medium text-gray-700">{progress}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2.5">
          <div 
            className="bg-blue-600 h-2.5 rounded-full transition-all duration-300 ease-in-out"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>
    )
  }