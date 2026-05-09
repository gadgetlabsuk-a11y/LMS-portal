interface StreamingTextOutputProps {
  text: string
  isStreaming: boolean
  placeholder?: string
}

export function StreamingTextOutput({ text, isStreaming, placeholder }: StreamingTextOutputProps) {
  return (
    <div className="font-mono text-sm whitespace-pre-wrap min-h-[80px] p-2 bg-gray-50 rounded border">
      {text || (!isStreaming && (
        <span className="text-gray-400">{placeholder ?? 'Output will appear here...'}</span>
      ))}
      {isStreaming && (
        <span
          className="inline-block w-2 h-4 bg-gray-700 ml-0.5 animate-pulse"
          data-testid="streaming-cursor"
        />
      )}
    </div>
  )
}
