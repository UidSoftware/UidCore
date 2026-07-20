import { Navigate, Route, Routes } from 'react-router-dom'
import useAuthStore from '../stores/authStore.js'
import AppLayout from '../components/layout/AppLayout.jsx'
import Login from '../pages/Login.jsx'
import Dashboard from '../pages/Dashboard.jsx'
import Clientes from '../pages/Clientes.jsx'
import Fornecedores from '../pages/Fornecedores.jsx'
import Financeiro from '../pages/Financeiro.jsx'

function ProtectedRoute({ children }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return children
}

function PlaceholderPage({ title }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] gap-3">
      <span className="text-5xl">🚧</span>
      <h2 className="text-xl font-semibold text-gray-700">{title}</h2>
      <p className="text-sm text-gray-400">Módulo em desenvolvimento.</p>
    </div>
  )
}

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/clientes" element={<Clientes />} />
        <Route path="/fornecedores" element={<Fornecedores />} />
        <Route path="/vendas" element={<PlaceholderPage title="Vendas" />} />
        <Route path="/pagamentos" element={<PlaceholderPage title="Pagamentos" />} />
        <Route path="/financeiro" element={<Financeiro />} />
        <Route path="/administrativo" element={<PlaceholderPage title="Administrativo" />} />
        <Route path="/rh" element={<PlaceholderPage title="RH" />} />
        <Route path="/agendamento" element={<PlaceholderPage title="Agendamento" />} />
        <Route path="/portal" element={<PlaceholderPage title="Portal do Cliente" />} />
      </Route>

      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}
