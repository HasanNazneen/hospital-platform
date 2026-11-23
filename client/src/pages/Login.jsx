import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useAuth } from "../AuthContext";
import { errorMessage } from "../api";
import AuthShell from "../components/AuthShell";
const schema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
});

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [error, setError] = useState("");
  const { register, handleSubmit, formState: { errors, isSubmitting } } =
    useForm({ resolver: zodResolver(schema) });

  const onSubmit = async (v) => {
    setError("");
    try {
      const u = await login(v.email, v.password);
      nav(u.role === "admin" ? "/dashboard" : "/appointments");
    } catch (e) { setError(errorMessage(e)); }
  };

  return (
    <AuthShell>
    <form className="auth-form" onSubmit={handleSubmit(onSubmit)}>
      <h2>Log in</h2>
      {error && <p className="err">{error}</p>}
      <label>Email<input type="email" {...register("email")} /></label>
      {errors.email && <p className="err">{errors.email.message}</p>}
      <label>Password<input type="password" {...register("password")} /></label>
      {errors.password && <p className="err">{errors.password.message}</p>}
      <button disabled={isSubmitting}>{isSubmitting ? "Signing in..." : "Log in"}</button>
      <p className="alt">No account? <Link to="/register">Register</Link></p>
    </form>
    </AuthShell>
  );
}