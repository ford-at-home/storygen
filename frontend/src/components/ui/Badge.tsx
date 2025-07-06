import React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
  {
    variants: {
      variant: {
        default: 'bg-richmond-river text-white hover:bg-richmond-river/80',
        secondary: 'bg-gray-100 text-gray-800 hover:bg-gray-200',
        destructive: 'bg-richmond-brick text-white hover:bg-richmond-brick/80',
        outline: 'border border-gray-300 text-gray-700',
        success: 'bg-moss-green text-white hover:bg-moss-green/80',
        warning: 'bg-richmond-sunset text-white hover:bg-richmond-sunset/80',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }