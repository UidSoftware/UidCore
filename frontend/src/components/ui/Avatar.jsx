import { useState, useEffect } from 'react'

const TAMANHOS = {
  sm: 'w-8 h-8 text-xs',
  md: 'w-10 h-10 text-sm',
  lg: 'w-24 h-24 text-2xl',
}

/**
 * Avatar genérico — foto ou iniciais num círculo. Zero biblioteca externa,
 * zero acoplamento a accounts.User (recebe só foto/nome/size via props,
 * reaproveitável por Cliente/Colaborador quando ganharem foto no futuro —
 * ver RN-10 da Especificacao_Hotfix.md da Manutenção #72).
 */
export default function Avatar({ foto, nome, size = 'md', className = '', onClick }) {
  const [erroCarregamento, setErroCarregamento] = useState(false)
  const tamanho = TAMANHOS[size] || TAMANHOS.md
  const inicial = (nome || '?').trim()[0]?.toUpperCase() || '?'

  // Se a URL da foto trocar, dá uma nova chance de carregar antes de
  // desistir e cair pras iniciais de novo.
  useEffect(() => {
    setErroCarregamento(false)
  }, [foto])

  if (foto && !erroCarregamento) {
    return (
      <img
        src={foto}
        alt={nome || 'Avatar'}
        onClick={onClick}
        onError={() => setErroCarregamento(true)}
        className={`${tamanho} rounded-full object-cover bg-primary-100 dark:bg-violet-900/40 ${className}`}
      />
    )
  }

  return (
    <div
      onClick={onClick}
      className={`${tamanho} rounded-full bg-primary-100 dark:bg-violet-900/40 flex items-center justify-center shrink-0 ${className}`}
    >
      <span className="font-semibold text-primary-700 dark:text-violet-300">{inicial}</span>
    </div>
  )
}
