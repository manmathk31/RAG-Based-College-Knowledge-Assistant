"""Curated official college knowledge base for MIT Academy of Engineering (MITAOE).

Serves as the authoritative knowledge repository for campus policies, regulations,
and provides seamless retrieval fallback when external vector services are unconfigured.
"""

from typing import List, Dict, Any
from app.retrieval.models import RetrievalCandidate

OFFICIAL_COLLEGE_DOCUMENTS: List[Dict[str, Any]] = [
    {
        "id": "doc-academic-regulations",
        "title": "MITAOE Academic Regulations & Attendance Policy",
        "category": "Academics",
        "version": "2025.1",
        "pages": 18,
        "description": "Rules governing attendance requirements, condonation on medical grounds, credit requirements, and academic probation.",
        "sampleQuestions": [
            "What is the minimum attendance requirement?",
            "What happens if my attendance falls below 75%?",
            "What is the procedure for medical leave condonation?",
            "What are the criteria for academic honors and distinction?"
        ]
    },
    {
        "id": "doc-exam-evaluation",
        "title": "MITAOE Examination & Evaluation Manual",
        "category": "Examinations",
        "version": "2025.1",
        "pages": 24,
        "description": "Assessment structure, mid-sem and end-sem weightage, grading scheme, backlog rules (ATKT), and revaluation process.",
        "sampleQuestions": [
            "Explain the exam revaluation process",
            "What is the grading scale and how is CGPA calculated?",
            "How many backlogs are allowed for ATKT progression?",
            "What are the rules regarding missed mid-semester exams?"
        ]
    },
    {
        "id": "doc-scholarships",
        "title": "MITAOE Scholarship & Financial Aid Handbook",
        "category": "Financial Aid",
        "version": "2025.1",
        "pages": 12,
        "description": "State and central government scholarships (MahaDBT, EBC, TFWS, SC/ST/OBC), institute merit awards, and application timelines.",
        "sampleQuestions": [
            "Where can I find scholarship information?",
            "What is the eligibility for EBC and TFWS fee concessions?",
            "What documents are required for MahaDBT scholarship renewal?",
            "Are there merit-based scholarships for top rankers?"
        ]
    },
    {
        "id": "doc-hostel-campus",
        "title": "MITAOE Campus Facilities & Hostel Handbook",
        "category": "Campus Life",
        "version": "2025.1",
        "pages": 16,
        "description": "On-campus boys and girls hostel facilities, mess timings, library hours, sports complex, health center, and Wi-Fi access guidelines.",
        "sampleQuestions": [
            "What hostel facilities are available?",
            "What are the hostel mess timings and menu rules?",
            "What are the library hours and digital book lending limits?",
            "Is on-campus medical and ambulance assistance available 24/7?"
        ]
    },
    {
        "id": "doc-admissions-fees",
        "title": "MITAOE Admissions & Fee Structure Guide",
        "category": "Admissions",
        "version": "2025.1",
        "pages": 20,
        "description": "Undergraduate B.Tech eligibility, MHT-CET and JEE Main cutoffs, fee breakdown, installment plans, and cancellation refund policy.",
        "sampleQuestions": [
            "What is the fee structure for B.Tech programmes?",
            "What is the refund policy if I cancel my admission?",
            "Can tuition fees be paid in installments?",
            "What are the eligibility criteria for lateral entry direct second year (DSE)?"
        ]
    },
    {
        "id": "doc-placements-internships",
        "title": "MITAOE Training & Placement Cell Guidelines",
        "category": "Placements",
        "version": "2025.1",
        "pages": 14,
        "description": "Placement eligibility criteria, dream company offers, internship credits, campus drive protocols, and career development support.",
        "sampleQuestions": [
            "What is the minimum CGPA required to sit for campus placements?",
            "What are the placement statistics and top recruiting companies?",
            "Can I accept a second offer if I receive a dream company package?",
            "How do semester internships count towards degree credits?"
        ]
    }
]

