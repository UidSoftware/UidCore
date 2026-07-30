import { Navigate, Route, Routes } from 'react-router-dom'
import useAuthStore from '../stores/authStore.js'
import AppLayout from '../components/layout/AppLayout.jsx'
import Login from '../pages/Login.jsx'
import Dashboard from '../pages/Dashboard.jsx'
import Clientes from '../pages/Clientes.jsx'
import Fornecedores from '../pages/Fornecedores.jsx'
import Financeiro from '../pages/Financeiro.jsx'
import Conciliacao from '../pages/Conciliacao.jsx'
import Vendas from '../pages/Vendas.jsx'
import Pagamentos from '../pages/Pagamentos.jsx'
import Administrativo from '../pages/Administrativo.jsx'
import Rh from '../pages/Rh.jsx'
import Agendamento from '../pages/Agendamento.jsx'
import Portal from '../pages/Portal.jsx'

function ProtectedRoute({ children }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return children
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
        <Route path="/vendas" element={<Vendas />} />
        <Route path="/pagamentos" element={<Pagamentos />} />
        <Route path="/financeiro" element={<Financeiro />} />
        <Route path="/conciliacao" element={<Conciliacao />} />
        <Route path="/administrativo" element={<Administrativo />} />
        <Route path="/rh" element={<Rh />} />
        <Route path="/agendamento" element={<Agendamento />} />
        <Route path="/portal" element={<Portal />} />
      </Route>

      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}
