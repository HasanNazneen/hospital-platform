import random
import secrets
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from faker import Faker

from accounts.models import User
from clinic.models import Admission, Appointment, Bed, Billing, Hospital, LabTest, Patient

fake = Faker("en_IN")
Faker.seed(42)
random.seed(42)

HOSPITALS = [
    ("Pink City Hospital", "Jaipur"),
    ("Amber Medical Centre", "Jaipur"),
    ("Aravali Multispeciality", "Jaipur"),
    ("Rajputana Clinic", "Jaipur"),
]
BEDS_PER_HOSPITAL = 40

# Free text on purpose: abbreviations, question marks, mixed styles, a few unmappable ones
DIAGNOSES = [
    "fever x3d", "Viral fever", "fever with chills ?malaria", "UTI", "urinary tract infection",
    "burning micturition ?UTI", "chest pain", "chest pain ?cardiac", "c/o chest pain, r/o MI",
    "type 2 DM, uncontrolled", "diabetes mellitus", "DM2 with high sugar", "HTN", "high BP",
    "hypertension, headache", "gastroenteritis", "loose motions + vomiting", "pneumonia",
    "LRTI", "fracture rt radius", "appendicitis", "dengue ?NS1 +ve", "asthma exacerbation",
    "weakness ? cause", "abd pain", "post-op observation",
]
LAB_TESTS = ["CBC", "Blood sugar (F)", "Creatinine", "Urine routine",
             "Liver function", "Chest X-ray", "ECG", "Dengue NS1"]


def make_phone():
    return f"{random.choice('6789')}{random.randint(10**8, 10**9 - 1)}"


def mess_name(name):
    """Return a sloppy version of a name, like a second registration at a front desk."""
    kind = random.choice(["upper", "lower", "space", "typo", "prefix"])
    if kind == "upper":
        return name.upper()
    if kind == "lower":
        return name.lower()
    if kind == "space":
        return name.replace(" ", "  ", 1)
    if kind == "typo" and len(name) > 4:
        i = random.randint(1, len(name) - 2)
        return name[:i] + name[i + 1:]
    return "Mr. " + name


def build_timeline(window_start, today):
    """Non-overlapping (admit, discharge) pairs for one patient."""
    n = random.choices([0, 1, 2, 3, 4], [40, 35, 15, 7, 3])[0]
    out = []
    d = window_start + timedelta(days=random.randint(0, 200))
    for _ in range(n):
        los = random.choices(range(1, 15),
                             weights=[10, 16, 16, 14, 11, 8, 6, 5, 4, 3, 2, 2, 2, 1])[0]
        discharge = d + timedelta(days=los)
        if discharge >= today - timedelta(days=1):
            break
        out.append((d, discharge))
        gap = random.randint(2, 28) if random.random() < 0.25 else random.randint(30, 150)
        d = discharge + timedelta(days=gap)
    return out