DEFAULT_KNOWLEDGE_CHUNKS: List[Dict[str, Any]] = [
    # --- Academic Regulations ---
    {
        "chunk_id": "acad-1",
        "document_id": "doc-academic-regulations",
        "document_name": "MITAOE Academic Regulations 2025.pdf",
        "document_version": 1,
        "page_number": 4,
        "section": "Attendance Requirements & Minimum Criteria",
        "content": (
            "Every registered student must maintain a minimum attendance of 75% in each theory course, laboratory, "
            "and tutorial session to be granted term grant and be eligible to appear for the End-Semester Examination (ESE). "
            "Students whose cumulative attendance falls between 60% and 74% may apply for condonation on genuine medical "
            "grounds or sanctioned official college representation (sports/cultural/competitions), subject to approval by the "
            "Head of the Department and the Dean of Academics. Students with attendance strictly below 60% are not eligible for "
            "condonation under any circumstances and shall be awarded an 'I' (Incomplete) grade, requiring them to re-register for the course."
        ),
        "keywords": ["attendance", "minimum", "75%", "condonation", "medical", "term grant", "eligibility", "exam", "grade", "incomplete"]
    },
    {
        "chunk_id": "acad-2",
        "document_id": "doc-academic-regulations",
        "document_name": "MITAOE Academic Regulations 2025.pdf",
        "document_version": 1,
        "page_number": 6,
        "section": "Medical Leave Condonation Procedure",
        "content": (
            "To apply for medical attendance condonation: The student must notify their Faculty Advisor and Head of Department "
            "within 3 working days of the onset of illness. Upon returning to campus, the original medical certificate from a registered "
            "medical practitioner, along with prescription slips and diagnostic reports, must be submitted to the Student Section "
            "within 5 working days. A maximum condonation of up to 15% attendance (allowing eligibility at 60% minimum) may be approved."
        ),
        "keywords": ["medical", "leave", "condonation", "certificate", "procedure", "illness", "doctor", "hospital", "prescription"]
    },
    {
        "chunk_id": "acad-3",
        "document_id": "doc-academic-regulations",
        "document_name": "MITAOE Academic Regulations 2025.pdf",
        "document_version": 1,
        "page_number": 9,
        "section": "Academic Honors and Credit Structure",
        "content": (
            "Under the autonomous curriculum, a minimum of 160 credits is required for the award of the B.Tech degree. "
            "Students maintaining a CGPA of 8.50 or higher without any active or cleared backlog are eligible to register for an "
            "Honors or Minor specialization in emerging areas (such as AI/ML, Cyber Security, Data Science, or Robotics) "
            "by earning an additional 18 to 20 credits across semesters 5 to 8."
        ),
        "keywords": ["credits", "honors", "minor", "degree", "cgpa", "distinction", "specialization", "btech"]
    },

    # --- Examination & Evaluation ---
    {
        "chunk_id": "exam-1",
        "document_id": "doc-exam-evaluation",
        "document_name": "MITAOE Examination & Evaluation Manual.pdf",
        "document_version": 1,
        "page_number": 12,
        "section": "Evaluation Scheme & Exam Revaluation Process",
        "content": (
            "The evaluation system comprises Continuous In-Semester Evaluation (ISE - 40% weightage) and End-Semester Examination "
            "(ESE - 60% weightage). After results are declared, students dissatisfied with their ESE evaluation can apply for "
            "Answer Sheet Photocopy within 5 days of result declaration by paying a fee of Rs. 300 per course. After receiving the "
            "photocopy, if a grievance persists, students may formally apply for Revaluation within 3 days with a revaluation fee of "
            "Rs. 500 per course. The revaluation is performed by an external senior examiner; if the revised score differs by more than "
            "5%, the revised grade is officially recorded."
        ),
        "keywords": ["revaluation", "exam", "photocopy", "evaluation", "grades", "marks", "result", "appeal", "challenge", "fee"]
    },
    {
        "chunk_id": "exam-2",
        "document_id": "doc-exam-evaluation",
        "document_name": "MITAOE Examination & Evaluation Manual.pdf",
        "document_version": 1,
        "page_number": 15,
        "section": "Grading Scale & SGPA/CGPA Calculation",
        "content": (
            "MITAOE follows a 10-point absolute grading scale: O (Outstanding, 10 points, >=90%), A+ (Excellent, 9 points, 80-89%), "
            "A (Very Good, 8 points, 70-79%), B+ (Good, 7 points, 60-69%), B (Above Average, 6 points, 50-59%), C (Pass, 5 points, 40-49%), "
            "and F (Fail, 0 points, <40%). The Semester Grade Point Average (SGPA) is computed as sum(Course Credits * Grade Points) / sum(Credits). "
            "Cumulative Grade Point Average (CGPA) reflects cumulative performance across all completed semesters."
        ),
        "keywords": ["grading", "scale", "gpa", "cgpa", "sgpa", "passing marks", "points", "marks", "percentage"]
    },
    {
        "chunk_id": "exam-3",
        "document_id": "doc-exam-evaluation",
        "document_name": "MITAOE Examination & Evaluation Manual.pdf",
        "document_version": 1,
        "page_number": 18,
        "section": "ATKT (Allowed to Keep Term) & Backlog Progression Rules",
        "content": (
            "To progress to the next academic year under ATKT regulations: A student can carry a maximum of 4 active backlog courses "
            "from the preceding year to register for the next academic year. To enter the 3rd year (Semester 5), all First Year (Sem 1 & 2) "
            "courses must be completely cleared (Zero First Year Backlogs). Similarly, to enter the 4th year (Semester 7), all Second Year "
            "courses must be cleared."
        ),
        "keywords": ["atkt", "backlog", "progression", "failed", "re-exam", "arrears", "allowed to keep term", "year down"]
    },

    # --- Scholarships & Financial Aid ---
    {
        "chunk_id": "schol-1",
        "document_id": "doc-scholarships",
        "document_name": "MITAOE Scholarship & Financial Aid Handbook.pdf",
        "document_version": 1,
        "page_number": 3,
        "section": "Government Scholarships & MahaDBT Portal",
        "content": (
            "MITAOE facilitates all official Maharashtra State Government scholarship schemes through the MahaDBT portal (mahadbt.maharashtra.gov.in). "
            "Eligible categories include: Rajarshi Chhatrapati Shahu Maharaj Shikshan Shulkh Shishyavrutti Yojna (EBC) providing a 50% tuition fee waiver "
            "for open/general category students with annual family income up to Rs. 8 Lakhs; Social Welfare schemes offering up to 100% tuition and exam fee "
            "waivers for SC/ST students, and 50% fee waivers for OBC/VJNT/SBC students. Students must apply online and submit verified hard copies to the "
            "Scholarship Section before the state deadline (usually October-November each academic year)."
        ),
        "keywords": ["scholarship", "mahadbt", "ebc", "fee concession", "waiver", "social welfare", "caste", "income limit", "financial aid"]
    },
    {
        "chunk_id": "schol-2",
        "document_id": "doc-scholarships",
        "document_name": "MITAOE Scholarship & Financial Aid Handbook.pdf",
        "document_version": 1,
        "page_number": 7,
        "section": "Institute Merit Scholarships & TFWS Scheme",
        "content": (
            "Tuition Fee Waiver Scheme (TFWS): 5% supernumerary seats in each branch are allotted via CAP rounds with 100% tuition fee waiver for students "
            "with parental annual income below Rs. 8 Lakhs. Additionally, MITAOE awards Institute Merit Scholarships to top 3 academic rankers in each department "
            "at the end of each academic year: 1st Rank: Rs. 25,000, 2nd Rank: Rs. 15,000, and 3rd Rank: Rs. 10,000, provided the student has a minimum CGPA of 9.0 "
            "with no disciplinary infractions."
        ),
        "keywords": ["tfws", "merit scholarship", "ranker", "cash award", "tuition fee waiver", "topper", "financial assistance"]
    },

    # --- Campus & Hostel Facilities ---
    {
        "chunk_id": "hostel-1",
        "document_id": "doc-hostel-campus",
        "document_name": "MITAOE Campus & Hostel Facilities.pdf",
        "document_version": 1,
        "page_number": 5,
        "section": "Hostel Accommodation & Facilities",
        "content": (
            "MITAOE provides secure on-campus and affiliated hostel facilities for both boys and girls. Rooms are available in twin-sharing and "
            "triple-sharing configurations equipped with study tables, beds, wardrobes, and attached/common washrooms. Hostel amenities include: "
            "24/7 high-speed Wi-Fi, biometric entry security, CCTV surveillance, solar water heaters, water purifiers on every floor, common reading rooms, "
            "indoor sports recreational spaces (table tennis, carrom, chess), and weekly laundry services. Applications for hostel admission open immediately "
            "following the CAP round admissions on a first-come, first-served basis."
        ),
        "keywords": ["hostel", "accommodation", "room", "boys hostel", "girls hostel", "facilities", "wifi", "mess", "laundry", "living"]
    },
    {
        "chunk_id": "hostel-2",
        "document_id": "doc-hostel-campus",
        "document_name": "MITAOE Campus & Hostel Facilities.pdf",
        "document_version": 1,
        "page_number": 8,
        "section": "Hostel Mess Timings & Campus Dining",
        "content": (
            "The campus dining facility provides hygienic, nutritious vegetarian breakfast, lunch, evening snacks, and dinner. "
            "Mess Timings: Breakfast: 7:30 AM to 9:00 AM; Lunch: 12:15 PM to 2:00 PM; Evening Tea/Snacks: 5:00 PM to 6:00 PM; "
            "Dinner: 7:30 PM to 9:30 PM. The mess committee, consisting of student hostel representatives and faculty wardens, conducts monthly quality "
            "audits and inspects kitchen hygiene standards regularly."
        ),
        "keywords": ["mess", "food", "dining", "timings", "canteen", "meals", "breakfast", "lunch", "dinner", "vegetarian"]
    },
    {
        "chunk_id": "hostel-3",
        "document_id": "doc-hostel-campus",
        "document_name": "MITAOE Campus & Hostel Facilities.pdf",
        "document_version": 1,
        "page_number": 11,
        "section": "Central Library & Digital Knowledge Center",
        "content": (
            "The Central Library houses over 45,000 print volumes, 12,000 reference titles, and provides electronic subscriptions to IEEE Xplore, "
            "ScienceDirect, Springer, and ACM digital libraries. Library Timings: 8:00 AM to 8:00 PM on working days, with reading halls open until "
            "11:00 PM during examination periods. Under the Book Bank scheme, students can borrow a complete set of textbooks for the entire semester. "
            "A dedicated Digital Library zone with 60 high-performance workstations is open for research and project work."
        ),
        "keywords": ["library", "books", "reading hall", "timings", "digital library", "ieee", "book bank", "study room", "journals"]
    },
    {
        "chunk_id": "hostel-4",
        "document_id": "doc-hostel-campus",
        "document_name": "MITAOE Campus & Hostel Facilities.pdf",
        "document_version": 1,
        "page_number": 14,
        "section": "Health Care, Sports & Campus Security",
        "content": (
            "MITAOE provides an on-campus Medical Health Center staffed with a qualified medical officer and nursing assistant from 9:00 AM to 6:00 PM, "
            "with 24/7 on-call emergency ambulance availability tied to nearby multi-specialty hospitals in Alandi and Pune. Campus amenities include a "
            "floodlit basketball court, volleyball ground, cricket nets, football ground, well-equipped gymnasium, and 24/7 security with 100+ CCTV surveillance points."
        ),
        "keywords": ["medical", "health", "doctor", "ambulance", "emergency", "sports", "gym", "gymnasium", "security", "campus"]
    },

    # --- Admissions & Fees ---
    {
        "chunk_id": "adm-1",
        "document_id": "doc-admissions-fees",
        "document_name": "MITAOE Admissions & Fee Structure 2025.pdf",
        "document_version": 1,
        "page_number": 3,
        "section": "B.Tech Eligibility & CAP Round Procedures",
        "content": (
            "Admissions to First Year B.Tech programmes are conducted through the Centralized Admission Process (CAP) governed by the State CET Cell, "
            "Government of Maharashtra. Eligibility: Candidate must have passed 10+2 with Physics and Mathematics as compulsory subjects along with Chemistry/Biotech/Biology/Technical Vocational subject, "
            "securing at least 45% marks (40% for backward class categories). Candidates must possess a non-zero positive score in MHT-CET 2025 or JEE Main Paper 1. "
            "Institutional quota seats and vacant seats post-CAP rounds are filled strictly on merit as per state regulatory guidelines."
        ),
        "keywords": ["admission", "eligibility", "mhtcet", "jee", "cap", "criteria", "cut off", "first year", "btech", "apply"]
    },
    {
        "chunk_id": "adm-2",
        "document_id": "doc-admissions-fees",
        "document_name": "MITAOE Admissions & Fee Structure 2025.pdf",
        "document_version": 1,
        "page_number": 7,
        "section": "Fee Structure & Installment Facility",
        "content": (
            "Annual tuition and development fees are finalized each year by the Fee Regulating Authority (FRA), Maharashtra. "
            "For the current academic year, the interim annual fee structure is approximately Rs. 1,65,000 (Tuition Fee: Rs. 1,45,000; Development Fee: Rs. 20,000). "
            "Eligible reserved category students pay concessional fees as sanctioned by the government. The college provides an installment facility allowing fees "
            "to be remitted in two equal installments per semester upon submitting an undertaking to the Accounts Section."
        ),
        "keywords": ["fee", "tuition", "development fee", "cost", "installment", "payment", "expenses", "structure"]
    },

    # --- Placements & Internships ---
    {
        "chunk_id": "place-1",
        "document_id": "doc-placements-internships",
        "document_name": "MITAOE Training & Placement Policy.pdf",
        "document_version": 1,
        "page_number": 4,
        "section": "Placement Eligibility & Dream Company Policy",
        "content": (
            "Students with a minimum cumulative CGPA of 6.50 and no active backlogs are eligible to register for campus placement drives commencing from Semester 7. "
            "MITAOE operates a 'Dream Company' placement policy: A student who secures an initial offer in the standard category (up to Rs. 7 LPA) remains eligible "
            "to participate in Dream Company drives (offering Rs. 8 LPA to Rs. 15 LPA) and Super Dream drives (exceeding Rs. 15 LPA). Over 180 companies visit the campus "
            "annually, including IBM, TCS, Infosys, Cognizant, Veritas, Cisco, BMC Software, and ZS Associates, with highest packages reaching up to Rs. 24 LPA."
        ),
        "keywords": ["placement", "job", "companies", "highest package", "average package", "recruiters", "salary", "dream company", "cgpa"]
    }
]


