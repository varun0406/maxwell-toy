import { useLocation, useNavigate } from 'react-router-dom';
import { Home, Users, FileText, CreditCard, BookOpen, Plus } from 'lucide-react';

const TABS = [
  { path: '/home',           icon: Home,       label: 'Home'      },
  { path: '/parties',        icon: Users,       label: 'Parties'   },
  { path: '/invoices',       icon: FileText,    label: 'Invoices'  },
  { path: '/payments',       icon: CreditCard,  label: 'Receipts'  },
  { path: '/address-book',   icon: BookOpen,    label: 'Addresses' },
];

export default function BottomNav() {
  const location = useLocation();
  const navigate = useNavigate();

  const isActive = (path: string) => {
    if (path === '/home') return location.pathname === '/home';
    return location.pathname.startsWith(path);
  };

  return (
    <nav className="bottom-nav">
      {TABS.map(({ path, icon: Icon, label }) => (
        <button
          key={path}
          className={`nav-item ${isActive(path) ? 'active' : ''}`}
          onClick={() => navigate(path)}
        >
          <Icon />
          <span>{label}</span>
        </button>
      ))}
      {/* Quick create invoice FAB-style button in nav */}
      <button
        className="nav-item"
        style={{
          background: 'var(--primary)',
          color: 'white',
          borderRadius: 14,
          margin: '4px 2px',
          border: 'none',
        }}
        onClick={() => navigate('/invoices/new')}
      >
        <Plus />
        <span>New Bill</span>
      </button>
    </nav>
  );
}
