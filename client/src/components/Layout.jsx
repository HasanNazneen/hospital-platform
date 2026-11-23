import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext";

export default function Layout() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  return (
    <>
      <header className="bar">
        <strong>Clinic Platform</strong>
        <nav>
          <NavLink to="/appointments">Appointments</NavLink>
          <NavLink to="/prescriptions">Prescriptions</NavLink>
          {user.role === "admin" && <NavLink to="/dashboard">Dashboard</NavLink>}
        </nav>
        <span>
          {user.email} ({user.role}){" "}
          <button className="link" onClick={async () => { await logout(); nav("/login"); }}>Log out</button>
        </span>
      </header>
      <main className="wrap"><Outlet /></main>
    </>
  );
}