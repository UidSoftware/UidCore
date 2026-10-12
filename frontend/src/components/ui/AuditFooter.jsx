const fmt = (d) => (d ? new Date(d).toLocaleDateString('pt-BR') : '')

/**
 * Rodapé discreto de auditoria — "Criado por X em dd/mm/aaaa · Alterado por
 * Y em dd/mm/aaaa" — exibido só nos modais de EDIÇÃO (nunca em criação, pois
 * o registro ainda não tem created_at). Consome created_by_nome/
 * updated_by_nome/created_at/updated_at já expostos pela API
 * (AuditFieldsMixin, backend/common/serializers.py) — somente leitura,
 * nenhum campo novo é editável (RF-20).
 */
export default function AuditFooter({ item }) {
  if (!item?.created_at) return null

  return (
    <p className="mt-4 text-xs text-gray-400 dark:text-slate-500 border-t border-gray-100 dark:border-navy-700 pt-3">
      Criado por {item.created_by_nome || '—'} em {fmt(item.created_at)}
      {item.updated_at && item.updated_at !== item.created_at && (
        <> · Alterado por {item.updated_by_nome || '—'} em {fmt(item.updated_at)}</>
      )}
    </p>
  )
}
