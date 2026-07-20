export default function Select({ label, error, options = [], id, className = '', ...props }) {
  const selectId = id || label?.toLowerCase().replace(/\s+/g, '-')
  return (
    <div className="flex flex-col gap-1">
      {label && (
        <label htmlFor={selectId} className="text-sm font-medium text-gray-700">
          {label}
        </label>
      )}
      <select
        id={selectId}
        className={`w-full rounded-lg border px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-colors duration-150 ${
          error ? 'border-red-500 bg-red-50' : 'border-gray-300 bg-white'
        } ${className}`}
        {...props}
      >
        {options.map(({ value, label: optLabel }) => (
          <option key={value} value={value}>
            {optLabel}
          </option>
        ))}
      </select>
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  )
}