def search_default_knowledge(query: str, limit: int = 5) -> List[RetrievalCandidate]:
    """Search the built-in college knowledge base using token overlap and keyword relevance."""
    if not query or not query.strip():
        return []

    query_tokens = set(query.lower().replace("?", "").replace(",", "").replace(".", "").split())
    # remove short noise words
    noise = {"is", "the", "what", "are", "how", "where", "can", "in", "for", "a", "an", "and", "to", "of", "do", "i"}
    meaningful = [t for t in query_tokens if t not in noise and len(t) > 2]
    if not meaningful:
        meaningful = list(query_tokens)

    scored_candidates = []
    for chunk in DEFAULT_KNOWLEDGE_CHUNKS:
        score = 0.0
        content_lower = chunk["content"].lower()
        section_lower = chunk["section"].lower()
        keywords = chunk.get("keywords", [])

        # Match meaningful tokens
        for token in meaningful:
            if token in section_lower:
                score += 3.0
            if any(token in kw for kw in keywords):
                score += 2.5
            if token in content_lower:
                score += 1.0

        # Exact phrase bonus
        if query.lower().strip() in content_lower or query.lower().strip() in section_lower:
            score += 5.0

        if score > 0:
            candidate = RetrievalCandidate(
                chunk_id=chunk["chunk_id"],
                document_id=chunk["document_id"],
                document_name=chunk["document_name"],
                document_version=chunk["document_version"],
                page_number=chunk["page_number"],
                section=chunk["section"],
                content=chunk["content"],
                score=score,
                retrieval_source="knowledge_base",
            )
            scored_candidates.append(candidate)

    scored_candidates.sort(key=lambda c: c.score, reverse=True)
    return scored_candidates[:limit]
