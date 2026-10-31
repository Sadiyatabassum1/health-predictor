"""Input validation for patient records."""
import re
from datetime import date, datetime

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")

# Plausible physiological ranges, used to catch typos such as 1979 for cholesterol.
RANGES = {
    "glucose": (20, 800, "mg/dL"),
    "haemoglobin": (3, 25, "g/dL"),
    "cholesterol": (50, 600, "mg/dL"),
}


def parse_dob(text):
    """Accept dd/mm/yyyy (also dd.mm.yyyy or dd-mm-yyyy). Return (date, error)."""
    text = (text or "").strip()
    if not text:
        return None, "Date of birth is required."
    text = text.replace(".", "/").replace("-", "/")
    if not re.fullmatch(r"\d{2}/\d{2}/\d{4}", text):
        return None, "Date of birth must be in dd/mm/yyyy format."
    try:
        dob = datetime.strptime(text, "%d/%m/%Y").date()
    except ValueError:
        return None, "Date of birth is not a real calendar date."
    if dob > date.today():
        return None, "Date of birth cannot be in the future."
    if dob.year < 1900:
        return None, "Date of birth is too far in the past."
    return dob, None


def parse_number(text, field):
    label = field.capitalize()
    text = (text or "").strip()
    if not text:
        return None, f"{label} is required."
    try:
        value = float(text)
    except ValueError:
        return None, f"{label} must be a number."
    low, high, unit = RANGES[field]
    if not (low <= value <= high):
        return None, f"{label} must be between {low} and {high} {unit}."
    return value, None


def validate_record(form):
    """Validate raw form input. Returns (clean_dict, errors_list)."""
    errors = []
    clean = {}

    name = " ".join((form.get("full_name") or "").split())
    if not name:
        errors.append("Full name is required.")
    elif len(name) > 100 or not re.fullmatch(r"[A-Za-z][A-Za-z .'-]*", name):
        errors.append("Full name may contain only letters, spaces, apostrophes, dots and hyphens.")
    clean["full_name"] = name

    dob, err = parse_dob(form.get("dob"))
    if err:
        errors.append(err)
    clean["dob"] = dob.strftime("%d/%m/%Y") if dob else None

    email = (form.get("email") or "").strip()
    if not email:
        errors.append("Email address is required.")
    elif not EMAIL_RE.match(email):
        errors.append("Email address is not in a valid format (e.g. name@example.com).")
    clean["email"] = email.lower()

    for field in ("glucose", "haemoglobin", "cholesterol"):
        value, err = parse_number(form.get(field), field)
        if err:
            errors.append(err)
        clean[field] = value

    return clean, errors
