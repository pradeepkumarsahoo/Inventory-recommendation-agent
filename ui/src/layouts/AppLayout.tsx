import { NavLink, Outlet } from 'react-router-dom';
import StoreSelector from '../components/StoreSelector';

const nav = [
  { to: '/dashboard', label: 'Executive' },
  { to: '/products', label: 'Products' },
  { to: '/inventory', label: 'Inventory' },
  { to: '/pricing', label: 'Pricing' },
  { to: '/agents', label: 'Agents' },
  { to: '/game-plan', label: 'Daily Plan' },
  { to: '/architecture', label: 'Architecture' },
];

export default function AppLayout() {
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">R·I</div>
          <div>
            <div className="brand-title">Retail Intelligence</div>
            <div className="brand-sub">Autonomous Store Decisions</div>
          </div>
        </div>
        <nav>
          {nav.map((n) => (
            <NavLink key={n.to} to={n.to} className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-foot">
          <div>Author: Pradeep Sahoo</div>
          <div>Learning Implementation</div>
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <StoreSelector />
        </header>
        <section className="page">
          <Outlet />
        </section>
      </main>
    </div>
  );
}
