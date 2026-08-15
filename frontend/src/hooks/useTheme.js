import { useCallback, useState } from 'react'

const STORAGE_KEY = 'uidcore-theme'

function applyThemeClass(isDark) {
  document.documentElement.classList.toggle('dark', isDark)
}

/**
 * Tema claro/escuro do UidCore — Manutenção #31 (Especificacao_Hotfix.md).
 * Default é o tema escuro (decisão do cliente, sobrepõe a decisão anterior
 * do Brush: escuro nasce ativado no primeiro acesso, sem depender de
 * prefers-color-scheme do SO — só volta pro claro se o usuário escolher).
 * O estado inicial é lido da classe já aplicada em <html> pelo script
 * anti-FOUC em index.html (roda antes do React montar), então o primeiro
 * render já nasce sincronizado com o localStorage — sem flash.
 */
export function useTheme() {
  const [isDark, setIsDark] = useState(() => document.documentElement.classList.contains('dark'))

  const toggleTheme = useCallback(() => {
    setIsDark((prev) => {
      const next = !prev
      applyThemeClass(next)
      localStorage.setItem(STORAGE_KEY, next ? 'dark' : 'light')
      return next
    })
  }, [])

  return { isDark, toggleTheme }
}
