import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api, { errorMessage } from "../api";
import { useAuth } from "../AuthContext";

const profileSchema = z.object({
  hospital: z.coerce.number().min(1, "Choose a hospital"),
  name: z.string().min(2, "Enter your full name"),
  dob: z.string().min(1, "Date of birth is required"),
  phone: z.string().regex(/^[6-9]\d{9}$/, "Enter a valid 10-digit mobile number"),
});

const bookSchema = z.object({
  doctor: z.coerce.number().min(1, "Choose a doctor"),
  slot: z.string().min(1, "Choose a date and time")
    .refine((v) => new Date(v) > new Date(), "Slot must be in the future"),
});

function ProfileForm({ onDone }) {
  const [error, setError] = useState("");
  const { data: hospitals = [] } = useQuery({
    queryKey: ["hospitals"], queryFn: async () => (await api.get("/hospitals/")).data.results,
  });
  const { register, handleSubmit, formState: { errors } } = useForm({ resolver: zodResolver(profileSchema) });
  const m = useMutation({
    mutationFn: (v) => api.post("/patients/", v),
    onSuccess: onDone,
    onError: (e) => setError(errorMessage(e)),
  });
  return (
    <form className="card" onSubmit={handleSubmit((v) => m.mutate(v))}>
      <h3>Complete your patient profile</h3>
      {error && <p className="err">{error}</p>}
      <label>Hospital
        <select {...register("hospital")}>
          <option value="">Select...</option>
          {hospitals.map((h) => <option key={h.id} value={h.id}>{h.name}</option>)}
        </select>
      </label>
      {errors.hospital && <p className="err">{errors.hospital.message}</p>}
      <label>Full name<input {...register("name")} /></label>
      {errors.name && <p className="err">{errors.name.message}</p>}
      <label>Date of birth<input type="date" {...register("dob")} /></label>
      {errors.dob && <p className="err">{errors.dob.message}</p>}
      <label>Mobile<input {...register("phone")} /></label>
      {errors.phone && <p className="err">{errors.phone.message}</p>}
      <button disabled={m.isPending}>Save profile</button>
    </form>
  );
}

function BookForm() {
  const qc = useQueryClient();
  const [error, setError] = useState("");
  const { data: doctors = [] } = useQuery({
    queryKey: ["doctors"], queryFn: async () => (await api.get("/doctors/")).data.results,
  });
  const { register, handleSubmit, reset, formState: { errors } } = useForm({ resolver: zodResolver(bookSchema) });
  const m = useMutation({
    mutationFn: (v) => api.post("/appointments/", { doctor: v.doctor, slot: new Date(v.slot).toISOString() }),
    onSuccess: () => { setError(""); reset(); qc.invalidateQueries({ queryKey: ["appointments"] }); },
    onError: (e) => setError(errorMessage(e)),
  });
  return (
    <form className="card" onSubmit={handleSubmit((v) => m.mutate(v))}>
      <h3>Book an appointment</h3>
      {error && <p className="err">{error}</p>}
      <label>Doctor
        <select {...register("doctor")}>
          <option value="">Select...</option>
          {doctors.map((d) => (
            <option key={d.id} value={d.id}>{`${d.first_name} ${d.last_name}`.trim() || d.email}</option>
          ))}
        </select>
      </label>
      {errors.doctor && <p className="err">{errors.doctor.message}</p>}
      <label>Date and time<input type="datetime-local" {...register("slot")} /></label>
      {errors.slot && <p className="err">{errors.slot.message}</p>}
      <button disabled={m.isPending}>Book</button>
    </form>
  );
}

export default function Appointments() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [actionError, setActionError] = useState("");

  const profile = useQuery({
    queryKey: ["myprofile"], enabled: user.role === "patient",
    queryFn: async () => (await api.get("/patients/")).data.results,
  });
  const list = useQuery({
    queryKey: ["appointments", status, search, page],
    queryFn: async () =>
      (await api.get("/appointments/", { params: { status: status || undefined, search: search || undefined, page } })).data,
  });
  const setStat = useMutation({
    mutationFn: ({ id, s }) => api.patch(`/appointments/${id}/`, { status: s }),
    onSuccess: () => { setActionError(""); qc.invalidateQueries({ queryKey: ["appointments"] }); },
    onError: (e) => setActionError(errorMessage(e)),
  });

  const needsProfile = user.role === "patient" && profile.data && profile.data.length === 0;
  const rows = list.data?.results || [];

  return (
    <>
      <h2>Appointments</h2>
      {needsProfile && <ProfileForm onDone={() => qc.invalidateQueries({ queryKey: ["myprofile"] })} />}
      {user.role === "patient" && profile.data?.length > 0 && <BookForm />}

      <div className="card">
        <div className="filters">
          <input placeholder="Search patient or doctor" value={search}
                 onChange={(e) => { setSearch(e.target.value); setPage(1); }} />
          <select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}>
            <option value="">All statuses</option>
            <option value="booked">Booked</option>
            <option value="done">Done</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>
        {actionError && <p className="err">{actionError}</p>}
        {list.isLoading ? <p>Loading...</p> : list.isError ? <p className="err">{errorMessage(list.error)}</p> : (
          <table>
            <thead><tr><th>When</th><th>Patient</th><th>Doctor</th><th>Status</th><th></th></tr></thead>
            <tbody>
              {rows.length === 0 && <tr><td colSpan="5">No appointments yet. Patients can book one from this page. </td></tr>}
              {rows.map((a) => (
                <tr key={a.id}>
                  <td>{new Date(a.slot).toLocaleString()}</td>
                  <td>{a.patient_name}</td>
                  <td>{a.doctor_name}</td>
                  <td><span className={`badge ${a.status}`}>{a.status}</span></td>
                  <td>
                    {a.status === "booked" && user.role !== "doctor" &&
                      <button className="link" onClick={() => setStat.mutate({ id: a.id, s: "cancelled" })}>Cancel</button>}
                    {a.status === "booked" && user.role === "doctor" && <>
                      <button className="link" onClick={() => setStat.mutate({ id: a.id, s: "done" })}>Mark done</button>{" "}
                      <button className="link" onClick={() => setStat.mutate({ id: a.id, s: "cancelled" })}>Cancel</button>
                    </>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div className="pager">
          <button disabled={!list.data?.previous} onClick={() => setPage((p) => p - 1)}>Prev</button>
          <span>Page {page}</span>
          <button disabled={!list.data?.next} onClick={() => setPage((p) => p + 1)}>Next</button>
        </div>
      </div>
    </>
  );
}