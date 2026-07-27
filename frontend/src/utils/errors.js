/**
 * Extrai uma mensagem legível de um erro de API (Axios/DRF) — em vez de
 * um "erro ao salvar" genérico, mostra o motivo real (validação de campo,
 * detail, non_field_errors etc.) pra saber o que aconteceu de fato.
 */
/**
 * Remove campos com string vazia de um payload antes de enviar pra API.
 * Necessario porque, com os campos virando opcionais no backend, um
 * input de data/numero/escolha deixado em branco manda "" — e "" nao e
 * um valor valido pra DateField/DecimalField/ChoiceField (o Django
 * aceita o campo AUSENTE ou null, nao uma string vazia mal formatada).
 * Texto livre (CharField/TextField) aceita "" numa boa, entao remover
 * a chave inteira nesses casos tambem e seguro (o model usa o default).
 */
export function stripEmptyStrings(payload) {
  const limpo = {}
  for (const [chave, valor] of Object.entries(payload)) {
    if (valor === '') continue
    limpo[chave] = valor
  }
  return limpo
}

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
