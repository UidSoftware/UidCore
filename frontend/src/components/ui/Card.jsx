export default function Card({ title, children, footer, className = '' }) {
  return (
    <div className={`bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden dark:bg-navy-800 dark:border-navy-600 dark:shadow-none ${className}`}>
      {title && (
        <div className="px-6 py-4 border-b border-gray-100 dark:border-navy-700">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-slate-200">{title}</h3>
        </div>
      )}
      <div className="px-6 py-4">{children}</div>
      {footer && (
        <div className="px-6 py-3 bg-gray-50 border-t border-gray-100 dark:bg-navy-900/50 dark:border-navy-700">{footer}</div>
      )}
    </div>
  )
}
