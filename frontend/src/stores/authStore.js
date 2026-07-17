import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1'

const useAuthStore = create(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,

      login: async (email, password) => {
        const { data: tokens } = await axios.post(`${API_BASE}/auth/token/`, { email, password })
        const { access, refresh } = tokens

        const { data: user } = await axios.get(`${API_BASE}/accounts/me/`, {
          headers: { Authorization: `Bearer ${access}` },
        })

        set({ accessToken: access, refreshToken: refresh, user, isAuthenticated: true })
      },

      logout: () => {
        set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false })
      },

      refreshAccessToken: async () => {
        const { refreshToken } = get()
        if (!refreshToken) throw new Error('Sem refresh token')

        const { data } = await axios.post(`${API_BASE}/auth/token/refresh/`, { refresh: refreshToken })
        set({ accessToken: data.access })
        return data.access
      },

      setUser: (user) => set({ user }),
    }),
    {
      name: 'uidcore-auth',
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    },
  ),
)

export default useAuthStore
