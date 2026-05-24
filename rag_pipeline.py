import chromadb
from difflib import get_close_matches
import re
from datetime import datetime
import json
import html
try:
    from llm_api import call_llm
except ImportError:
    call_llm = None

# =====================================================
# DATABASES
# =====================================================
client = chromadb.PersistentClient(path="vector_db")
college_db = client.get_collection("college_catalog_db")
cutoff_db = client.get_collection("cutoff_db")
query_history_db = client.get_or_create_collection("query_history_db")

# =====================================================
# COURSES (UNCHANGED — AS REQUESTED)
# =====================================================
COURSES = {
    "aero": "aeronautical engineering",
    "aeroengineering": "aeronautical engineering",
    "aeronautical": "aeronautical engineering",
    "electronics and communication": "electronics and communication engineering",
    "electronics & communication": "electronics and communication engineering",
    "ece": "electronics and communication engineering",
    "communication": "electronics and communication engineering",
    "electronicscommunication": "electronics and communication engineering",
    "electronics communication": "electronics and communication engineering",
    "eee": "electrical & electronics engineering",
    "electrical & electronics": "electrical & electronics engineering",
    "electrical and electronics": "electrical & electronics engineering",
    "electrical electronics": "electrical & electronics engineering",
    "electrical electronics": "electrical & electronics engineering",
    "vlsi": "(vlsi) verylarge scale integration engineering",
    "verylarge scale integration": "(vlsi) verylarge scale integration engineering",
    "verylargescale integration": "(vlsi) verylarge scale integration engineering",
    "verylargescaleintegration": "(vlsi) verylarge scale integration engineering",
    "industrial": "industrial engineering",
    "industry": "industrial engineering",
    "mech": "mechanical engineering",
    "mechanical": "mechanical engineering",
    "cse": "computer science engineering",
    "computer science": "computer science engineering",
    "computerscience": "computer science engineering",
    "computer": "computer science engineering",
    "civil": "civil engineering",
    "it": "information technology engineering",
    "information": "information technology engineering",
    "informationtechnology": "information technology engineering",
    "auto": "automobile engineering",
    "aids": "ai & data science engineering",
    "ds": "ai & data science engineering",
    "data science": "ai & data science engineering",
    "ceramic": "ceramic engineering",
    "robotics": "robotics & automation engineering",
    "robotics and automation": "robotics & automation engineering",
    "robotics & automation": "robotics & automation engineering",
    "robotics automation": "robotics & automation engineering",
    "roboticsautomation": "robotics & automation engineering",
    "biotech": "biotech engineering",
    "bt": "biotech engineering",
    "mechatronics": "mechatronics engineering",
    "mechat": "mechatronics engineering",
    "bio medical": "bio medical engineering",
    "biomedical": "bio medical engineering",
    "bme": "bio medical engineering",
    "chemical": "chemical engineering",
    "textile technology": "textile technology engineering",
    "textile": "textile technology engineering",
    "food technology": "food technology engineering",
    "food": "food technology engineering",
    "ft": "food technology engineering"
}

# =====================================================
# EXTRACTORS
# =====================================================
def normalize_query(query: str) -> str:
    """
    Step 1: Normalize query by replacing abbreviations with full names.
    This should happen FIRST before any other processing.
    """
    q = query.lower()
    
    # Replace abbreviations with full district names
    for abbr, full_name in DISTRICT_ABBREVIATIONS.items():
        # Match as whole word using word boundaries
        words = q.split()
        for i, word in enumerate(words):
            if word == abbr:
                words[i] = full_name
        q = " ".join(words)
    
    return q


def extract_course(query: str):
    """Extract course from query with token-safe matching, then conservative fuzzy fallback."""
    query_lower = query.lower()
    # Keep only alphanumeric tokens for stable matching (ignores punctuation).
    tokens = re.findall(r"[a-z0-9]+", query_lower)
    token_set = set(tokens)

    # 0) Full course-name match (value-side), e.g. "computer science engineering"
    for full_name in sorted(set(COURSES.values()), key=len, reverse=True):
        name_tokens = re.findall(r"[a-z0-9]+", full_name.lower())
        if name_tokens and all(t in token_set for t in name_tokens):
            return full_name

    # 1) Exact token/phrase match (preferred)
    # Sort by key length so specific multi-word keys win first.
    for key, value in sorted(COURSES.items(), key=lambda kv: len(kv[0]), reverse=True):
        key_tokens = key.split()
        if len(key_tokens) == 1:
            if key_tokens[0] in token_set:
                return value
        else:
            if all(t in token_set for t in key_tokens):
                return value

    # 2) Conservative fuzzy fallback for typos like "cs" -> "cse"
    # Avoid fuzzy-matching generic words like "what" into a course key.
    course_keys = list(COURSES.keys())
    for word in tokens:
        if len(word) <= 2:
            continue
        matches = get_close_matches(word, course_keys, n=1, cutoff=0.8)
        if matches:
            matched_key = matches[0]
            # Guard against accidental semantic mismatch in fuzzy mode.
            if matched_key.startswith(word[:2]) or word.startswith(matched_key[:2]):
                return COURSES[matched_key]

    return None


CATEGORIES = {"bc", "oc", "mbc", "bcm", "sc", "sca", "st"}

def extract_category(query: str):
    """Extract category as a whole word/token, not substring."""
    words = query.split()
    for word in words:
        # Ensure lowercase comparison
        word_lower = word.lower()
        if word_lower in CATEGORIES:
            return word_lower
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

# Common abbreviations for districts
DISTRICT_ABBREVIATIONS = {
    "cbe": "coimbatore",
    "ari": "ariyalur",
    "cgl": "chengalpattu",
    "che": "chennai",
    "erd": "erode",
    "knp": "kancheepuram",
    "kpm": "kancheepuram",
    "kgi": "krishnagiri",
    "mdu": "madurai",
    "ngp": "nagappattinam",
    "rmd": "ramanathapuram",
    "tnj": "thanjavur",
    "tut": "thoothukudi",
    "tri": "tirunelveli",
    "vlr": "vellore",
    "vpm": "villupuram",
    "cbr": "coimbatore",
    "coi": "coimbatore",
    "chn": "chennai",
    "trz": "tiruchirappalli",
    "slm": "salem",
    "tni": "thiruvannamalai",
}

# =====================================================
# SYNONYM KEYWORDS & FLEXIBLE MATCHING (NEW)
# =====================================================
KEYWORD_SYNONYMS = {
    # College Keywords (all variations)
    "college_keywords": [
        "college", "colleges", "institute", "institution", "academic",
        "university", "campus", "educational", "school", "institute for",
        "engineering college", "govt college", "government college",
        "private college", "aided college", "list", "listing"
    ],
    
    # Location/District Keywords
    "location_keywords": [
        "in", "located in", "available in", "based in", "near",
        "from", "at", "is in", "place", "location", "area"
    ],
    
    # Offering Keywords
    "offering_keywords": [
        "offer", "offering", "offers", "offered", "have", "has", "having",
        "provide", "provides", "providing", "provided", "available",
        "teach", "teaches", "teaching", "taught", "run", "running",
        "conduct", "conducting", "conducting courses", "stream", "streams"
    ],
    
    # Cutoff Keywords
    "cutoff_keywords": [
        "cutoff", "cutoffs", "cut off", "cut-off", "mark", "marks",
        "score", "scores", "marks scored", "rank", "ranks", "ranking",
        "merit", "merit score", "selection mark", "qualifying mark",
        "minimum mark", "threshold", "marks required", "required marks"
    ],
    
    # Category Keywords
    "category_keywords": list(CATEGORIES),  # bc, oc, mbc, etc.
    
    # Eligibility/Possibility Keywords
    "eligibility_keywords": [
        "possibility", "get seat", "eligible", "qualify", "qualify for",
        "admit", "admission", "admissible", "qualify for admission",
        "can i get", "will i get", "can i secure", "can i obtain",
        "is it possible", "possibility of", "chance of", "chances of",
        "likelihood", "can i manage", "can i secure", "can i reach",
        "would i get", "would i be eligible", "qualifying chances",
        "manage to get", "be able to get", "can secure", "able to get",
        "seat availability", "get admission", "secure seat"
    ],
    
    # Personal Performance Keywords
    "personal_keywords": [
        "i have", "i got", "i scored", "i secured", "i obtained",
        "i achieved", "my score", "my mark", "my marks",
        "can i", "will i", "do i", "am i", "could i", "would i",
        "i'm having", "with", "score is", "got", "just got", "recently got",
        "from my performance", "performance wise"
    ],
    
    # Comparison Keywords
    "comparison_keywords": [
        "compare", "comparing", "compared to", "comparison",
        "differentiate", "difference", "different",
        "similar", "vs vs", "versus", "between",
        "which is better", "which is best", "which one",
        "which should", "best option", "better option",
        "prefer", "choose between", "confused", "i'm confused",
        "help me decide", "which to pick", "which to choose",
        "compare both", "compare 2", "compare two"
    ]
}

