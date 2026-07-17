import { useState } from 'react'
import useAuthStore from '../stores/authStore.js'

export function useAuth() {
  const { user, isAuthenticated, login: storeLogin, logout } = useAuthStore()
  const [isLoading, setIsLoading] = useState(false)

  const login = async (email, password) => {
    setIsLoading(true)
    try {
      await storeLogin(email, password)
    } finally {
      setIsLoading(false)
    }
  }

  return { user, isAuthenticated, login, logout, isLoading }
}
