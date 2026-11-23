import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext";

export default function Layout() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const name = `${user.first_name || ""} ${user.last_name || ""}`.trim() || user.email;
  const initials = name.split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase();

  return (
    <div className="shell">
      <aside className="side">
        <div className="brand">Clinic Platform<small>Jaipur health network</small></div>
        <nav>
          <NavLink to="/appointments">Appointments</NavLink>
          <NavLink to="/prescriptions">Prescriptions</NavLink>
          {user.role === "admin" && <NavLink to="/dashboard">Dashboard</NavLink>}
        </nav>
        <div className="me">
          <div className="avatar">{initials}</div>
          <div className="me-text"><b>{name}</b><span>{user.role}</span></div>
          <button className="link" onClick={async () => { await logout(); nav("/login"); }}>Log out</button>
        </div>
      </aside>
      <main className="main"><div className="content"><Outlet /></div></main>
    </div>
  );
}