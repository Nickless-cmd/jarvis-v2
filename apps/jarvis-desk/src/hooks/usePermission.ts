import { useContext } from 'react'
import { PermissionContext } from '../contexts/PermissionContext'

export function usePermission() {
  const ctx = useContext(PermissionContext)
  if (!ctx) throw new Error('usePermission must be used within PermissionProvider')
  return ctx
}
