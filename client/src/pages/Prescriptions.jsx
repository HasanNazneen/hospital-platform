import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api, { errorMessage } from "../api";
import { useAuth } from "../AuthContext";

const MAX_MB = 5;
const OK_TYPES = ["image/jpeg", "image/png", "application/pdf"];
const serverOrigin = import.meta.env.VITE_API_URL.replace(/\/api\/?$/, "");

function PrescriptionForm() {
  const qc = useQueryClient();
  const [appointment, setAppointment] = useState("");
  const [items, setItems] = useState([{ drug: "", dose: "", days: "" }]);
  const [notes, setNotes] = useState("");
  const [file, setFile] = useState(null);
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");

  const { data: appts = [] } = useQuery({
    queryKey: ["appointments", "forRx"],
    queryFn: async () => (await api.get("/appointments/", { params: { ordering: "-slot" } })).data.results,
  });

  const m = useMutation({
    mutationFn: (fd) => api.post("/prescriptions/", fd),
    onSuccess: () => {
      setOk("Prescription saved."); setError("");
      setAppointment(""); setItems([{ drug: "", dose: "", days: "" }]); setNotes(""); setFile(null);
      qc.invalidateQueries({ queryKey: ["prescriptions"] });
    },
    onError: (e) => { setError(errorMessage(e)); setOk(""); },
  });

  function submit(e) {
    e.preventDefault();
    setOk("");
    if (!appointment) return setError("Choose an appointment.");
    const clean = items.filter((i) => i.drug.trim() || i.dose.trim());
    if (clean.length === 0 || clean.some((i) => !i.drug.trim() || !i.dose.trim()))
      return setError("Each medicine needs a drug name and a dose.");
    if (file && !OK_TYPES.includes(file.type)) return setError("Only JPG, PNG or PDF files are allowed.");
    if (file && file.size > MAX_MB * 1024 * 1024) return setError(`File must be ${MAX_MB} MB or smaller.`);
    const fd = new FormData();
    fd.append("appointment", appointment);
    fd.append("items", JSON.stringify(clean.map((i) => ({ ...i, days: i.days ? Number(i.days) : undefined }))));
    fd.append("notes", notes);
    if (file) fd.append("attachment", file);
    setError("");
    m.mutate(fd);
  }

  const setItem = (idx, key, val) => setItems(items.map((it, i) => (i === idx ? { ...it, [key]: val } : it)));

  return (
    <form className="card" onSubmit={submit}>
      <h3>Write a prescription</h3>
      {error && <p className="err">{error}</p>}
      {ok && <p className="okmsg">{ok}</p>}
      <label>Appointment
        <select value={appointment} onChange={(e) => setAppointment(e.target.value)}>
          <option value="">Select...</option>
          {appts.filter((a) => a.status !== "cancelled").map((a) => (
            <option key={a.id} value={a.id}>{`${new Date(a.slot).toLocaleString()} - ${a.patient_name}`}</option>
          ))}
        </select>
      </label>
      {items.map((it, i) => (
        <div className="row" key={i}>
          <input placeholder="Drug" value={it.drug} onChange={(e) => setItem(i, "drug", e.target.value)} />
          <input placeholder="Dose (e.g. 500mg)" value={it.dose} onChange={(e) => setItem(i, "dose", e.target.value)} />
          <input placeholder="Days" type="number" min="1" value={it.days} onChange={(e) => setItem(i, "days", e.target.value)} />
          {items.length > 1 && <button type="button" className="link" onClick={() => setItems(items.filter((_, k) => k !== i))}>Remove</button>}
        </div>
      ))}
      <button type="button" className="link" onClick={() => setItems([...items, { drug: "", dose: "", days: "" }])}>+ Add medicine</button>
      <label>Notes<textarea value={notes} onChange={(e) => setNotes(e.target.value)} /></label>
      <label>Attachment (JPG, PNG or PDF, max 5 MB)
        <input type="file" accept=".jpg,.jpeg,.png,.pdf" onChange={(e) => setFile(e.target.files[0] || null)} />
      </label>
      <button disabled={m.isPending}>{m.isPending ? "Saving..." : "Save prescription"}</button>
    </form>
  );
}

export default function Prescriptions() {
  const { user } = useAuth();
  const [search, setSearch] = useState("");
  const list = useQuery({
    queryKey: ["prescriptions", search],
    queryFn: async () => (await api.get("/prescriptions/", { params: { search: search || undefined } })).data.results,
  });

  return (
    <>
      <h2>Prescriptions</h2>
      {user.role !== "patient" && <PrescriptionForm />}
      <div className="card">
        <div className="filters">
          <input placeholder="Search notes or patient" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        {list.isLoading ? <p>Loading...</p> : list.isError ? <p className="err">{errorMessage(list.error)}</p> : (
          list.data.length === 0 ? <p>No prescriptions yet.</p> :
          list.data.map((p) => (
            <div className="rx" key={p.id}>
              <strong>Appointment #{p.appointment}</strong>
              <ul>{p.items.map((i, k) => <li key={k}>{i.drug} - {i.dose}{i.days ? ` for ${i.days} days` : ""}</li>)}</ul>
              {p.notes && <p>Notes: {p.notes}</p>}
              {p.attachment && (
                <a href={p.attachment.startsWith("http") ? p.attachment : serverOrigin + p.attachment}
                   target="_blank" rel="noreferrer">View attachment</a>
              )}
            </div>
          ))
        )}
      </div>
    </>
  );
}