import React from 'react'
import { cn } from '@/lib/utils'

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  helperText?: string
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, label, error, helperText, ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label className="block text-sm font-medium text-gray-700 mb-2">
            {label}
          </label>
        )}
        <input
          type={type}
          className={cn(
            'flex h-10 w-full rounded-md border-2 border-gray-300 bg-white px-3 py-2 text-sm placeholder:text-gray-400',
            'focus:border-richmond-river focus:outline-none focus:ring-3 focus:ring-richmond-river/10',
            'disabled:cursor-not-allowed disabled:opacity-50',
            error && 'border-richmond-brick focus:border-richmond-brick focus:ring-richmond-brick/10',
            className
          )}
          ref={ref}
          {...props}
        />
        {error && (
          <p className="mt-1 text-sm text-richmond-brick">{error}</p>
        )}
        {helperText && !error && (
          <p className="mt-1 text-sm text-gray-500">{helperText}</p>
        )}
      </div>
    )
  }
)
Input.displayName = 'Input'

export { Input }