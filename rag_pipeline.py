import chromadb

# =====================================================
# DATABASES
# =====================================================
client = chromadb.PersistentClient(path="vector_db")
college_db = client.get_collection("college_catalog_db")
cutoff_db = client.get_collection("cutoff_db")

# =====================================================
# COURSES (UNCHANGED — AS REQUESTED)
# =====================================================
COURSES = {
    "aero": "aeronautical engineering",
    "ece": "electronics and communication engineering",
    "eee": "electrical & electronics engineering",
    "vlsi": "(vlsi) verylarge scale integration engineering",
    "industrial": "industrial engineering",
    "mech": "mechanical engineering",
    "mechanical": "mechanical engineering",
    "cse": "computer science engineering",
    "civil": "civil engineering",
    "it": "information technology engineering",
    "auto": "automobile engineering",
    "aids": "ai & data science engineering",
    "ceramic": "ceramic engineering",
    "robotics": "robotics & automation engineering",
    "biotech": "biotech engineering",
    "mechatronics": "mechatronics engineering",
    "bio medical": "bio medical engineering",
    "biomedical": "bio medical engineering",
    "bme": "bio medical engineering",
    "chemical": "chemical engineering",
    "textile technology": "textile technology engineering",
    "food technology": "food technology engineering"
}

# =====================================================
# EXTRACTORS
# =====================================================
def extract_course(query: str):
    for key, value in COURSES.items():
        if key in query:
            return value
    return None


CATEGORIES = {"bc", "oc", "mbc", "bcm", "sc", "sca", "st"}

def extract_category(query: str):
    for c in CATEGORIES:
        if c in query:
            return c
    return None


def extract_year(query: str):
    for y in ("2024", "2023", "2022"):
        if y in query:
            return int(y)
    return 2024


DISTRICTS = {
    "ariyalur","chengalpattu","chennai","coimbatore","cuddalore",
    "dharmapuri","dindigul","erode","kancheepuram","kanyakumari",
    "krishnagiri","madurai","nagappattinam","ramanathapuram",
    "salem","sivagangai","thanjavur","theni","thoothukudi",
    "thiruvannamalai","tiruchirappalli","trichy","tirunelveli",
    "vellore","villupuram"
}

def extract_district(query: str):
    for d in DISTRICTS:
        if d in query:
            return d
    return None

# =====================================================
# ROUTERS
# =====================================================
def is_cutoff_query(q: str) -> bool:
    return "cutoff" in q or any(c in q for c in CATEGORIES)


def is_college_query(q: str) -> bool:
    return "college" in q or "colleges" in q

# =====================================================
# DB FETCH FUNCTIONS (STRICT & CORRECT)
# =====================================================
def fetch_cutoff(district, course, category, year):
    """
    STRICT MODE:
    Returns ONLY colleges that truly have
    (district + course + category + year) rows
    """

    res = cutoff_db.get(
        where={
            "$and": [
                {"district": district},
                {"course": course},
                {"category": category},
                {"year": year}
            ]
        }
    )

    docs = res.get("documents", [])
    if not docs:
        return ["No cutoff data found."]

    output = []
    for doc in docs:
        name = code = cutoff = None

        for line in doc.splitlines():
            l = line.lower()
            if l.startswith("college name"):
                name = line.split(":", 1)[1].strip()
            elif l.startswith("college code"):
                code = line.split(":", 1)[1].strip()
            elif l.startswith("cutoff"):
                cutoff = line.split(":", 1)[1].strip()

        if name and code and cutoff:
            output.append(
                f"{name} | Code: {code} | District: {district.title()} | "
                f"Category: {category.upper()} | Cutoff: {cutoff}"
            )

    return output


def fetch_colleges_by_district(district):
    res = college_db.get(where={"district": district})
    docs = res.get("documents", [])

    if not docs:
        return ["No colleges found."]

    output = []
    for doc in docs:
        name = code = ctype = None

        for line in doc.splitlines():
            l = line.lower()
            if l.startswith("college name"):
                name = line.split(":", 1)[1].strip()
            elif l.startswith("college code"):
                code = line.split(":", 1)[1].strip()
            elif l.startswith("college type"):
                ctype = line.split(":", 1)[1].strip()

        if name and code:
            output.append(
                f"{name} (Code: {code}, District: {district.title()}, Type: {ctype})"
            )

    return output

# =====================================================
# MAIN ENTRY
# =====================================================
def handle_query(user_question: str):
    q = user_question.lower()

    # ---- CUTOFF ----
    if is_cutoff_query(q):
        district = extract_district(q)
        course = extract_course(q)
        category = extract_category(q)
        year = extract_year(q)

        if not all([district, course, category]):
            return ["Please specify district, course and category."]

        return fetch_cutoff(district, course, category, year)

    # ---- COLLEGES ----
    if is_college_query(q):
        district = extract_district(q)
        if not district:
            return ["Please specify a district."]
        return fetch_colleges_by_district(district)

    # ---- HARD STOP ----
    return ["This system only answers college and cutoff related queries."]
