import { NavLink } from 'react-router-dom'
import useAuthStore from '../../stores/authStore.js'

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: '📊' },
  { to: '/clientes', label: 'Clientes', icon: '👥' },
  { to: '/fornecedores', label: 'Fornecedores', icon: '🏭' },
  { to: '/vendas', label: 'Vendas', icon: '🛒' },
  { to: '/produtos', label: 'Produtos', icon: '📦' },
  { to: '/pagamentos', label: 'Pagamentos', icon: '💳' },
  { to: '/financeiro', label: 'Financeiro', icon: '💰' },
  { to: '/conciliacao', label: 'Conciliação', icon: '🔄' },
  { to: '/administrativo', label: 'Administrativo', icon: '📁' },
  { to: '/rh', label: 'RH', icon: '👔' },
  { to: '/usuarios', label: 'Usuários', icon: '👤', staffOnly: true },
  { to: '/agendamento', label: 'Agendamento', icon: '📅' },
  { to: '/portal', label: 'Portal do Cliente', icon: '🌐' },
]

export default function Sidebar({ collapsed, onToggle }) {
  const isStaff = useAuthStore((s) => s.user?.is_staff)
  const visibleItems = navItems.filter((item) => !item.staffOnly || isStaff)

  return (
    <aside
      className={`
        flex flex-col bg-gray-900 dark:bg-navy-900 text-white transition-all duration-300 ease-in-out
        ${collapsed ? 'w-16' : 'w-64'}
      `}
    >
      <div className="flex items-center justify-between px-4 py-5 border-b border-gray-700 dark:border-navy-600 min-h-[64px]">
        {!collapsed && (
          <span className="text-lg font-bold text-white tracking-tight">UidCore</span>
        )}
        <button
          onClick={onToggle}
          className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-gray-700 dark:hover:bg-navy-700 transition-colors"
          aria-label={collapsed ? 'Expandir menu' : 'Recolher menu'}
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            {collapsed ? (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
            )}
          </svg>
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto py-4 space-y-1 px-2">
        {visibleItems.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) => `
              flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium
              transition-colors duration-150
              ${isActive
                ? 'bg-primary-600 dark:bg-violet-600 text-white'
                : 'text-gray-400 hover:bg-gray-700 hover:text-white dark:hover:bg-navy-700'
              }
            `}
            title={collapsed ? label : undefined}
          >
            <span className="text-lg leading-none shrink-0">{icon}</span>
            {!collapsed && <span className="truncate">{label}</span>}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
