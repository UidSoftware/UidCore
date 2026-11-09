import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { NavLink, useLocation } from 'react-router-dom'
import useAuthStore, {
  selectTemAcessoTotal,
  selectPodeAcessarMarketing,
  selectPodeAcessarFinanceiro,
} from '../../stores/authStore.js'
import Avatar from '../ui/Avatar.jsx'
import FotoPerfilModal from './FotoPerfilModal.jsx'

/**
 * Menu separado por setor. Cada item diz o seu `grupo`; item sem `grupo`
 * fica solto no topo (Dashboard). `tecnico` fica reservado para os itens
 * de nicho de um sistema derivado (no LifeStyle, o estúdio).
 * Grupo sem nenhum item visível para o usuário não aparece.
 */
const GRUPOS = [
  { id: 'operacional', label: 'Operacional', icon: '👥' },
  { id: 'tecnico', label: 'Técnico', icon: '💪' },
  { id: 'financas', label: 'Finanças', icon: '💰' },
  { id: 'comercial', label: 'Comercial', icon: '🛒' },
  { id: 'relatorios', label: 'Relatórios', icon: '📈' },
  { id: 'configuracao', label: 'Configuração', icon: '⚙️' },
]

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: '📊' },
  { to: '/clientes', label: 'Clientes', icon: '👥', grupo: 'operacional' },
  { to: '/agendamento', label: 'Agendamento', icon: '📅', grupo: 'operacional' },
  { to: '/administrativo', label: 'Administrativo', icon: '📁', grupo: 'operacional' },
  { to: '/portal', label: 'Portal do Cliente', icon: '🌐', grupo: 'operacional' },
  { to: '/financeiro', label: 'Financeiro', icon: '💰', requer: 'financeiro', grupo: 'financas' },
  { to: '/conciliacao', label: 'Conciliação', icon: '🔄', requer: 'financeiro', grupo: 'financas' },
  { to: '/assinaturas', label: 'Assinaturas', icon: '🔁', requer: 'financeiro', grupo: 'financas' },
  { to: '/pagamentos', label: 'Pagamentos', icon: '💳', grupo: 'financas' },
  { to: '/compras', label: 'Compras', icon: '🧾', requer: 'financeiro', grupo: 'financas' },
  { to: '/fornecedores', label: 'Fornecedores', icon: '🏭', grupo: 'financas' },
  { to: '/vendas', label: 'Vendas', icon: '🛒', grupo: 'comercial' },
  { to: '/produtos', label: 'Produtos', icon: '📦', grupo: 'comercial' },
  { to: '/marketing', label: 'Marketing', icon: '📣', requer: 'marketing', grupo: 'comercial' },
  { to: '/usuarios', label: 'Usuários', icon: '👤', requer: 'staff', grupo: 'configuracao' },
  { to: '/rh', label: 'RH', icon: '👔', requer: 'staff', grupo: 'configuracao' },
]

const classeItem = ({ isActive }) => `
  flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium
  transition-colors duration-150
  ${isActive
    ? 'bg-primary-600 dark:bg-violet-600 text-white'
    : 'text-gray-400 hover:bg-gray-700 hover:text-white dark:hover:bg-navy-700'
  }
`

const classeSubItem = ({ isActive }) => `
  flex items-center gap-2 px-2 py-1.5 rounded-md text-sm transition-colors duration-150
  ${isActive
    ? 'text-white bg-primary-600/80 dark:bg-violet-600/80 font-medium'
    : 'text-gray-400 hover:text-white hover:bg-gray-700 dark:hover:bg-navy-700'
  }
`