# =====================================================
# ADVANCED PREPROCESSING PIPELINE (BEFORE KEYWORD MATCHING)
# =====================================================
def correct_typos_and_preprocess(query: str) -> str:
    """
    STEP 1: Advanced preprocessing pipeline
    Process order:
    1. Common typo/spelling fixes (including keyword typos)
    2. Normalize spacing and punctuation
    3. Expand contractions
    4. Normalize common misspellings
    5. Standardize numbers
    
    This happens BEFORE keyword extraction.
    """
    q = query.lower().strip()
    
    # Fix common typos and misspellings - KEYWORD TYPOS FIRST
    typo_fixes = {
        # Keyword typos
        r'\bcollges\b': 'colleges',
        r'\bcollge\b': 'colleges',
        r'\bcolleges\b': 'colleges',
        r'\binstitute\b': 'institute',
        r'\bscroeds\b': 'scored',
        r'\bscroed\b': 'scored',
        r'\bscored\b': 'scored',
        r'\bscure\b': 'secure',
        r'\bsecured\b': 'secured',
        r'\bsecruity\b': 'security',
        
        # Cutoff variations
        r'\bcut\s*off\b': 'cutoff',
        r'\bcut-off\b': 'cutoff',
        r'\bcutoff\b': 'cutoff',
        r'\bmarks?\b': 'mark',  # mark/marks → mark
        
        # Other common typos
        r'\bi\'ve\b': 'i have',
        r'\bi\'m\b': 'i am',
        r'\bcan\'t\b': 'cannot',
        r'\bwill\'t\b': 'will not',
        r'\bdont\b': 'do not',
        r'\bdoesnt\b': 'does not',
        
        # Course variations
        r'\bcse\b': 'cse',
        r'\bc\.s\.e\b': 'cse',
        r'\bc\.s\.e\.\b': 'cse',
        r'\bece\b': 'ece',
        r'\be\.c\.e\b': 'ece',
        r'\beee\b': 'eee',
        r'\be\.e\.e\b': 'eee',
        r'\bmech\b': 'mechanical',
        r'\bmechanics\b': 'mechanical',
        r'\bcivil\b': 'civil',
        r'\bit\b': 'information technology',  # Only if standalone
        r'\bcs\b': 'computer science',  # cs → computer science
        r'\bcomp\b': 'computer science',
        r'\beng\b': 'engineering',
        r'\bauto\b': 'automobile',
    }
    
    for pattern, replacement in typo_fixes.items():
        q = re.sub(pattern, replacement, q, flags=re.IGNORECASE)
    
    # Fuzzy matching for keywords with typos (if substring match fails)
    # Check for ONLY actual/likely typos with high cutoff (0.8+)
    keyword_fuzzy_fixes = {
        'collges': 'colleges',
        'collge': 'colleges',
        'scroeds': 'scored',
        'scroed': 'scored',
        'cuoff': 'cutoff',
        'cuttoff': 'cutoff',
    }
    
    words = q.split()
    for i, word in enumerate(words):
        for typo, correction in keyword_fuzzy_fixes.items():
            # Use strict cutoff (0.85+) to avoid false positives
            # Only match exact or very close typos
            if word == typo or (len(word) > 4 and get_close_matches(word, [typo], cutoff=0.85)):
                words[i] = correction
    q = ' '.join(words)
    
    # Normalize extra spaces
    q = re.sub(r'\s+', ' ', q).strip()
    
    # Remove extra punctuation but keep hyphens in some cases
    q = re.sub(r'[!?;:,](?=\s|$)', '', q)
    
    return q


def extract_keywords_flexible(query: str, keyword_group: str) -> list:
    """
    STEP 2: After preprocessing, extract keywords with synonym support.
    
    Uses fuzzy matching combined with exact keyword matching.
    Returns list of matched keywords (can be multiple).
    """
    q = query.lower()
    matched = []
    
    if keyword_group not in KEYWORD_SYNONYMS:
        return matched
    
    keywords = KEYWORD_SYNONYMS[keyword_group]
    
    for keyword in keywords:
        # Try exact substring match first
        if keyword in q:
            matched.append(keyword)
        else:
            # Try fuzzy match for typos
            if len(keyword) >= 4:  # Only fuzzy match longer keywords
                matches = get_close_matches(keyword, [q], n=1, cutoff=0.7)
                if matches:
                    matched.append(keyword)
    
    return matched


def has_keywords(query: str, keyword_group: str, min_matches: int = 1) -> bool:
    """Check if query has at least min_matches keywords from a group."""
    keywords = extract_keywords_flexible(query, keyword_group)
    return len(keywords) >= min_matches


def count_keywords(query: str, keyword_group: str) -> int:
    """Count how many keywords from a group are in the query."""
    keywords = extract_keywords_flexible(query, keyword_group)
    return len(keywords)


def extract_district(query: str):
    """
    Extract district from query.
    Query should already be normalized (abbreviations replaced).
    Stage 1: Exact match (with location keyword requirement for safety)
    Stage 2: Fuzzy match (only if location keyword present, typos like 'channi' → 'chennai')
    """
    q = query.lower()
    
    # Check if location keyword is present (used for fuzzy matching gate)
    location_keywords = ['in ', ' in', 'at ', ' at', 'from ', ' from', 'based ', 'located']
    has_location_keyword = any(lk in q for lk in location_keywords)
    
    # Stage 1: Exact match
    for d in DISTRICTS:
        if d in query:
            return d
    
    # Stage 2: Fuzzy match for typos - ONLY if location keyword present
    # This prevents false positives like "colleges" matching "vellore"
    if has_location_keyword:
        words = query.split()
        for word in words:
            if len(word) > 3:  # Longer words only (reduces false positives)
                matches = get_close_matches(word, DISTRICTS, n=1, cutoff=0.75)  # Increased cutoff
                if matches:
                    return matches[0]
    
    return None

