import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import ListEditor from "../components/ListEditor.jsx";
import SymptomChecklist from "../components/SymptomChecklist.jsx";
import ClinicalNoteExtractor from "../components/ClinicalNoteExtractor.jsx";
import {
  FormSection,
  SelectInput,
  TextArea,
  TextInput,
  compact,
  toNum,
} from "../components/fields.jsx";
import { api } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";

function nowLocal() {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
}

const EMPTY_VITALS = {
  temperature_c: "",
  systolic_bp: "",
  diastolic_bp: "",
  heart_rate: "",
  respiratory_rate: "",
  spo2: "",
  blood_glucose_mg_dl: "",
  pain_score: "",
};

const EMPTY_SOCIAL = {
  smoking_status: "unknown",
  pack_years: "",
  alcohol_use: "",
  recreational_drug_use: "",
  diet: "",
  exercise: "",
  living_situation: "",
  occupational_exposure: "",
  travel_history: "",
  sexual_history: "",
  sleep: "",
  bowel_movements: "",
  bladder_frequency: "",
  addictions: "",
  menstrual_history: "",
  lmp_date: "",
};

const EMPTY_EXAM = {
  pallor: "",
  edema: "",
  cyanosis: "",
  clubbing: "",
  lymphadenopathy: "",
  dehydration: "",
  extra_notes: "",
};