export default function Sidebar({ collapsed, onToggle }) {
  const location = useLocation()
  const user = useAuthStore((s) => s.user)
  const temAcessoTotal = useAuthStore(selectTemAcessoTotal)
  const podeMarketing = useAuthStore(selectPodeAcessarMarketing)
  const podeFinanceiro = useAuthStore(selectPodeAcessarFinanceiro)

  const [gruposAbertos, setGruposAbertos] = useState({})
  const [modalFoto, setModalFoto] = useState(false)

  const visibleItems = navItems.filter((item) => {
    if (item.requer === 'staff') return temAcessoTotal
    if (item.requer === 'marketing') return podeMarketing
    if (item.requer === 'financeiro') return podeFinanceiro
    return true
  })

  const idsGrupos = new Set(GRUPOS.map((g) => g.id))
  const soltos = visibleItems.filter((item) => !item.grupo || !idsGrupos.has(item.grupo))
  const grupos = GRUPOS
    .map((g) => ({ ...g, itens: visibleItems.filter((item) => item.grupo === g.id) }))
    .filter((g) => g.itens.length > 0)

  const rotaAtiva = (to) => location.pathname === to || location.pathname.startsWith(`${to}/`)

  // Abre sozinho o grupo da tela atual (ex.: entrou direto por um link).
  const grupoAtivo = grupos.find((g) => g.itens.some((item) => rotaAtiva(item.to)))?.id
  useEffect(() => {
    if (grupoAtivo) setGruposAbertos((prev) => (prev[grupoAtivo] ? prev : { ...prev, [grupoAtivo]: true }))
  }, [grupoAtivo])

  const alternarGrupo = (id) => {
    if (collapsed) {
      onToggle()
      setGruposAbertos((prev) => ({ ...prev, [id]: true }))
      return
    }
    setGruposAbertos((prev) => ({ ...prev, [id]: !prev[id] }))
  }

  // No mobile (drawer) a navegação fecha o menu; no desktop não mexe.
  const aoNavegar = () => {
    if (window.innerWidth < 768) onToggle()
  }

  const nome = user?.nome_completo || user?.email || ''

  return (
    <aside
      className={`
        flex flex-col h-full bg-gray-900 dark:bg-navy-900 text-white transition-all duration-300 ease-in-out
        ${collapsed ? 'w-16' : 'w-64'}
      `}
    >
      {/* Perfil: foto, nome e e-mail */}
      {user && (
        <div className={`flex flex-col items-center gap-2 border-b border-gray-700 dark:border-navy-600 shrink-0 ${collapsed ? 'px-2 py-4' : 'px-4 py-5'}`}>
          <button
            type="button"
            onClick={() => setModalFoto(true)}
            className="relative group rounded-full focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-400"
            title="Trocar foto"
            aria-label="Trocar foto de perfil"
          >
            <Avatar foto={user.foto_url} nome={nome} size={collapsed ? 'md' : 'lg'} />
            <span className="absolute inset-0 rounded-full bg-black/50 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity text-lg">
              📷
            </span>
          </button>
          {!collapsed && (
            <div className="w-full text-center">
              <p className="text-sm font-semibold text-white leading-tight truncate">{nome}</p>
              {user.nome_completo && user.email && (
                <p className="text-xs text-gray-400 dark:text-slate-400 truncate mt-0.5">{user.email}</p>
              )}
            </div>
          )}
        </div>
      )}

      <nav className="flex-1 overflow-y-auto py-4 space-y-1 px-2">
        {soltos.map(({ to, label, icon }) => (
          <NavLink key={to} to={to} onClick={aoNavegar} className={classeItem} title={collapsed ? label : undefined}>
            <span className="text-lg leading-none shrink-0">{icon}</span>
            {!collapsed && <span className="truncate">{label}</span>}
          </NavLink>
        ))}

        {grupos.map((g) => {
          const aberto = !!gruposAbertos[g.id]
          const ativo = g.id === grupoAtivo
          return (
            <div key={g.id}>
              <button
                type="button"
                onClick={() => alternarGrupo(g.id)}
                aria-expanded={aberto}
                title={collapsed ? g.label : undefined}
                className={`
                  w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors duration-150
                  ${ativo ? 'text-white' : 'text-gray-400 hover:bg-gray-700 hover:text-white dark:hover:bg-navy-700'}
                `}
              >
                <span className="text-lg leading-none shrink-0">{g.icon}</span>
                {!collapsed && (
                  <>
                    <span className="flex-1 text-left truncate">{g.label}</span>
                    <svg
                      className={`w-4 h-4 shrink-0 transition-transform duration-200 ${aberto ? 'rotate-180' : ''}`}
                      fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </>
                )}
              </button>

              {!collapsed && aberto && (
                <div className="mt-1 ml-5 pl-3 border-l border-gray-700 dark:border-navy-600 space-y-0.5">
                  {g.itens.map(({ to, label, icon }) => (
                    <NavLink key={to} to={to} onClick={aoNavegar} className={classeSubItem}>
                      <span className="text-base leading-none shrink-0">{icon}</span>
                      <span className="truncate">{label}</span>
                    </NavLink>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </nav>

      {/* Recolher / expandir (no mobile, fecha o menu) */}
      <div className="p-2 border-t border-gray-700 dark:border-navy-600 shrink-0">
        <button
          type="button"
          onClick={onToggle}
          className="w-full flex items-center justify-center p-2 rounded-lg text-gray-400 hover:text-white hover:bg-gray-700 dark:hover:bg-navy-700 transition-colors"
          aria-label={collapsed ? 'Expandir menu' : 'Recolher menu'}
          title={collapsed ? 'Expandir menu' : 'Recolher menu'}
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

      {/* Portal: no mobile a Sidebar fica num drawer com transform, que
          prenderia o modal (position: fixed) dentro dos 256px do menu. */}
      {modalFoto && createPortal(<FotoPerfilModal onClose={() => setModalFoto(false)} />, document.body)}
    </aside>
  )
}