class Command(BaseCommand):
    help = "Seed 4 hospitals with synthetic, deliberately messy data"

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete earlier seeded data first")
        parser.add_argument("--patients", type=int, default=300, help="Patients per hospital")

    @transaction.atomic
    def handle(self, *args, **opts):
        existing = Hospital.objects.filter(name__in=[h[0] for h in HOSPITALS])
        if existing.exists():
            if not opts["reset"]:
                self.stdout.write("Seed data already exists. Use --reset to rebuild.")
                return
            Patient.objects.filter(hospital__in=existing).delete()
            existing.delete()

        today = date.today()
        window_start = today - timedelta(days=365)

        # Doctors (random password, printed once)
        password = secrets.token_urlsafe(10)
        doctors = []
        for i in range(1, 9):
            email = f"seed.doctor{i}@hospital.test"
            u = User.objects.filter(email=email).first()
            if not u:
                u = User.objects.create_user(
                    username=email, email=email, password=password,
                    first_name=fake.first_name(), last_name=fake.last_name(), role="doctor")
            doctors.append(u)

        # Hospitals and beds
        hospitals, beds_by_h = [], {}
        for name, city in HOSPITALS:
            h = Hospital.objects.create(name=name, city=city)
            beds_by_h[h.id] = Bed.objects.bulk_create(
                [Bed(hospital=h, label=f"B-{i:03d}") for i in range(1, BEDS_PER_HOSPITAL + 1)])
            hospitals.append(h)

        # Patients, then duplicates (~5%) with different IDs and sloppy names
        counter, base = 0, []
        for idx, h in enumerate(hospitals, start=1):
            for _ in range(opts["patients"]):
                counter += 1
                base.append(Patient(
                    hospital=h, source_patient_id=f"H{idx}-{counter:05d}", name=fake.name(),
                    dob=fake.date_of_birth(minimum_age=1, maximum_age=90), phone=make_phone()))
        Patient.objects.bulk_create(base)

        dupes = []
        for orig in random.sample(base, k=int(len(base) * 0.05)):
            counter += 1
            h = random.choice(hospitals)
            dupes.append(Patient(
                hospital=h, source_patient_id=f"H{hospitals.index(h) + 1}-{counter:05d}",
                name=mess_name(orig.name), dob=orig.dob,
                phone=orig.phone if random.random() < 0.7 else ""))
        Patient.objects.bulk_create(dupes)
        patients = base + dupes

        # Admissions (~8% lose their discharge date)
        admissions, by_hosp, missing = [], {}, 0
        for p in patients:
            by_hosp.setdefault(p.hospital_id, []).append(p)
            for adm, dis in build_timeline(window_start, today):
                lost = random.random() < 0.08
                missing += lost
                admissions.append(Admission(
                    patient=p, bed=None if lost else random.choice(beds_by_h[p.hospital_id]),
                    admit_date=adm, discharge_date=None if lost else dis,
                    diagnosis_raw="" if random.random() < 0.06 else random.choice(DIAGNOSES)))

        # Patients who are in a bed right now
        for h in hospitals:
            for bed in random.sample(beds_by_h[h.id], k=random.randint(12, 28)):
                admissions.append(Admission(
                    patient=random.choice(by_hosp[h.id]), bed=bed,
                    admit_date=today - timedelta(days=random.randint(0, 9)),
                    diagnosis_raw=random.choice(DIAGNOSES)))
        Admission.objects.bulk_create(admissions)

        # Lab tests and inpatient bills
        labs, bills = [], []
        for a in admissions:
            for t in random.sample(LAB_TESTS, k=random.randint(1, 3)):
                labs.append(LabTest(patient_id=a.patient_id, admission=a, test_name=t,
                                    result_value=str(round(random.uniform(1, 200), 1)),
                                    test_date=a.admit_date))
            if a.discharge_date:
                los = max((a.discharge_date - a.admit_date).days, 1)
                bills.append(Billing(patient_id=a.patient_id, admission=a, visit_type="ipd",
                                     amount=Decimal(random.randint(2500, 6000) * los),
                                     billed_on=a.discharge_date))

        # OPD visits: past appointments plus bills
        used, opd = set(), []
        for _ in range(opts["patients"] * len(hospitals)):
            p, d = random.choice(patients), random.choice(doctors)
            day = today - timedelta(days=random.randint(1, 365))
            slot = timezone.make_aware(
                datetime.combine(day, time(random.randint(9, 16), random.choice([0, 15, 30, 45]))))
            if (d.id, slot) in used:
                continue
            used.add((d.id, slot))
            opd.append(Appointment(patient=p, doctor=d, slot=slot, status="done"))
            bills.append(Billing(patient=p, visit_type="opd",
                                 amount=Decimal(random.randint(300, 1500)), billed_on=day))
        Appointment.objects.bulk_create(opd)
        LabTest.objects.bulk_create(labs)
        Billing.objects.bulk_create(bills)

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(hospitals)} hospitals, {len(patients)} patients "
            f"({len(dupes)} injected duplicates), {len(admissions)} admissions "
            f"({missing} with lost discharge date), {len(opd)} OPD visits."))
        self.stdout.write(f"Seed doctor login: seed.doctor1@hospital.test / {password}  (shown once)")