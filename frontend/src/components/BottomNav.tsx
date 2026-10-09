import { useLocation, useNavigate } from 'react-router-dom';
import { Home, Users, FileText, CreditCard, BookOpen, Plus, ShoppingCart, BookMarked, ArrowDownToLine, ArrowUpFromLine, Tag } from 'lucide-react';

const TABS = [
  { path: '/home',           icon: Home,         label: 'Home'      },
  { path: '/parties',        icon: Users,         label: 'Parties'   },
  { path: '/invoices',       icon: FileText,      label: 'Invoices'  },
  { path: '/payments',       icon: CreditCard,    label: 'Receipts'  },
  { path: '/purchases',      icon: ShoppingCart,  label: 'Purchases' },
  { path: '/chart-of-accounts', icon: BookOpen,   label: 'Accounts' },
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
          background: 'var(--accent)',
          color: 'white',
          borderRadius: 14,
          margin: '4px 2px',
          border: 'none',
        }}
        onClick={() => navigate('/invoices/new')}
      >
        <Plus />
        <span>Sales Invoice</span>
      </button>
      <button className={`nav-item ${isActive('/vouchers') ? 'active' : ''}`} onClick={() => navigate('/vouchers')} title="All Vouchers">
        <BookMarked />
        <span>Vouchers</span>
      </button>
      <button className={`nav-item ${isActive('/rate-book') ? 'active' : ''}`} onClick={() => navigate('/rate-book')} title="Party Rate Book">
        <Tag />
        <span>Rates</span>
      </button>
      <button className="nav-item" onClick={() => navigate('/payments/new')} title="New customer receipt">
        <ArrowDownToLine />
        <span>New Receipt</span>
      </button>
      <button className="nav-item" onClick={() => navigate('/purchases')} title="New vendor payment">
        <ArrowUpFromLine />
        <span>New Payment</span>
      </button>
      <button className={`nav-item ${isActive('/vouchers/credit-note') ? 'active' : ''}`} onClick={() => navigate('/vouchers/credit-note')} title="Sales Return">
        <ArrowDownToLine />
        <span>Credit Note</span>
      </button>
    </nav>
  );
}