export default function NewVisitPage() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [demo, setDemo] = useState({
    full_name: "", mrn: "", date_of_birth: "", sex: "unknown",
    gender_identity: "", weight_kg: "", height_cm: "", occupation: "",
    phone: "", email: "", address: "",
  });
  const [visitInfo, setVisitInfo] = useState({
    occurred_at: nowLocal(), visit_type: "new",
    referring_doctor_name: "", chief_complaint: "",
    complaint_duration: "", severity_score: "", progression: "",
  });
  const [hpi, setHpi] = useState({
    hpi_onset: "", hpi_location: "", hpi_character: "",
    hpi_aggravating_factors: "", hpi_relieving_factors: "",
    hpi_radiation: "", hpi_timing: "",
  });
  const [symptoms, setSymptoms] = useState([]);
  const [vitals, setVitals] = useState(EMPTY_VITALS);
  const [history, setHistory] = useState([]);
  const [medications, setMedications] = useState([]);
  const [allergies, setAllergies] = useState([]);
  const [social, setSocial] = useState(EMPTY_SOCIAL);
  const [exam, setExam] = useState(EMPTY_EXAM);
  const [workingNotes, setWorkingNotes] = useState("");

  const [busyLabel, setBusyLabel] = useState("");
  const [error, setError] = useState("");
  const [fillFeedback, setFillFeedback] = useState("");

  const bmi = useMemo(() => {
    const w = toNum(demo.weight_kg);
    const h = toNum(demo.height_cm);
    if (!w || !h) return null;
    return (w / Math.pow(h / 100, 2)).toFixed(1);
  }, [demo.weight_kg, demo.height_cm]);

  function handleExtractAndFill(extracted) {
    if (!extracted) return;

    // 1. Demographics
    setDemo((prev) => ({
      ...prev,
      full_name: extracted.demographics?.full_name || prev.full_name || (extracted.demographics?.age_years ? `Patient (${extracted.demographics.sex || "Unknown"}, ${extracted.demographics.age_years}yo)` : prev.full_name),
      sex: extracted.demographics?.sex || prev.sex,
      date_of_birth: extracted.demographics?.date_of_birth || prev.date_of_birth,
      weight_kg: extracted.demographics?.weight_kg !== undefined && extracted.demographics?.weight_kg !== null ? String(extracted.demographics.weight_kg) : prev.weight_kg,
      height_cm: extracted.demographics?.height_cm !== undefined && extracted.demographics?.height_cm !== null ? String(extracted.demographics.height_cm) : prev.height_cm,
      occupation: extracted.demographics?.occupation || prev.occupation,
    }));

    // 2. Visit Info
    setVisitInfo((prev) => ({
      ...prev,
      chief_complaint: extracted.visit_info?.chief_complaint || prev.chief_complaint,
      complaint_duration: extracted.visit_info?.complaint_duration || prev.complaint_duration,
      severity_score: extracted.visit_info?.severity_score !== undefined && extracted.visit_info?.severity_score !== null ? String(extracted.visit_info.severity_score) : prev.severity_score,
      progression: extracted.visit_info?.progression || prev.progression,
    }));

    // 3. HPI
    setHpi((prev) => ({
      ...prev,
      hpi_onset: extracted.hpi?.hpi_onset || prev.hpi_onset,
      hpi_location: extracted.hpi?.hpi_location || prev.hpi_location,
      hpi_character: extracted.hpi?.hpi_character || prev.hpi_character,
      hpi_aggravating_factors: extracted.hpi?.hpi_aggravating_factors || prev.hpi_aggravating_factors,
      hpi_relieving_factors: extracted.hpi?.hpi_relieving_factors || prev.hpi_relieving_factors,
      hpi_radiation: extracted.hpi?.hpi_radiation || prev.hpi_radiation,
      hpi_timing: extracted.hpi?.hpi_timing || prev.hpi_timing,
    }));

    // 4. Vitals
    setVitals((prev) => {
      const v = extracted.vitals || {};
      return {
        ...prev,
        temperature_c: v.temperature_c !== undefined && v.temperature_c !== null ? String(v.temperature_c) : prev.temperature_c,
        systolic_bp: v.systolic_bp !== undefined && v.systolic_bp !== null ? String(v.systolic_bp) : prev.systolic_bp,
        diastolic_bp: v.diastolic_bp !== undefined && v.diastolic_bp !== null ? String(v.diastolic_bp) : prev.diastolic_bp,
        heart_rate: v.heart_rate !== undefined && v.heart_rate !== null ? String(v.heart_rate) : prev.heart_rate,
        respiratory_rate: v.respiratory_rate !== undefined && v.respiratory_rate !== null ? String(v.respiratory_rate) : prev.respiratory_rate,
        spo2: v.spo2 !== undefined && v.spo2 !== null ? String(v.spo2) : prev.spo2,
        blood_glucose_mg_dl: v.blood_glucose_mg_dl !== undefined && v.blood_glucose_mg_dl !== null ? String(v.blood_glucose_mg_dl) : prev.blood_glucose_mg_dl,
        pain_score: v.pain_score !== undefined && v.pain_score !== null ? String(v.pain_score) : prev.pain_score,
      };
    });

    // 5. Symptoms
    const newSymptoms = [];
    const seen = new Set();
    
    (extracted.symptoms_present || []).forEach((s) => {
      const id = s.canonical_id || s.name.toLowerCase().replace(/\s+/g, "_");
      if (!seen.has(id)) {
        seen.add(id);
        newSymptoms.push({ name: id, status: "present", severity: "", duration: "" });
      }
    });

    (extracted.symptoms_absent || []).forEach((s) => {
      const id = s.canonical_id || s.name.toLowerCase().replace(/\s+/g, "_");
      if (!seen.has(id)) {
        seen.add(id);
        newSymptoms.push({ name: id, status: "absent", severity: "", duration: "" });
      }
    });

    if (newSymptoms.length > 0) {
      setSymptoms(newSymptoms);
    }

    // 6. Medical History
    if (extracted.medical_history && extracted.medical_history.length > 0) {
      setHistory(extracted.medical_history.map((h) => ({
        category: h.category || "general",
        name: h.name,
        details: h.details || "",
        onset_year: h.onset_year ? String(h.onset_year) : "",
        resolved: Boolean(h.resolved),
      })));
    }

    // 7. Medications
    if (extracted.medications && extracted.medications.length > 0) {
      setMedications(extracted.medications.map((m) => ({
        name: m.name,
        dose: m.dose || "",
        frequency: m.frequency || "",
        is_active: m.is_active !== false,
        notes: m.notes || "",
      })));
    }

    // 8. Allergies
    if (extracted.allergies && extracted.allergies.length > 0) {
      setAllergies(extracted.allergies.map((a) => ({
        allergen: a.allergen,
        type: a.type || "medication",
        reaction: a.reaction || "",
        severity: a.severity || "",
        notes: a.notes || "",
      })));
    }

    // 9. Social History
    if (extracted.social_history) {
      setSocial((prev) => ({
        ...prev,
        smoking_status: extracted.social_history.smoking_status || prev.smoking_status,
        pack_years: extracted.social_history.pack_years !== undefined && extracted.social_history.pack_years !== null ? String(extracted.social_history.pack_years) : prev.pack_years,
        alcohol_use: extracted.social_history.alcohol_use || prev.alcohol_use,
        recreational_drug_use: extracted.social_history.recreational_drug_use || prev.recreational_drug_use,
        diet: extracted.social_history.diet || prev.diet,
        exercise: extracted.social_history.exercise || prev.exercise,
        living_situation: extracted.social_history.living_situation || prev.living_situation,
        occupational_exposure: extracted.social_history.occupational_exposure || prev.occupational_exposure,
        travel_history: extracted.social_history.travel_history || prev.travel_history,
        sleep: extracted.social_history.sleep || prev.sleep,
      }));
    }

    // 10. Physical Exam
    if (extracted.physical_exam) {
      const sanitizeSign = (v) => {
        if (!v) return "";
        const s = String(v).toLowerCase().trim();
        if (["absent", "no", "none", "negative", "nil", "normal"].includes(s)) return "absent";
        if (["present", "yes", "positive", "abnormal", "mild", "moderate", "severe", "1+", "2+", "3+", "4+"].includes(s)) return "present";
        return "";
      };

      setExam((prev) => ({
        ...prev,
        pallor: sanitizeSign(extracted.physical_exam.pallor) || prev.pallor,
        edema: sanitizeSign(extracted.physical_exam.edema) || prev.edema,
        cyanosis: sanitizeSign(extracted.physical_exam.cyanosis) || prev.cyanosis,
        clubbing: sanitizeSign(extracted.physical_exam.clubbing) || prev.clubbing,
        lymphadenopathy: sanitizeSign(extracted.physical_exam.lymphadenopathy) || prev.lymphadenopathy,
        dehydration: sanitizeSign(extracted.physical_exam.dehydration) || prev.dehydration,
        extra_notes: extracted.physical_exam.extra_notes || prev.extra_notes,
      }));
    }

    // Feedback Banner
    setFillFeedback("✨ Form successfully autofilled from clinical note! You can review and adjust any field below before submitting.");
    setTimeout(() => setFillFeedback(""), 8000);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    if (!demo.full_name.trim()) {
      setError("Patient full name is required.");
      return;
    }
    try {
      setBusyLabel("Saving patient...");
      const patient = await api.post("/patients", {
        ...compact(demo),
        date_of_birth: demo.date_of_birth || undefined,
      });
      const pid = patient.id;

      for (const allergy of allergies) {
        await api.post(`/patients/${pid}/allergies`, compact(allergy));
      }
      for (const entry of history) {
        await api.post(`/patients/${pid}/history`, compact(entry));
      }
      for (const med of medications) {
        await api.post(`/patients/${pid}/medications`, compact(med));
      }

      setBusyLabel("Saving visit...");
      const visit = await api.post("/visits", {
        patient_id: pid,
        attending_doctor_id: user.id,
        occurred_at: visitInfo.occurred_at || undefined,
        ...compact({ ...visitInfo, severity_score: toNum(visitInfo.severity_score) }),
        ...compact(hpi),
      });
      const vid = visit.id;

      setBusyLabel("Saving symptoms & vitals...");
      const presentRows = symptoms.map((s) => ({
        name: s.name,
        status: s.status,
        severity: s.status === "present" ? toNum(s.severity) : null,
        duration: s.duration || null,
      }));
      if (presentRows.length > 0) {
        await api.put(`/visits/${vid}/symptoms`, presentRows);
      }

      const vitalsPayload = compact(
        Object.fromEntries(Object.entries(vitals).map(([k, v]) => [k, toNum(v)]))
      );
      if (Object.keys(vitalsPayload).length > 0) {
        await api.put(`/visits/${vid}/vitals`, vitalsPayload);
      }
      const socialPayload = compact(social);
      const hasSocial =
        Object.keys(socialPayload).length > 1 || social.smoking_status !== "unknown";
      if (hasSocial) {
        await api.put(`/visits/${vid}/social-history`, {
          ...socialPayload,
          lmp_date: social.lmp_date || undefined,
        });
      }

      const examPayload = compact(
        Object.fromEntries(
          Object.entries(exam).map(([k, v]) => [
            k,
            k === "extra_notes" ? (v || undefined) : (v ? v : undefined),
          ])
        )
      );
      if (Object.keys(examPayload).length > 0) {
        await api.put(`/visits/${vid}/general-exam`, examPayload);
      }

      navigate(`/visits/${vid}/results`);
    } catch (err) {
      const msg = err.readableMessage || err.message || "Failed to save consultation.";
      setError(`Save failed: ${msg}`);
      setBusyLabel("");
    }
  }

  const setD = (key) => (v) => setDemo((s) => ({ ...s, [key]: v }));
  const setV = (key) => (v) => setVisitInfo((s) => ({ ...s, [key]: v }));
  const setH = (key) => (v) => setHpi((s) => ({ ...s, [key]: v }));

  return (
    <div className="container">
      <form onSubmit={handleSubmit}>
        <div className="flex items-center justify-between gap-4 mb-4">
          <div>
            <h1>New consultation</h1>
            <p className="text-sm text-slate-500">Record a patient encounter, extract notes, and generate an AI-assisted differential diagnosis.</p>
          </div>
        </div>

        {fillFeedback && (
          <div className="mb-5 rounded-xl border border-emerald-200 bg-emerald-50/90 p-4 text-sm font-medium text-emerald-800 shadow-sm flex items-center justify-between dark:border-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-200">
            <span>{fillFeedback}</span>
            <button
              type="button"
              onClick={() => setFillFeedback("")}
              className="text-emerald-700 hover:text-emerald-900 dark:text-emerald-300 dark:hover:text-emerald-100 font-bold ml-3"
            >
              ✕
            </button>
          </div>
        )}

        <ClinicalNoteExtractor onExtractAndFill={handleExtractAndFill} />

        <FormSection title="2.1 Patient demographics">
          <div className="grid-2">
          <TextInput id="full_name" label="Full name *" value={demo.full_name} onChange={setD("full_name")} />
          <TextInput id="mrn" label="MRN (optional)" value={demo.mrn} onChange={setD("mrn")} />
          <TextInput id="dob" label="Date of birth" type="date" value={demo.date_of_birth} onChange={setD("date_of_birth")} />
          <SelectInput id="sex" label="Sex" value={demo.sex} onChange={setD("sex")}
            options={[
              { value: "female", label: "Female" },
              { value: "male", label: "Male" },
              { value: "other", label: "Other" },
              { value: "unknown", label: "Unknown" },
            ]} />
          <TextInput id="gender" label="Gender identity (optional)" value={demo.gender_identity} onChange={setD("gender_identity")} />
          <TextInput id="occupation" label="Occupation" value={demo.occupation} onChange={setD("occupation")} />
          <TextInput id="weight" label={`Weight (kg)${bmi ? ` - BMI ${bmi}` : ""}`} type="number" step="0.1" value={demo.weight_kg} onChange={setD("weight_kg")} />
          <TextInput id="height" label="Height (cm)" type="number" step="0.1" value={demo.height_cm} onChange={setD("height_cm")} />
          <TextInput id="phone" label="Phone" value={demo.phone} onChange={setD("phone")} />
          <TextInput id="pemail" label="Email" type="email" value={demo.email} onChange={setD("email")} />
        </div>
        <TextArea id="address" label="Address" value={demo.address} onChange={setD("address")} rows={2} />
      </FormSection>

      <FormSection title="2.2 Visit information">
        <div className="grid-3">
          <TextInput id="occurred_at" label="Date & time" type="datetime-local" value={visitInfo.occurred_at} onChange={setV("occurred_at")} />
          <SelectInput id="vtype" label="Visit type" value={visitInfo.visit_type} onChange={setV("visit_type")}
            options={[
              { value: "new", label: "New patient" },
              { value: "follow_up", label: "Follow-up" },
              { value: "emergency", label: "Emergency" },
              { value: "telehealth", label: "Telehealth" },
            ]} />
          <TextInput id="refdoc" label="Referring doctor (if any)" value={visitInfo.referring_doctor_name} onChange={setV("referring_doctor_name")} />
        </div>
        <p className="muted">Attending doctor: you ({user.email})</p>
      </FormSection>

      <FormSection title="2.3 Chief complaint">
        <TextArea id="cc" label="What brought the patient in today?" value={visitInfo.chief_complaint} onChange={setV("chief_complaint")} rows={2} />
        <div className="grid-3">
          <TextInput id="cdur" label="Duration" placeholder="e.g. 3 days" value={visitInfo.complaint_duration} onChange={setV("complaint_duration")} />
          <TextInput id="sev" label="Severity (1-10)" type="number" min="1" max="10" value={visitInfo.severity_score} onChange={setV("severity_score")} />
          <SelectInput id="prog" label="Progression" value={visitInfo.progression} onChange={setV("progression")}
            options={[
              { value: "", label: "-" },
              { value: "improving", label: "Improving" },
              { value: "worsening", label: "Worsening" },
              { value: "stable", label: "Stable" },
              { value: "fluctuating", label: "Fluctuating" },
            ]} />
        </div>
      </FormSection>

      <FormSection title="2.4 History of present illness (OPQRST)" hint="Optional - fill what is relevant.">
        <div className="grid-2">
          <TextInput id="onset" label="Onset (sudden/gradual)" value={hpi.hpi_onset} onChange={setH("hpi_onset")} />
          <TextInput id="loc" label="Location" value={hpi.hpi_location} onChange={setH("hpi_location")} />
          <TextInput id="char" label="Character (sharp/dull/burning...)" value={hpi.hpi_character} onChange={setH("hpi_character")} />
          <TextInput id="timing" label="Timing (constant/intermittent...)" value={hpi.hpi_timing} onChange={setH("hpi_timing")} />
          <TextInput id="rad" label="Radiation" value={hpi.hpi_radiation} onChange={setH("hpi_radiation")} />
        </div>
        <div className="grid-2">
          <TextArea id="agg" label="Aggravating factors" value={hpi.hpi_aggravating_factors} onChange={setH("hpi_aggravating_factors")} rows={2} />
          <TextArea id="rel" label="Relieving factors" value={hpi.hpi_relieving_factors} onChange={setH("hpi_relieving_factors")} rows={2} />
        </div>
      </FormSection>

      <FormSection title="2.5 Symptom checklist"
        hint="Marked 'present' symptoms are used by the classifier and reasoning engine.">
        <SymptomChecklist entries={symptoms} onChange={setSymptoms} />
      </FormSection>

      <FormSection title="2.6 Vitals" hint="Leave blank what was not measured.">
        <div className="grid-4">
          <TextInput id="temp" label="Temp (C)" type="number" step="0.1" value={vitals.temperature_c} onChange={(v) => setVitals((s) => ({ ...s, temperature_c: v }))} />
          <TextInput id="sysbp" label="Systolic BP" type="number" value={vitals.systolic_bp} onChange={(v) => setVitals((s) => ({ ...s, systolic_bp: v }))} />
          <TextInput id="diabp" label="Diastolic BP" type="number" value={vitals.diastolic_bp} onChange={(v) => setVitals((s) => ({ ...s, diastolic_bp: v }))} />
          <TextInput id="hr" label="Heart rate" type="number" value={vitals.heart_rate} onChange={(v) => setVitals((s) => ({ ...s, heart_rate: v }))} />
          <TextInput id="rr" label="Resp. rate" type="number" value={vitals.respiratory_rate} onChange={(v) => setVitals((s) => ({ ...s, respiratory_rate: v }))} />
          <TextInput id="spo2" label="SpO2 (%)" type="number" step="0.1" value={vitals.spo2} onChange={(v) => setVitals((s) => ({ ...s, spo2: v }))} />
          <TextInput id="gluc" label="Glucose (mg/dL)" type="number" value={vitals.blood_glucose_mg_dl} onChange={(v) => setVitals((s) => ({ ...s, blood_glucose_mg_dl: v }))} />
          <TextInput id="pain" label="Pain score (0-10)" type="number" min="0" max="10" value={vitals.pain_score} onChange={(v) => setVitals((s) => ({ ...s, pain_score: v }))} />
        </div>
      </FormSection>

      <FormSection title="2.7 Past medical history"
        hint="Use Category = Family history to record diseases in parents/siblings.">
        <ListEditor
          entries={history}
          onChange={setHistory}
          addLabel="Add history entry"
          makeNew={() => ({ category: "chronic_condition", name: "", onset_year: "" })}
          columns={[
            { key: "category", label: "Category", type: "select", options: [
              { value: "chronic_condition", label: "Chronic condition" },
              { value: "surgery", label: "Surgery" },
              { value: "hospitalization", label: "Hospitalization" },
              { value: "immunization", label: "Immunization" },
              { value: "family_history", label: "Family history" },
            ]},
            { key: "name", label: "Name", placeholder: "e.g. Hypertension" },
            { key: "onset_year", label: "Onset year", type: "number", min: "1900", max: "2100" },
            { key: "resolved", label: "Resolved?", type: "checkbox" },
          ]}
        />
      </FormSection>

      <FormSection title="2.8 Medications & allergies">
        <h3>Current medications</h3>
        <ListEditor
          entries={medications}
          onChange={setMedications}
          addLabel="Add medication"
          makeNew={() => ({ name: "", dose: "", frequency: "" })}
          columns={[
            { key: "name", label: "Name", placeholder: "e.g. Amlodipine" },
            { key: "dose", label: "Dose", placeholder: "e.g. 5 mg" },
            { key: "frequency", label: "Frequency", placeholder: "e.g. once daily" },
          ]}
        />
        <h3>Allergies</h3>
        <ListEditor
          entries={allergies}
          onChange={setAllergies}
          addLabel="Add allergy"
          makeNew={() => ({ allergen: "", type: "drug", reaction: "" })}
          columns={[
            { key: "allergen", label: "Allergen", placeholder: "e.g. Penicillin" },
            { key: "type", label: "Type", type: "select", options: [
              { value: "drug", label: "Drug" },
              { value: "food", label: "Food" },
              { value: "environmental", label: "Environmental" },
              { value: "other", label: "Other" },
            ]},
            { key: "reaction", label: "Reaction", placeholder: "e.g. hives" },
          ]}
        />
      </FormSection>

      <FormSection title="2.9 Personal history" hint="Fill what is relevant for this case.">
        <h3>Personal & social</h3>
        <div className="grid-3">
          <SelectInput id="smoke" label="Smoking" value={social.smoking_status} onChange={(v) => setSocial((s) => ({ ...s, smoking_status: v }))}
            options={[
              { value: "never", label: "Never" },
              { value: "former", label: "Former" },
              { value: "current", label: "Current" },
              { value: "unknown", label: "Unknown" },
            ]} />
          <TextInput id="packyears" label="Pack-years" type="number" min="0" value={social.pack_years} onChange={(v) => setSocial((s) => ({ ...s, pack_years: v }))} />
          <TextInput id="alc" label="Alcohol use" value={social.alcohol_use} onChange={(v) => setSocial((s) => ({ ...s, alcohol_use: v }))} />
          <SelectInput id="diet" label="Diet" value={social.diet} onChange={(v) => setSocial((s) => ({ ...s, diet: v }))}
            options={[
              { value: "", label: "-" },
              { value: "vegetarian", label: "Vegetarian" },
              { value: "non_veg", label: "Non-veg" },
              { value: "eggetarian", label: "Eggetarian" },
            ]} />
          <SelectInput id="sleep" label="Sleep" value={social.sleep} onChange={(v) => setSocial((s) => ({ ...s, sleep: v }))}
            options={[
              { value: "", label: "-" },
              { value: "adequate", label: "Adequate" },
              { value: "inadequate", label: "Not adequate" },
            ]} />
          <SelectInput id="bowel" label="Bowel movements" value={social.bowel_movements} onChange={(v) => setSocial((s) => ({ ...s, bowel_movements: v }))}
            options={[
              { value: "", label: "-" },
              { value: "regular", label: "Regular" },
              { value: "irregular", label: "Irregular" },
            ]} />
          <SelectInput id="bladder" label="Bladder frequency" value={social.bladder_frequency} onChange={(v) => setSocial((s) => ({ ...s, bladder_frequency: v }))}
            options={[
              { value: "", label: "-" },
              { value: "normal", label: "Normal" },
              { value: "abnormal", label: "Abnormal" },
            ]} />
          <TextInput id="addictions" label="Addictions (tobacco etc.)" value={social.addictions} onChange={(v) => setSocial((s) => ({ ...s, addictions: v }))} />
          <TextInput id="drugs" label="Recreational drugs" value={social.recreational_drug_use} onChange={(v) => setSocial((s) => ({ ...s, recreational_drug_use: v }))} />
          <TextInput id="exer" label="Exercise" value={social.exercise} onChange={(v) => setSocial((s) => ({ ...s, exercise: v }))} />
          <TextInput id="living" label="Living situation" value={social.living_situation} onChange={(v) => setSocial((s) => ({ ...s, living_situation: v }))} />
          <TextInput id="occexp" label="Occupational exposure" value={social.occupational_exposure} onChange={(v) => setSocial((s) => ({ ...s, occupational_exposure: v }))} />
        </div>
        {demo.sex === "female" && (
          <>
            <h3>Menstrual history (if applicable)</h3>
            <div className="grid-2">
              <TextInput id="lmp" label="LMP - last menstrual period" type="date" value={social.lmp_date} onChange={(v) => setSocial((s) => ({ ...s, lmp_date: v }))} />
              <TextInput id="menstrual" label="Cycle details" placeholder="e.g. regular 28-day cycles" value={social.menstrual_history} onChange={(v) => setSocial((s) => ({ ...s, menstrual_history: v }))} />
            </div>
          </>
        )}
        <TextArea id="travel" label="Travel history" value={social.travel_history} onChange={(v) => setSocial((s) => ({ ...s, travel_history: v }))} rows={2} />
        <TextArea id="sexual" label="Sexual history (only if relevant)" value={social.sexual_history} onChange={(v) => setSocial((s) => ({ ...s, sexual_history: v }))} rows={2} />
      </FormSection>

      <FormSection title="General examination"
        hint="Leave as '-' for anything not assessed.">
        <div className="grid-3">
          {[["pallor", "Pallor"], ["edema", "Edema"], ["cyanosis", "Cyanosis"],
            ["clubbing", "Clubbing"], ["lymphadenopathy", "Lymphadenopathy"],
            ["dehydration", "Dehydration"]].map(([key, label]) => (
            <SelectInput key={key} id={key} label={label} value={exam[key]}
              onChange={(v) => setExam((s) => ({ ...s, [key]: v }))}
              options={[
                { value: "", label: "-" },
                { value: "absent", label: "Absent" },
                { value: "present", label: "Present" },
              ]} />
          ))}
        </div>
        <TextArea id="examnotes" label="Other exam findings" value={exam.extra_notes} onChange={(v) => setExam((s) => ({ ...s, extra_notes: v }))} rows={2} />
      </FormSection>

      <FormSection title="2.12 Working notes" hint="Free-text clinical impressions - sent to the reasoning engine as extra context.">
        <TextArea id="notes" label="Notes" value={workingNotes} onChange={setWorkingNotes} rows={5} />
      </FormSection>

      {error && <div className="error" role="alert">{error}</div>}
      <button type="submit" disabled={Boolean(busyLabel)}>
        {busyLabel || "Save consultation"}
      </button>
    </form>
    </div>
  );
}
