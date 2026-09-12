import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import './index.css';

import Calculator from './pages/Calculator';
import { ProtectedLayout } from './components/ProtectedLayout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import { PartiesList, PartyDetail } from './pages/Parties';
import { InvoicesList, NewInvoice } from './pages/Sales';
import { PaymentsList, NewPayment, PaymentDetail } from './pages/Payments';
import Analytics from './pages/Analytics';
import AddressBook from './pages/AddressBook';
import Users from './pages/Users';
import PendingDues from './pages/PendingDues';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 0,
      refetchOnWindowFocus: true,
      refetchOnMount: true,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* Stealth entry — always shows calculator first */}
          <Route path="/" element={<div className="app-shell"><Calculator /></div>} />

          {/* Login — only reachable after calculator unlock */}
          <Route path="/login" element={<Login />} />

          {/* Protected accounting app */}
          <Route element={<ProtectedLayout />}>
            <Route path="/home" element={<Dashboard />} />

            <Route path="/parties" element={<PartiesList />} />
            <Route path="/parties/:id" element={<PartyDetail />} />

            <Route path="/invoices" element={<InvoicesList />} />
            <Route path="/invoices/new" element={<NewInvoice />} />

            <Route path="/payments" element={<PaymentsList />} />
            <Route path="/payments/new" element={<NewPayment />} />
            <Route path="/payments/:id" element={<PaymentDetail />} />

            <Route path="/analytics" element={<Analytics />} />
            <Route path="/address-book" element={<AddressBook />} />
            <Route path="/users" element={<Users />} />
            <Route path="/pending-dues" element={<PendingDues />} />
          </Route>

          {/* Catch-all → calculator */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
