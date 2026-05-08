import { ReactNode } from 'react'

type BadgeVariant = 'info' | 'success' | 'warning' | 'danger'

interface BadgeProps {
  children: ReactNode
  variant?: BadgeVariant
}

export const Badge = ({ children, variant = 'info' }: BadgeProps) => (
  <span className={`badge ${variant}`}>
    {children}
  </span>
)
