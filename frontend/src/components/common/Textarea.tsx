import { TextareaHTMLAttributes } from 'react'

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string
  error?: string
}

export const Textarea = ({ label, error, ...props }: TextareaProps) => (
  <div className="mb-4">
    {label && (
      <label className="block text-sm font-medium mb-1 text-gray-700">{label}</label>
    )}
    <textarea
      {...props}
      className={`custom-textarea w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${
        error ? 'border-red-500' : 'border-gray-300'
      }`}
    />
    {error && <p className="text-red-500 text-sm mt-1">{error}</p>}
  </div>
)
