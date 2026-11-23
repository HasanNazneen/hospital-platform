import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api, { errorMessage } from "../api";

function Stat({ label, value }) {
  return <div className="stat"><div className="num">{value ?? "-"}</div><div>{label}</div></div>;
}

export default function Dashboard() {
  const [hospital, setHospital] = useState("");
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["dashboard", hospital],
    queryFn: async () => (await api.get("/analytics/dashboard/", { params: { hospital: hospital || undefined } })).data,
  });
  const hospitals = useQuery({
    queryKey: ["hospitals"], queryFn: async () => (await api.get("/hospitals/")).data.results,
  });

  return (
    <>
      <h2>Admin dashboard</h2>
      <label>Hospital{" "}
        <select value={hospital} onChange={(e) => setHospital(e.target.value)}>
          <option value="">All hospitals</option>
          {(hospitals.data || []).map((h) => <option key={h.id} value={h.id}>{h.name}</option>)}
        </select>
      </label>
      {isLoading && <p>Loading...</p>}
      {isError && <p className="err">{errorMessage(error)}</p>}
      {data && (
        <>
          <div className="stats">
            <Stat label="Average length of stay (days)" value={data.avg_length_of_stay_days} />
            <Stat label="Bed occupancy" value={`${data.bed_occupancy_pct}%`} />
            <Stat label="30-day readmission rate" value={`${data.readmission_rate_30d_pct}%`} />
          </div>
          <p>Beds in use: {data.occupied_beds} of {data.total_beds} | Discharged admissions: {data.discharged_admissions}</p>
          <p>
            Data quality: {data.data_quality.missing_discharge_flagged} admissions flagged for missing discharge date,{" "}
            {data.data_quality.unmapped_diagnoses} diagnoses without a code.
          </p>
          {data.by_hospital && (
            <table>
              <thead><tr><th>Hospital</th><th>Avg stay</th><th>Occupancy</th><th>Readmission</th></tr></thead>
              <tbody>
                {data.by_hospital.map((h) => (
                  <tr key={h.id}>
                    <td>{h.name}</td><td>{h.avg_length_of_stay_days ?? "-"}</td>
                    <td>{h.bed_occupancy_pct}%</td><td>{h.readmission_rate_30d_pct}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </>
  );
}