# =====================================================
# LLM OUTPUT KEYWORD EXTRACTION
# =====================================================
def extract_keywords_from_output(llm_response: str) -> dict:
    """
    Extract structured keywords from LLM output.
    Returns: {
        'extracted': {
            'cutoff': value or None,
            'category': value or None,
            'colleges': [list] or None,
            'district': value or None
        },
        'remaining_text': unparsed content for further processing
    }
    """
    response_lower = llm_response.lower()
    extracted = {
        'cutoff': None,
        'category': None,
        'colleges': [],
        'district': None
    }
    remaining_lines = []
    
    lines = llm_response.split('\n')
    
    for line in lines:
        line_lower = line.lower()
        matched = False
        
        # Extract DISTRICT
        district_match = extract_district(line_lower)
        if district_match:
            extracted['district'] = district_match
            matched = True
        
        # Extract CATEGORY (bc, oc, mbc, etc.)
        category_match = extract_category(line_lower)
        if category_match:
            extracted['category'] = category_match
            matched = True
        
        # Extract CUTOFF (if line mentions "cutoff")
        if 'cutoff' in line_lower and ('mark' in line_lower or 'rank' in line_lower or any(c in line_lower for c in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'])):
            extracted['cutoff'] = line.strip()
            matched = True
        
        # Extract COLLEGES (look for college names, patterns like "College of Engineering")
        if any(keyword in line_lower for keyword in ['college', 'institute', 'engineering college', 'engineering institute', 'government college']):
            # Avoid matching lines that are just explanatory text
            if len(line.strip()) > 10 and not any(skip in line_lower for skip in ['offer', 'provide', 'here are']):
                extracted['colleges'].append(line.strip())
                matched = True
        
        # If line wasn't matched as a keyword, add to remaining text
        if not matched and line.strip():
            remaining_lines.append(line)
    
    return {
        'extracted': extracted,
        'remaining_text': '\n'.join(remaining_lines)
    }


def format_extracted_keywords(extracted_dict: dict) -> str:
    """Format extracted keywords into a structured response."""
    lines = []
    
    ext = extracted_dict.get('extracted', {})
    
    if ext.get('district'):
        lines.append(f"📍 **District:** {ext['district'].title()}")
    
    if ext.get('category'):
        lines.append(f"📋 **Category:** {ext['category'].upper()}")
    
    if ext.get('cutoff'):
        lines.append(f"📊 **Cutoff:** {ext['cutoff']}")
    
    if ext.get('colleges'):
        lines.append(f"🎓 **Colleges Found:** {len(ext['colleges'])}")
        for college in ext['colleges'][:5]:  # Show max 5
            lines.append(f"   • {college}")
        if len(ext['colleges']) > 5:
            lines.append(f"   ... and {len(ext['colleges']) - 5} more")
    
    return '\n'.join(lines) if lines else None


# =====================================================
# KEYWORD COMBINATION CHECKING (Smart Routing)
# =====================================================
def count_cutoff_keywords(query: str) -> dict:
    """
    Count keywords for CUTOFF queries.
    Required: cutoff + district + category + course
    Returns: {
        'count': number of keywords found,
        'has_cutoff': bool,
        'has_district': bool, 'district': value or None,
        'has_category': bool, 'category': value or None,
        'has_course': bool, 'course': value or None,
        'year': extracted year or None,
        'missing': [list of missing keywords]
    }
    """
    count = 0
    missing = []
    
    # Check for cutoff keyword
    has_cutoff = "cutoff" in query.lower()
    if has_cutoff:
        count += 1
    else:
        missing.append("cutoff")
    
    # Check for district
    district = extract_district(query)
    has_district = district is not None
    if has_district:
        count += 1
    else:
        missing.append("district")
    
    # Check for category
    category = extract_category(query)
    has_category = category is not None
    if has_category:
        count += 1
    else:
        missing.append("category")
    
    # Check for course
    course = extract_course(query)
    has_course = course is not None
    if has_course:
        count += 1
    else:
        missing.append("course")
    
    # Extract year (if present)
    year = extract_year(query)
    
    return {
        'count': count,
        'has_cutoff': has_cutoff,
        'has_district': has_district,
        'district': district,
        'has_category': has_category,
        'category': category,
        'has_course': has_course,
        'course': course,
        'year': year,
        'missing': missing
    }


def count_college_keywords(query: str) -> dict:
    """
    Count keywords for COLLEGE LIST queries.
    Required: (college/colleges) + district + (offer/available)
    Returns: {
        'count': number of keywords found,
        'has_college': bool,
        'has_district': bool, 'district': value or None,
        'has_offer': bool,
        'has_course': bool, 'course': value or None,
        'missing': [list of missing keywords]
    }
    """
    count = 0
    missing = []
    query_lower = query.lower()
    
    # Check for college keyword
    has_college = any(kw in query_lower for kw in ["college", "colleges", "institute", "institution"])
    if has_college:
        count += 1
    else:
        missing.append("college")
    
    # Check for district
    district = extract_district(query)
    has_district = district is not None
    if has_district:
        count += 1
    else:
        missing.append("district")
    
    # Check for offer/available keyword
    has_offer = any(kw in query_lower for kw in ["offer", "offering", "available", "list"])
    if has_offer:
        count += 1
    else:
        missing.append("offer/available")
    
    # Check for course (optional but helpful)
    course = extract_course(query)
    has_course = course is not None
    
    return {
        'count': count,
        'has_college': has_college,
        'has_district': has_district,
        'district': district,
        'has_offer': has_offer,
        'has_course': has_course,
        'course': course,
        'missing': missing
    }


# =====================================================
# REFINED QUERY TYPE DETECTORS (Per User Specification)
# =====================================================

def detect_college_district_only(query: str) -> dict:
    """
    TYPE 1: College List (District Only)
    Keywords: college/colleges + in/available (optional) + district
    MUST NOT have: course or category keywords
    Uses flexible keyword matching with synonyms
    """
    # Use flexible keyword matching (with synonym support)
    has_college = has_keywords(query, "college_keywords", min_matches=1)
    if not has_college:
        return {'match': False, 'district': None}
    
    # Check for district
    district = extract_district(query)
    if not district:
        return {'match': False, 'district': None}
    
    # CRITICAL: Must NOT have course or category keywords
    has_course = extract_course(query) is not None
    has_category = extract_category(query) is not None
    
    if has_course or has_category:
        return {'match': False, 'district': None}
    
    # Check for location keywords (optional)
    has_location = has_keywords(query, "location_keywords", min_matches=1)
    
    return {
        'match': True,
        'district': district,
        'colleges': [],
        'original_query': query
    }


def detect_college_course_query(query: str) -> dict:
    """
    TYPE 2: College Course Query
    Keywords: colleges + offer/have (optional) + course + district
    NO category mentioned
    Uses flexible keyword matching with synonyms
    """
    # Check for college keyword
    has_college = has_keywords(query, "college_keywords", min_matches=1)
    if not has_college:
        return {'match': False, 'district': None, 'course': None}
    
    # Check for course
    course = extract_course(query)
    if not course:
        return {'match': False, 'district': None, 'course': None}
    
    # Check for district
    district = extract_district(query)
    if not district:
        return {'match': False, 'district': None, 'course': None}
    
    # CRITICAL: Must NOT have category keyword
    has_category = extract_category(query) is not None
    if has_category:
        return {'match': False, 'district': None, 'course': None}
    
    # Check for offering keywords (optional)
    has_offering = has_keywords(query, "offering_keywords", min_matches=1)
    
    return {
        'match': True,
        'district': district,
        'course': course,
        'has_offering': has_offering,
        'original_query': query
    }


def detect_eligibility_query(query: str) -> dict:
    """
    TYPE 5: Eligibility Query (NEW)
    Keywords: (I have/scored/secured) + mark (number) + course + category + possibility/get seat
    Uses flexible keyword matching with synonyms
    """
    # Check for eligibility/possibility keywords
    has_eligibility = has_keywords(query, "eligibility_keywords", min_matches=1)
    
    # Check for personal performance keywords
    has_personal = has_keywords(query, "personal_keywords", min_matches=1)
    
    if not (has_eligibility or has_personal):
        return {'match': False}
    
    # Extract cutoff mark (a number in the query)
    cutoff_mark = None
    import re as regex
    numbers = regex.findall(r'\d+\.?\d*', query)
    if numbers:
        cutoff_mark = float(numbers[0])
    
    if not cutoff_mark:
        return {'match': False}
    
    # Extract course, category, district
    course = extract_course(query)
    category = extract_category(query)
    district = extract_district(query)
    
    # Need at least course + category
    if not (course and category):
        return {'match': False}
    
    return {
        'match': True,
        'cutoff_mark': cutoff_mark,
        'course': course,
        'category': category,
        'district': district,
        'original_query': query
    }


# =====================================================
# ROUTERS
# =====================================================
def is_definition_question(q: str) -> bool:
    """
    Detect if query is asking for definition/explanation (NOT data lookup).
    These should be answered by LLM, not RAG database.
    Returns True if question is conceptual (what is, explain, etc.)
    
    EXCLUDES: Queries asking for specific data like cutoffs, colleges, marks, ranks
    """
    # Data-specific keywords that indicate this is NOT a definition question
    data_keywords = {
        "cutoff", "mark", "rank", "college", "colleges", "institute",
        "offering", "offer", "available", "list", "get"
    }
    
    # If query contains data keywords, it's a data query, not definition
    if any(dk in q for dk in data_keywords):
        return False
    
    # Definition signals - only match if NO data keywords
    definition_signals = {
        "what is", "what are", "explain", "meaning", 
        "define", "how to", "how can", "how does",
        "scope of", "career in", "about ", 
        "difference between", "comparison of"
    }
    
    for signal in definition_signals:
        if signal in q:
            return True
    
    return False


def is_cutoff_query(q: str) -> bool:
    """
    Detect CUTOFF queries using smart keyword combination.
    REQUIRES: At least 3 of these 4 keywords: cutoff, district, category, course
    EXCLUDES: Definition questions
    """
    # REJECT definition/explanation questions
    if is_definition_question(q):
        return False
    
    # Check keyword combination
    keywords = count_cutoff_keywords(q)
    
    # Need at least 3 out of 4 keywords for a valid cutoff query
    return keywords['count'] >= 3


def is_college_query(q: str) -> bool:
    """
    Detect COLLEGE LIST queries using smart keyword combination.
    REQUIRES: college + district + (offer/available) = 3 keywords
    EXCLUDES: Definition questions and cutoff queries
    """
    # REJECT definition/explanation questions
    if is_definition_question(q):
        return False
    
    # Exclude if it's clearly a cutoff query
    if is_cutoff_query(q):
        return False
    
    # Check keyword combination
    keywords = count_college_keywords(q)
    
    # Need at least 3 of 3 keywords for a valid college list query
    return keywords['count'] >= 3

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
        base_msg = (
            f"No cutoff data found for {course.title()} in {district.title()} "
            f"for {category.upper()} category ({year})."
        )

        # Try same district/course/category for any other year.
        alt_year_res = cutoff_db.get(
            where={
                "$and": [
                    {"district": district},
                    {"course": course},
                    {"category": category}
                ]
            }
        )
        alt_year_meta = alt_year_res.get("metadatas", [])
        available_years = sorted(
            {
                m.get("year") for m in alt_year_meta
                if isinstance(m, dict) and m.get("year")
            },
            reverse=True
        )
        available_years = [y for y in available_years if y != year]

        if available_years:
            return [
                base_msg,
                "Available years for the same district/course/category: "
                + ", ".join(str(y) for y in available_years[:3])
                + ".",
                "Try adding a year in your query (example: 2023)."
            ]

        # Try same course/category/year across other districts.
        alt_district_res = cutoff_db.get(
            where={
                "$and": [
                    {"course": course},
                    {"category": category},
                    {"year": year}
                ]
            }
        )
        alt_district_meta = alt_district_res.get("metadatas", [])
        available_districts = sorted(
            {
                m.get("district") for m in alt_district_meta
                if isinstance(m, dict) and m.get("district") and m.get("district") != district
            }
        )

        if available_districts:
            suggestion = ", ".join(d.title() for d in available_districts[:8])
            return [
                base_msg,
                f"Available districts for this course/category/year: {suggestion}.",
                "Try changing district (example: Coimbatore / cbe)."
            ]

        return [
            base_msg,
            "No alternate records found for the same course/category in the current dataset."
        ]

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


def fetch_colleges_by_district(district, course=None):
    """
    Fetch colleges by district and optionally by course.
    If course is specified, filters colleges that offer that course.
    """
    res = college_db.get(where={"district": district})
    docs = res.get("documents", [])

    if not docs:
        return ["No colleges found."]

    output = []
    for doc in docs:
        name = code = ctype = courses_offered = None

        for line in doc.splitlines():
            l = line.lower()
            if l.startswith("college name"):
                name = line.split(":", 1)[1].strip()
            elif l.startswith("college code"):
                code = line.split(":", 1)[1].strip()
            elif l.startswith("college type"):
                ctype = line.split(":", 1)[1].strip()
            elif l.startswith("courses offered") or l.startswith("streams"):
                courses_offered = line.split(":", 1)[1].strip().lower()

        # Filter by course if specified
        if course and courses_offered:
            if course.lower() not in courses_offered:
                continue

        if name and code:
            course_info = f", Offers: {courses_offered}" if courses_offered else ""
            output.append(
                f"{name} (Code: {code}, District: {district.title()}, Type: {ctype}{course_info})"
            )

    return output


def check_eligibility(user_score, course, category, district=None):
    """
    TYPE 5: Check if user can get a seat based on cutoff marks.
    Fetches cutoff data and sends to LLM for eligibility analysis.
    Returns: LLM analysis of eligibility
    """
    # Fetch cutoff data for the specified course/category/district
    if district:
        cutoff_data = fetch_cutoff(district, course, category, 2024)
    else:
        # If district not specified, fetch across all districts for this course/category
        res = cutoff_db.get(
            where={
                "$and": [
                    {"course": course},
                    {"category": category},
                    {"year": 2024}
                ]
            }
        )
        documents = res.get("documents", [])
        if not documents:
            return [
                f"No cutoff data found for {course.title()} ({category.upper()}) in our database.",
                f"Cannot determine eligibility without reference cutoff marks."
            ]
        cutoff_data = documents
    
    # Format cutoff data for LLM
    cutoff_text = "\n".join(cutoff_data) if isinstance(cutoff_data, list) else str(cutoff_data)
    
    # Prepare LLM prompt for eligibility analysis
    llm_prompt = f"""analyze if the student can get admission based on the following:

Student's Score: {user_score}
Course: {course.title()}
Category: {category.upper()}
{f"District: {district.title()}" if district else "All Districts"}

AVAILABLE CUTOFF DATA:
{cutoff_text}

Based on this data, provide:
1. Whether the student can likely qualify for admission
2. Which colleges the student might be eligible for
3. Colleges that are borderline (close call)
4. Risk assessment for safety/moderate/ambitious colleges
5. Recommendation on which colleges to target

Be concise and practical in your analysis."""
    
    if call_llm:
        try:
            llm_response = call_llm(llm_prompt, history=[])
            if llm_response and isinstance(llm_response, str):
                return [llm_response]
        except Exception as e:
            print(f"[ELIGIBILITY] LLM error: {e}")
    
    return [cutoff_text]

# =====================================================
# QUERY LOGGING & RETRIEVAL (For comparison & analysis)
# =====================================================
def log_query_to_db(user_question, extracted_data, result_colleges, query_type, session_id=None):
    """
    Log query with CLEAR TYPE DISTINCTION for safe comparisons.
    Stores actual results for side-by-side comparison.
    query_type: 'cutoff' or 'college'
    session_id: User session ID for query isolation
    """
    try:
        if query_type == "cutoff":
            exact_type = "CUTOFF_QUERY"
            comparison_key = f"{extracted_data.get('district')}_{extracted_data.get('course')}_{extracted_data.get('category')}"
        else:
            exact_type = "COLLEGE_LIST_QUERY"
            comparison_key = f"{extracted_data.get('district')}_{extracted_data.get('course')}"
        
        # Serialize college results for later retrieval
        results_json = json.dumps(result_colleges) if result_colleges else "[]"
        
        query_history_db.add(
            ids=[f"query_{datetime.now().timestamp()}"],
            documents=[results_json],  # Store actual results, not just question
            metadatas=[{
                "timestamp": datetime.now().isoformat(),
                "query_type": exact_type,
                "comparison_key": comparison_key,
                "original_question": user_question,
                "district": extracted_data.get("district") or "none",
                "course": extracted_data.get("course") or "none",
                "category": extracted_data.get("category") or "none",
                "year": str(extracted_data.get("year", 2024)),
                "college_count": len(result_colleges) if result_colleges else 0,
                "is_comparable": query_type == "cutoff",
                "session_id": session_id or "default"
            }]
        )
        print(f"[LOG] Query logged: {exact_type} | {comparison_key} | Session: {session_id} | Results: {len(result_colleges) if result_colleges else 0}")
    except Exception as e:
        print(f"Error logging query: {e}")


def retrieve_comparable_queries(limit=5, query_type="cutoff", session_id=None):
    """
    Retrieve ONLY same-type queries for valid comparison.
    query_type: 'cutoff', 'college', or 'any'
    session_id: Filter queries by user session (isolates users)
    Returns queries with actual college/cutoff results
    """
    try:
        # Build where clause with session_id filter
        where_clause = None
        
        if query_type == "cutoff":
            where_clause = {"query_type": "CUTOFF_QUERY"}
        elif query_type == "college":
            where_clause = {"query_type": "COLLEGE_LIST_QUERY"}
        
        # Add session_id filter if provided
        if session_id:
            session_filter = {"session_id": session_id or "default"}
            if where_clause:
                where_clause = {"$and": [where_clause, session_filter]}
            else:
                where_clause = session_filter
        
        if where_clause:
            res = query_history_db.get(
                where=where_clause,
                include=["documents", "metadatas"]
            )
        else:
            res = query_history_db.get(
                include=["documents", "metadatas"]
            )
        
        queries = []
        for doc, meta in zip(res.get("documents", []), res.get("metadatas", [])):
            try:
                # Deserialize the college results
                results = json.loads(doc) if doc else []
            except:
                results = []
            
            queries.append({
                "original_question": meta.get("original_question", ""),
                "results": results,  # Actual college/cutoff data
                "query_type": meta.get("query_type"),
                "district": meta.get("district"),
                "course": meta.get("course"),
                "category": meta.get("category"),
                "year": meta.get("year"),
                "timestamp": meta.get("timestamp"),
                "college_count": meta.get("college_count"),
                "is_comparable": meta.get("is_comparable"),
                "session_id": meta.get("session_id")
            })
        
        # Newest-first ordering to avoid stale comparisons from old chats.
        def _ts_value(item):
            ts = item.get("timestamp")
            if not ts:
                return datetime.min
            try:
                return datetime.fromisoformat(ts)
            except Exception:
                return datetime.min

        queries.sort(key=_ts_value, reverse=True)
        recent = queries[:limit]

        print(f"[RETRIEVE] Found {len(queries)} total {query_type} queries for session {session_id}, returning latest {len(recent)}")
        return recent
    except Exception as e:
        print(f"Error retrieving queries: {e}")
        return []


def format_comparison_for_llm(queries, query_type_label):
    """Format comparison data as text for LLM analysis"""
    if not queries:
        return "No comparison data available"
    
    text = f"\n{query_type_label} QUERY COMPARISON DATA:\n"
    text += "=" * 80 + "\n\n"
    
    for i, q in enumerate(queries, 1):
        text += f"QUERY {i}:\n"
        text += f"  Original Question: {q.get('original_question', 'N/A')}\n"
        text += f"  District: {q['district'].title()}\n"
        text += f"  Course: {q['course']}\n"
        if q.get('category') and q['category'] != 'none':
            text += f"  Category: {q['category'].upper()}\n"
        text += f"  Year: {q['year']}\n"
        
        # Display actual results
        results = q.get('results', [])
        if results and isinstance(results, list):
            text += f"  Results ({len(results)} colleges):\n"
            for result in results:
                if isinstance(result, str):
                    text += f"    • {result}\n"
        else:
            text += f"  Results: {q.get('college_count', 0)} colleges found\n"
        
        text += "\n"
    
    text += "=" * 80 + "\n"
    return text


def format_comparison_html(llm_response, query_type="CUTOFF"):
    """Format LLM comparison response as styled HTML for UI with gold theme."""
    
    # Icon based on query type
    icon = "📊" if query_type == "CUTOFF" else "🎓"
    title = "Cutoff Comparison Analysis" if query_type == "CUTOFF" else "College Options Analysis"
    
    html = f"""<div style="background: rgba(201, 168, 76, 0.08); border-left: 5px solid #c9a84c; padding: 22px 18px; border-radius: 10px; margin: 12px 0; font-size: 13px; line-height: 1.85;">
    <div style="color: #ffd700; font-weight: 700; font-size: 15px; margin-bottom: 16px; display: flex; align-items: center; gap: 10px; letter-spacing: 0.5px;">
        <span style="font-size: 18px;">{icon}</span> {title}
    </div>
    <div style="color: #e8e0d0; white-space: pre-wrap; word-wrap: break-word; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
{llm_response.strip()}
    </div>
</div>"""
    return html


def parse_llm_insights(response_text):
    """Parse LLM response into structured insights."""
    import re as regex
    
    insights = []
    # Try to extract numbered points like "1. **Title** Description"
    pattern = r'(\d+)\.\s*\*\*([^*]+)\*\*:?\s*(.+?)(?=\n\d+\.|$)'
    matches = regex.findall(pattern, response_text, regex.DOTALL)
    
    if matches:
        for num, title, content in matches:
            insights.append({
                'number': num,
                'title': title.strip(),
                'content': content.strip().replace('\n', ' ')
            })
    
    return insights


def format_comparison_html_detailed(response_text, query_type="CUTOFF"):
    """Format LLM response as styled HTML cards - flexible formatting for natural paragraph text."""

    print(f"[FORMAT_HTML] Received response: type={type(response_text)}, len={len(str(response_text)) if response_text else 0}")
    
    icon = "📊" if query_type == "CUTOFF" else "🎓"
    title = "Cutoff Comparison Analysis" if query_type == "CUTOFF" else "College Options Analysis"
    
    # Handle null/empty response
    if not response_text:
        print(f"[FORMAT_HTML] NULL response detected, returning empty state")
        return f"""<div style="background: rgba(201, 168, 76, 0.06); border: 2px solid rgba(201, 168, 76, 0.3); border-radius: 12px; padding: 24px; margin: 12px 0; font-family: 'Poppins', sans-serif;">
    <div style="color: #ffd700; font-weight: 700; font-size: 16px; margin-bottom: 20px; display: flex; align-items: center; gap: 10px; letter-spacing: 0.5px;">
        <span style="font-size: 20px;">{icon}</span> {title}
    </div>
    <div style="color: #e8e0d0; font-size: 13px; padding: 16px; background: rgba(201, 168,76, 0.04); border-radius: 8px;">
        Analysis in progress. Please try again.
    </div>
</div>"""
    
    response_str = str(response_text).strip()
    if not response_str:
        print(f"[FORMAT_HTML] Empty string response detected")
        return f"""<div style="background: rgba(201, 168, 76, 0.06); border: 2px solid rgba(201, 168, 76, 0.3); border-radius: 12px; padding: 24px; margin: 12px 0; font-family: 'Poppins', sans-serif;">
    <div style="color: #ffd700; font-weight: 700; font-size: 16px; margin-bottom: 20px; display: flex; align-items: center; gap: 10px; letter-spacing: 0.5px;">
        <span style="font-size: 20px;">{icon}</span> {title}
    </div>
    <div style="color: #e8e0d0; font-size: 13px; padding: 16px; background: rgba(201, 168, 76, 0.04); border-radius: 8px;">
        No comparison data available.
    </div>
</div>"""
    
    # Split response into paragraphs (double newline or natural breaks)
    paragraphs = response_str.split('\n\n')
    if len(paragraphs) <= 1:
        # No paragraph breaks from LLM: treat each non-empty line as a display chunk.
        paragraphs = [line.strip() for line in response_str.split('\n') if line.strip()]
    
    print(f"[FORMAT_HTML] Parsed {len(paragraphs)} paragraphs")
    
    html_output = f"""<div style="background: rgba(201, 168, 76, 0.06); border: 2px solid rgba(201, 168, 76, 0.3); border-radius: 12px; padding: 24px; margin: 12px 0; font-family: 'Poppins', sans-serif;">
    <div style="color: #ffd700; font-weight: 700; font-size: 16px; margin-bottom: 20px; display: flex; align-items: center; gap: 10px; letter-spacing: 0.5px;">
        <span style="font-size: 20px;">{icon}</span> {title}
    </div>
"""
    cards_added = 0

    for i, para in enumerate(paragraphs):
        para = para.strip()
        if not para or para.startswith('['):
            continue
        
        # Clean up markdown formatting
        clean_para = para.replace('**', '').replace('- ', '').replace('• ', '')
        
        # Check if paragraph has a section label (text before colon)
        section_title = None
        if ':' in clean_para:
            first_part = clean_para.split(':')[0].strip()
            # If first part is short and looks like a label, use it
            if len(first_part) < 60 and not first_part.endswith('.') and len(first_part.split()) < 8:
                section_title = first_part
                content = ':'.join(clean_para.split(':')[1:]).strip()
            else:
                content = clean_para
        else:
            content = clean_para
        
        print(f"[FORMAT_HTML] Paragraph {i+1}: title={section_title}, content_len={len(content)}")
        
        # Build card with section if applicable
        if section_title:
            html_output += f"""    <div style="background: rgba(201, 168, 76, 0.04); border-left: 4px solid #c9a84c; padding: 16px 16px; margin-bottom: 14px; border-radius: 8px;">
        <div style="color: #d4af37; font-weight: 700; font-size: 13px; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 10px;">
            {html.escape(section_title)}
        </div>
        <div style="color: #e8e0d0; font-size: 13px; line-height: 1.8;">
            {html.escape(content)}
        </div>
    </div>
"""
            cards_added += 1
        else:
            html_output += f"""    <div style="background: rgba(201, 168, 76, 0.04); border-left: 4px solid #c9a84c; padding: 16px 16px; margin-bottom: 14px; border-radius: 8px; color: #e8e0d0; font-size: 13px; line-height: 1.8;">
        {html.escape(content)}
    </div>
"""
            cards_added += 1

    if cards_added == 0:
        html_output += f"""    <div style="background: rgba(201, 168, 76, 0.04); border-left: 4px solid #c9a84c; padding: 16px 16px; margin-bottom: 14px; border-radius: 8px; color: #e8e0d0; font-size: 13px; line-height: 1.8;">
        {html.escape(response_str)}
    </div>
"""
    
    html_output += """</div>"""
    print(f"[FORMAT_HTML] Generated HTML length: {len(html_output)}")
    return html_output


def format_comparison_response(queries, query_type_label):
    """Format comparison data with ACTUAL RESULTS displayed side-by-side"""
    if not queries:
        return ["No queries to compare"]
    
    response = []
    response.append("=" * 90)
    response.append(f"{query_type_label} QUERY COMPARISON SUMMARY ({len(queries)} queries)")
    response.append("=" * 90)
    
    for i, q in enumerate(queries, 1):
        response.append(f"\n{'─' * 90}")
        response.append(f"QUERY {i}: {q.get('original_question', 'N/A')}")
        response.append(f"District: {q['district'].title()} | Course: {q['course']}", )
        if q.get('category') and q['category'] != 'none':
            response.append(f"Category: {q['category'].upper()} | Year: {q['year']}")
        response.append(f"{'─' * 90}")
        
        # Display actual results
        results = q.get('results', [])
        if results:
            if isinstance(results, list) and len(results) > 0:
                for result in results:
                    if isinstance(result, str):
                        response.append(f"  {result}")
                    else:
                        response.append(f"  {str(result)}")
            else:
                response.append(f"  No results")
        else:
            response.append(f"  No results")
        
        response.append(f"  (Total: {q.get('college_count', 0)} colleges)")
    
    response.append("\n" + "=" * 90)
    response.append("KEY INSIGHTS:")
    if query_type_label == "CUTOFF":
        response.append("  • Compare cutoff scores across districts/categories")
        response.append("  • Identify which district has higher/lower cutoff difficulty")
        response.append("  • Spot patterns in selection preferences")
    else:
        response.append("  • Compare college availability by district")
        response.append("  • Identify course offering patterns")
        response.append("  • Find best options by location and college count")
    response.append("=" * 90)
    
    return response


def compare_cutoff_queries(user_question, session_id=None):
    """Compare ONLY cutoff queries with type safety and smart detection."""
    print(f"[COMPARE] Comparing CUTOFF queries for: {user_question}")
    
    # Detect if user specified how many queries to compare (e.g., "compare last 2")
    limit = 2  # Default: compare last 2 queries only
    if "last" in user_question.lower():
        # Try to extract number: "compare last 3" → 3
        import re as regex
        match = regex.search(r'last\s+(\d+)', user_question.lower())
        if match:
            limit = int(match.group(1))
            print(f"[COMPARE] User specified: compare last {limit}")
    
    history = retrieve_comparable_queries(limit=limit, query_type="cutoff", session_id=session_id)
    
    if not history:
        return ["No CUTOFF queries found in history to compare."]
    
    print(f"[COMPARE] Found {len(history)} recent cutoff queries to compare")
    
    # If we have at least 2 queries, get comparison from LLM
    if len(history) >= 2:
        # Format data for LLM analysis
        comparison_text = format_comparison_for_llm(history, "CUTOFF")
        
        # Create simple, open-ended comparison prompt (no template)
        llm_prompt = f"""Compare these college cutoff queries and provide practical insights for a student. Be concise.

{comparison_text}

Provide a brief comparison covering:
- Which district has better options and why
- What cutoff scores to aim for
- Which choices are safest/risky
- Key differences between districts  
- Your recommendation

Use a natural response style and focus on practical advice."""
        
        # Send to LLM for analysis
        if call_llm:
            print(f"[COMPARE] Sending to LLM for student-focused analysis (last {len(history)} queries)")
            llm_response = call_llm(llm_prompt, history=[])
            print(f"[COMPARE] LLM Response type: {type(llm_response)}, Length: {len(str(llm_response)) if llm_response else 0}")
            
            # Validate LLM response
            if llm_response and isinstance(llm_response, str) and llm_response.strip():
                print(f"[COMPARE] LLM response valid, formatting HTML")
                # Format as HTML for nice UI display
                html_response = format_comparison_html_detailed(llm_response, query_type="CUTOFF")
                return [html_response]
            else:
                print(f"[COMPARE] LLM response empty/null, using fallback formatting")
                # Fallback to text-based comparison
                return format_comparison_response(history, "CUTOFF")
        else:
            # Fallback if LLM unavailable
            print(f"[COMPARE] LLM not available, using fallback formatting")
            return format_comparison_response(history, "CUTOFF")
    else:
        return [
            f"Need at least 2 CUTOFF queries to compare. You have only {len(history)}.",
            f"Try: 'cutoff cse oc salem' then 'compare' (will compare last 2)",
            "Or: 'compare last 3' to compare last 3 queries"
        ]


def compare_college_queries(user_question, session_id=None):
    """Compare ONLY college list queries with type safety."""
    print(f"[COMPARE] Comparing COLLEGE queries for: {user_question}")
    
    # Detect if user specified how many queries to compare
    limit = 2  # Default: compare last 2 queries only
    if "last" in user_question.lower():
        import re as regex
        match = regex.search(r'last\s+(\d+)', user_question.lower())
        if match:
            limit = int(match.group(1))
            print(f"[COMPARE] User specified: compare last {limit}")
    
    history = retrieve_comparable_queries(limit=limit, query_type="college", session_id=session_id)
    
    if not history:
        return ["No COLLEGE queries found in history to compare."]
    
    print(f"[COMPARE] Found {len(history)} recent college queries to compare")
    
    # If we have at least 2 queries, get comparison from LLM
    if len(history) >= 2:
        # Format data for LLM analysis
        comparison_text = format_comparison_for_llm(history, "COLLEGE")
        
        # Create simple, open-ended comparison prompt (no template)
        llm_prompt = f"""Compare these college availability queries and provide practical insights for a student. Be concise.

{comparison_text}

Provide a brief comparison covering:
- Which district has more college options
- Variety and differences between districts
- Which district to consider as backup
- Key insights for student decision-making
- Your recommendation

Keep each point to 1-2 sentences. Focus on practical advice."""
        
        # Send to LLM for analysis
        if call_llm:
            print(f"[COMPARE] Sending to LLM for student-focused analysis (last {len(history)} queries)")
            llm_response = call_llm(llm_prompt, history=[])
            print(f"[COMPARE] LLM Response type: {type(llm_response)}, Length: {len(str(llm_response)) if llm_response else 0}")
            
            # Validate LLM response
            if llm_response and isinstance(llm_response, str) and llm_response.strip():
                print(f"[COMPARE] LLM response valid, formatting HTML")
                # Format as HTML for nice UI display
                html_response = format_comparison_html_detailed(llm_response, query_type="COLLEGE")
                return [html_response]
            else:
                print(f"[COMPARE] LLM response empty/null, using fallback formatting")
                # Fallback to text-based comparison
                return format_comparison_response(history, "COLLEGE")
        else:
            print(f"[COMPARE] LLM not available, using fallback formatting")
            return format_comparison_response(history, "COLLEGE")
    else:
        return [
            f"Need at least 2 COLLEGE queries to compare. You have only {len(history)}.",
            f"Try: 'colleges in salem offering ece' then 'compare'",
            "Or: 'compare last 3' to compare last 3 queries"
        ]


def show_query_history():
    """Show all queries in history with their types."""
    history = retrieve_comparable_queries(limit=20, query_type="any")
    
    if not history:
        return ["No query history found."]
    
    response = ["Your Query History (Last 20):"]
    response.append("=" * 70)
    
    for i, q in enumerate(history, 1):
        query_type_short = "CUTOFF" if q["query_type"] == "CUTOFF_QUERY" else "COLLEGE"
        response.append(f"{i}. [{query_type_short}] {q['original_query'][:55]}...")
    
    response.append("=" * 70)
    return response

# =====================================================
# IN-MEMORY QUERY STATE (Temporary storage for merging)
# ====================================================="
_query_context = {
    "original_query": None,
    "awaiting_input": None,  # "category" or "district"
}

def reset_query_context():
    """Reset the query context after processing."""
    global _query_context
    _query_context = {
        "original_query": None,
        "awaiting_input": None,
    }

# =====================================================
# MAIN ENTRY
# =====================================================
def handle_query(user_question: str, session_id=None):
    global _query_context
    
    # STEP 0: PREPROCESSING (Happens FIRST before any keyword extraction)
    preprocessed = correct_typos_and_preprocess(user_question)
    q = normalize_query(preprocessed)  # Replace abbreviations
    
    print(f"\n[HANDLE_QUERY] Original: '{user_question}'")
    print(f"[HANDLE_QUERY] Preprocessed: '{preprocessed}'")
    print(f"[HANDLE_QUERY] Normalized: '{q}'")
    
    # STEP 0: Check for comparison/analysis requests WITH TYPE SAFETY
    keywords_analysis = ["compare", "difference", "similar colleges", "vs ", "versus"]
    print(f"[HANDLE_QUERY] Checking keywords: {keywords_analysis}")
    print(f"[HANDLE_QUERY] Any match? {any(kw in q for kw in keywords_analysis)}")
    
    if any(kw in q for kw in keywords_analysis):
        print(f"[HANDLE_QUERY] *** COMPARISON DETECTED ***")
        # Detect comparison type - check recent queries
        recent = retrieve_comparable_queries(limit=1, query_type="any", session_id=session_id)
        print(f"[HANDLE_QUERY] Recent queries: {len(recent)}")
        if recent:
            print(f"[HANDLE_QUERY] Most recent query type: {recent[0].get('query_type')}")
        
        # Explicit type hints in user question
        if any(kw in q for kw in ["cutoff", "score", "rank"]):
            print(f"[HANDLE_QUERY] Routing to compare_cutoff_queries (explicit keyword)")
            return compare_cutoff_queries(user_question, session_id=session_id)
        elif any(kw in q for kw in ["college", "institution", "offering"]):
            print(f"[HANDLE_QUERY] Routing to compare_college_queries (explicit keyword)")
            return compare_college_queries(user_question, session_id=session_id)
        # Smart detection: look at recent query type
        elif recent and recent[0].get("query_type") == "CUTOFF_QUERY":
            print(f"[HANDLE_QUERY] Routing to compare_cutoff_queries (recent query is cutoff)")
            return compare_cutoff_queries(user_question, session_id=session_id)
        elif recent and recent[0].get("query_type") == "COLLEGE_LIST_QUERY":
            print(f"[HANDLE_QUERY] Routing to compare_college_queries (recent query is college)")
            return compare_college_queries(user_question, session_id=session_id)
        else:
            # Default to cutoff if unsure
            print(f"[HANDLE_QUERY] Routing to compare_cutoff_queries (default)")
            return compare_cutoff_queries(user_question, session_id=session_id)
    
    print(f"[HANDLE_QUERY] No comparison keywords found, proceeding with normal query")
    
    # Check for history requests
    if "show history" in q or "past queries" in q:
        return show_query_history()
    
    # STEP 1: Normalize query (replace abbreviations)
    q = normalize_query(user_question)
    
    # STEP 2: Smart context check - only apply pending input if it looks like a follow-up
    # If user asks a NEW multi-keyword query (e.g., "colleges offering..."), reset context
    words_in_query = user_question.lower().split()
    
    # If awaiting category/district but the new query looks like a COMPLETE NEW QUERY (3+ words with specific keywords),
    # it's not a follow-up, so reset context
    if _query_context["awaiting_input"] and len(words_in_query) > 2:
        # Check if this is a follow-up (single word or 2 words like "salem cbe")
        # vs a new query (has keywords like college, cutoff, offering, etc.)
        new_query_keywords = set(words_in_query)
        has_major_keywords = any(kw in new_query_keywords for kw in ["college", "colleges", "cutoff", "offering", "available", "compare"])
        
        if has_major_keywords:
            # This is a new query, not a follow-up - reset context
            print(f"[DEBUG] Multi-keyword query detected while awaiting input - resetting context")
            reset_query_context()
    
    # STEP 3: Check if this is a response to a pending selection
    if _query_context["awaiting_input"] == "category":
        # User is providing category selection
        # Extract category from user response (handles "mbc cutoff..." not just "mbc")
        extracted_cat = extract_category(user_question)
        if extracted_cat:
            # Merge the extracted category into original query
            q = _query_context["original_query"] + " " + extracted_cat
            _query_context["original_query"] = None
            _query_context["awaiting_input"] = None
        else:
            return [f"Invalid category. Please select from: {', '.join(sorted(CATEGORIES))}"]
    
    elif _query_context["awaiting_input"] == "district":
        # User is providing district selection
        # Normalize first (handles abbreviations like "cbe")
        normalized_user = normalize_query(user_question)
        # Extract district from normalized response
        extracted_dist = extract_district(normalized_user)
        if extracted_dist:
            # Merge the extracted district into original query
            q = _query_context["original_query"] + " " + extracted_dist
            _query_context["original_query"] = None
            _query_context["awaiting_input"] = None
        else:
            return [f"Invalid district. Please select from: {', '.join(sorted(DISTRICTS))}"]
    
    # STEP 3: Route to appropriate handler using refined query type detection
    print(f"[HANDLE_QUERY] ====== QUERY ROUTING ======")
    
    # ---- TYPE 5: ELIGIBILITY QUERY (Highest Priority After Comparison) ----
    eligibility_result = detect_eligibility_query(q)
    if eligibility_result.get('match'):
        print(f"[HANDLE_QUERY] *** TYPE 5: ELIGIBILITY QUERY DETECTED ***")
        cutoff_mark = eligibility_result['cutoff_mark']
        course = eligibility_result['course']
        category = eligibility_result['category']
        district = eligibility_result['district']
        
        result = check_eligibility(cutoff_mark, course, category, district)
        log_query_to_db(
            user_question,
            {
                "district": district or "any",
                "course": course,
                "category": category,
                "year": 2024
            },
            result,
            "cutoff",
            session_id=session_id
        )
        reset_query_context()
        return result
    
    # ---- TYPE 3: CUTOFF QUERY (Smart keyword combination matching) ----
    if is_cutoff_query(q):
        print(f"[HANDLE_QUERY] *** TYPE 3: CUTOFF QUERY DETECTED ***")
        # Check keyword combination
        keywords = count_cutoff_keywords(q)
        
        # If ALL 4 keywords present, fetch directly
        if keywords['count'] == 4:
            result = fetch_cutoff(keywords['district'], keywords['course'], keywords['category'], keywords['year'] or 2024)
            log_query_to_db(
                user_question,
                {
                    "district": keywords['district'],
                    "course": keywords['course'],
                    "category": keywords['category'],
                    "year": keywords['year'] or 2024
                },
                result,
                "cutoff",
                session_id=session_id
            )
            reset_query_context()
            if result and result[0] != "No cutoff data found.":
                return result
            return ["No cutoff data found for your query."]
        
        # If 3 keywords present, ask for the missing one
        elif keywords['count'] == 3:
            missing_keyword = keywords['missing'][0]
            
            if missing_keyword == "cutoff":
                return ["Did you mean to ask for cutoff marks? Please include 'cutoff' in your query."]
            
            elif missing_keyword == "category":
                _query_context["original_query"] = q
                _query_context["awaiting_input"] = "category"
                categories_list = ", ".join(sorted(CATEGORIES))
                return [
                    f"📋 **Missing Category** - This system requires category for accurate results.",
                    f"",
                    f"Available categories: {categories_list}",
                    f"",
                    f"✅ **Example**: 'cutoff for {keywords['course']} in {keywords['district']} for <category>'",
                    f"",
                    f"Respond with one of: bc, oc, mbc, bcm, sc, sca, st"
                ]
            
            elif missing_keyword == "district":
                _query_context["original_query"] = q
                _query_context["awaiting_input"] = "district"
                return [
                    f"📍 **Missing District** - Please specify which district.",
                    f"",
                    f"Available districts: {', '.join(sorted(DISTRICTS))}",
                    f"",
                    f"✅ **Example**: 'cutoff for {keywords['course']} in <district> {keywords['category']}'",
                    f"",
                    f"You can use abbreviations like 'cbe' for Coimbatore or full names."
                ]
            
            elif missing_keyword == "course":
                return [
                    f"🎓 **Missing Course** - Please specify the engineering course.",
                    f"",
                    f"❓ What course are you interested in?",
                    f"",
                    f"Available courses: CSE, Mechanical, Civil, ECE, EEE, etc."
                ]
        
        # If less than 3 keywords, show system design note + example
        else:
            return [
                f"ℹ️  **System Design Note**:",
                f"",
                f"This system is specifically designed for **TNEA** cutoff queries.",
                f"",
                f"✅ **Best Results Require 4 Keywords:**",
                f"   • Cutoff keyword (required)",
                f"   • District name (required)",
                f"   • Course name (required)",
                f"   • Category like BC/OC/MBC (required)",
                f"",
                f"📌 **Example Query to Try:**",
                f"   'What is the cutoff for CSE in Coimbatore for MBC category?'",
                f"",
                f"Or simply: 'cutoff for cse in cbe mbc'",
                f"",
                f"This helps us fetch accurate results for your specific requirements! 🎓"
            ]
    
    # ---- TYPE 2: COLLEGE COURSE QUERY ----
    college_course_result = detect_college_course_query(q)
    if college_course_result.get('match'):
        print(f"[HANDLE_QUERY] *** TYPE 2: COLLEGE COURSE QUERY DETECTED ***")
        district = college_course_result['district']
        course = college_course_result['course']
        
        result = fetch_colleges_by_district(district, course)
        log_query_to_db(
            user_question,
            {"district": district, "course": course, "category": None, "year": 2024},
            result,
            "college",
            session_id=session_id
        )
        reset_query_context()
        if result and result[0] != "No colleges found.":
            note = f"🎓 Here are colleges offering {course.title()} in {district.title()}:"
            return [note] + result
        return result
    
    # ---- TYPE 1: COLLEGE DISTRICT ONLY QUERY ----
    college_district_result = detect_college_district_only(q)
    if college_district_result.get('match'):
        print(f"[HANDLE_QUERY] *** TYPE 1: COLLEGE DISTRICT ONLY QUERY DETECTED ***")
        district = college_district_result['district']
        
        result = fetch_colleges_by_district(district)
        log_query_to_db(
            user_question,
            {"district": district, "course": None, "category": None, "year": 2024},
            result,
            "college",
            session_id=session_id
        )
        reset_query_context()
        if result and result[0] != "No colleges found.":
            note = f"🎓 Here are colleges in {district.title()}:"
            return [note] + result
        return result
    
    # ---- FALLBACK: Check if only a number (Type 6 - Invalid Input) ----
    if q.strip().isdigit() or (len(q.strip().split()) == 1 and q.strip().replace('.', '').isdigit()):
        print(f"[HANDLE_QUERY] *** TYPE 6: INVALID INPUT (Number Only) ***")
        return [
            "❌ Invalid input - Please provide a meaningful query.",
            "",
            "Examples of valid queries:",
            "  • 'colleges in madurai'",
            "  • 'colleges in coimbatore offering cse'",
            "  • 'cutoff for cse in cbe for mbc category'",
            "  • 'i scored 185 can i get cse in mbc coimbatore'"
        ]
    
    # ---- FALLBACK: Definition Question or other LLM-suitable input (Type 6) ----
    if is_definition_question(q):
        print(f"[HANDLE_QUERY] *** TYPE 6: DEFINITION/EXPLANATION QUESTION ***")
        if call_llm:
            llm_response = call_llm(user_question, history=[])
            reset_query_context()
            return [llm_response] if llm_response else ["I couldn't process your question. Please try rephrasing it."]
        return ["Please ask about college/cutoff specific data."]
    
    # ---- FALLBACK: General LLM for other inputs (Type 6) ----
    print(f"[HANDLE_QUERY] *** TYPE 6: FALLBACK TO LLM ***")
    if call_llm:
        try:
            llm_response = call_llm(user_question, history=[])
            reset_query_context()
            return [llm_response] if llm_response else ["Unable to process. Please try another query."]
        except Exception as e:
            print(f"[HANDLE_QUERY] LLM error: {e}")
            return ["Error processing query. Please try again."]
    
    reset_query_context()
    return ["This system answers college and cutoff related queries. Please try a specific question."]
