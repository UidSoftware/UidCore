import { useAuth } from '../../hooks/useAuth.js'
import { useTheme } from '../../hooks/useTheme.js'

export default function Header({ onMenuOpen }) {
  const { user, logout } = useAuth()
  const { isDark, toggleTheme } = useTheme()

  return (
    <header className="h-16 bg-white dark:bg-navy-900 border-b border-gray-200 dark:border-navy-600 flex items-center justify-between px-6 shrink-0">
      <div className="flex items-center gap-4">
        <button
          onClick={onMenuOpen}
          className="md:hidden p-2 rounded-lg text-gray-500 hover:bg-gray-100 dark:text-slate-400 dark:hover:bg-navy-700 transition-colors"
          aria-label="Abrir menu"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
        <span className="hidden md:block text-sm font-semibold text-primary-600 dark:text-violet-400 tracking-wide">UidCore</span>
      </div>

      <div className="flex items-center gap-4">
        <button
          onClick={toggleTheme}
          aria-label={isDark ? 'Ativar modo claro' : 'Ativar modo escuro'}
          title={isDark ? 'Ativar modo claro' : 'Ativar modo escuro'}
          className="w-9 h-9 flex items-center justify-center rounded-lg text-lg
                     text-gray-500 hover:bg-gray-100
                     dark:text-slate-400 dark:hover:bg-navy-700
                     transition-colors"
        >
          {isDark ? '☀️' : '🌙'}
        </button>
        {user && (
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-primary-100 dark:bg-violet-900/40 flex items-center justify-center">
              <span className="text-xs font-semibold text-primary-700 dark:text-violet-300">
                {(user.nome_completo || user.email || '?')[0].toUpperCase()}
              </span>
            </div>
            <span className="hidden sm:block text-sm font-medium text-gray-700 dark:text-slate-300">
              {user.nome_completo || user.email}
            </span>
          </div>
        )}
        <button
          onClick={logout}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm text-gray-500 hover:bg-gray-100 hover:text-gray-700 dark:text-slate-400 dark:hover:bg-navy-700 dark:hover:text-slate-200 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
          </svg>
          <span className="hidden sm:block">Sair</span>
        </button>
      </div>
    </header>
  )
}
