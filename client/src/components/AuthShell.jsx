export default function AuthShell({ children }) {
  return (
    <div className="auth">
      <section className="auth-art">
        <h1>Clinic Platform</h1>
        <p>Book visits, write prescriptions and track hospital load across four Jaipur hospitals.</p>
      </section>
      <section className="auth-pane">{children}</section>
    </div>
  );
}