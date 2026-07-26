/**
 * Extrai uma mensagem legível de um erro de API (Axios/DRF) — em vez de
 * um "erro ao salvar" genérico, mostra o motivo real (validação de campo,
 * detail, non_field_errors etc.) pra saber o que aconteceu de fato.
 */
export function extractErrorMessage(error, fallback = 'Erro ao salvar.') {
  const data = error?.response?.data
  if (!data) return error?.message || fallback

  if (typeof data === 'string') return data

  if (typeof data.detail === 'string') return data.detail

  const partes = []
  for (const [campo, valor] of Object.entries(data)) {
    const texto = Array.isArray(valor) ? valor.join(' ') : String(valor)
    partes.push(campo === 'non_field_errors' ? texto : `${campo}: ${texto}`)
  }
  return partes.length > 0 ? partes.join(' | ') : fallback
}
