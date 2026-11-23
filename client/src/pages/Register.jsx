import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import api, { errorMessage } from "../api";
import { useAuth } from "../AuthContext";
import AuthShell from "../components/AuthShell";
const schema = z.object({
  first_name: z.string().min(1, "First name is required"),
  last_name: z.string().optional(),
  email: z.string().email("Enter a valid email"),
  password: z.string().min(8, "At least 8 characters"),
});

export default function Register() {
  const nav = useNavigate();
  const { login } = useAuth();
  const [error, setError] = useState("");
  const { register, handleSubmit, formState: { errors, isSubmitting } } =
    useForm({ resolver: zodResolver(schema) });

  const onSubmit = async (v) => {
    setError("");
    try {
      await api.post("/auth/register/", v);
      await login(v.email, v.password);
      nav("/appointments");
    } catch (e) { setError(errorMessage(e)); }
  };

  return (
    <AuthShell>
    <form className="auth-form" onSubmit={handleSubmit(onSubmit)}>
      <h2>Create account</h2>
      {error && <p className="err">{error}</p>}
      <label>First name<input {...register("first_name")} /></label>
      {errors.first_name && <p className="err">{errors.first_name.message}</p>}
      <label>Last name<input {...register("last_name")} /></label>
      <label>Email<input type="email" {...register("email")} /></label>
      {errors.email && <p className="err">{errors.email.message}</p>}
      <label>Password<input type="password" {...register("password")} /></label>
      {errors.password && <p className="err">{errors.password.message}</p>}
      <button disabled={isSubmitting}>Create account</button>
      <p className="alt">Already registered? <Link to="/login">Log in</Link></p>
    </form>
    </AuthShell>
  );
}