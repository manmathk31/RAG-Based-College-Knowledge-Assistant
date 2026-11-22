import React, { useState, useMemo } from "react";
import {
  Search,
  ChevronDown,
  Copy,
  Check,
  MessageSquare,
  BookOpen,
  Sparkles,
  X,
} from "lucide-react";

export interface FaqItem {
  id: string;
  category: "Academics" | "Examinations" | "Scholarships" | "Campus & Hostel" | "Admissions & Fees" | "Placements";
  question: string;
  summary: string;
  bullets: string[];
  documentName: string;
  pageNumber: number;
  articleRef?: string;
}

export const FAQS_DATA: FaqItem[] = [
  // --- Academics & Attendance ---
  {
    id: "acad-faq-1",
    category: "Academics",
    question: "What is the minimum attendance requirement to appear for exams?",
    summary: "Every registered student must maintain a minimum aggregate attendance of 75% in each theory course, laboratory, and tutorial session.",
    bullets: [
      "75% minimum attendance is mandatory for Term Grant and End-Semester Exam (ESE) eligibility.",
      "60% to 74%: Eligible for condonation on genuine medical grounds or official college representation (sports/cultural), subject to HOD & Dean approval.",
      "Strictly below 60%: No condonation under any circumstances. Awarded 'I' (Incomplete) grade requiring course re-registration.",
    ],
    documentName: "MITAOE Academic Regulations 2025.pdf",
    pageNumber: 4,
    articleRef: "Regulation 4.2",
  },
  {
    id: "acad-faq-2",
    category: "Academics",
    question: "What is the procedure for medical leave attendance condonation?",
    summary: "Formal medical condonation must be submitted through your Faculty Advisor and Student Section within strict deadlines.",
    bullets: [
      "Notify your Faculty Advisor and HOD within 3 working days of the onset of illness.",
      "Submit original medical certificate, prescription slips, and diagnostic reports to the Student Section within 5 working days of returning to campus.",
      "Maximum condonation allowed is up to 15% (permitting exam eligibility down to a 60% floor).",
    ],
    documentName: "MITAOE Academic Regulations 2025.pdf",
    pageNumber: 6,
    articleRef: "Regulation 4.5",
  },
  {
    id: "acad-faq-3",
    category: "Academics",
    question: "What are the criteria for B.Tech Honors or Minor specialization?",
    summary: "Eligible students can earn an Honors or Minor specialization in emerging tech domains like AI/ML, Cyber Security, Data Science, or Robotics.",
    bullets: [
      "Minimum cumulative CGPA of 8.50 without any active or cleared backlogs.",
      "Earn an additional 18 to 20 credits across Semesters 5 through 8.",
      "Total degree credits: 160 (Standard B.Tech) + 18-20 (Honors/Minor) = 178-180 credits.",
    ],
    documentName: "MITAOE Academic Regulations 2025.pdf",
    pageNumber: 9,
    articleRef: "Regulation 7.1",
  },

  // --- Examinations & ATKT ---
  {
    id: "exam-faq-1",
    category: "Examinations",
    question: "Explain the exam revaluation and photocopy process.",
    summary: "Students dissatisfied with their End-Semester Examination (ESE) evaluation can apply for Answer Sheet Photocopy and formal Revaluation.",
    bullets: [
      "Step 1 - Photocopy: Apply within 5 days of result declaration with a fee of Rs. 300 per course.",
      "Step 2 - Revaluation: After receiving the photocopy, submit grievance within 3 days with a revaluation fee of Rs. 500 per course.",
      "Evaluation is conducted by an independent external senior examiner; if the revised score differs by >5%, the updated grade is officially recorded.",
    ],
    documentName: "MITAOE Examination & Evaluation Manual.pdf",
    pageNumber: 12,
    articleRef: "Section 6.3",
  },
  {
    id: "exam-faq-2",
    category: "Examinations",
    question: "What is the 10-point grading scale and how is CGPA calculated?",
    summary: "MITAOE autonomous curriculum follows a standard 10-point absolute credit-based grading scale.",
    bullets: [
      "O: Outstanding (10 pts, >=90%) | A+: Excellent (9 pts, 80-89%) | A: Very Good (8 pts, 70-79%)",
      "B+: Good (7 pts, 60-69%) | B: Above Average (6 pts, 50-59%) | C: Pass (5 pts, 40-49%) | F: Fail (0 pts, <40%)",
      "SGPA = sum(Course Credits * Grade Points) / sum(Credits) for that semester.",
      "CGPA = Cumulative performance across all registered and completed semesters.",
    ],
    documentName: "MITAOE Examination & Evaluation Manual.pdf",
    pageNumber: 15,
    articleRef: "Section 8.1",
  },
  {
    id: "exam-faq-3",
    category: "Examinations",
    question: "How many backlogs are allowed for ATKT progression?",
    summary: "Rules governing progression to subsequent academic years under ATKT (Allowed to Keep Term).",
    bullets: [
      "A student can carry a maximum of 4 active backlog courses from the preceding year to progress to the next year.",
      "To enter 3rd Year (Semester 5): All First Year (Sem 1 & 2) courses must be 100% cleared (Zero First Year Backlogs).",
      "To enter 4th Year (Semester 7): All Second Year (Sem 3 & 4) courses must be 100% cleared.",
    ],
    documentName: "MITAOE Examination & Evaluation Manual.pdf",
    pageNumber: 18,
    articleRef: "Section 9.4",
  },

  // --- Scholarships & Aid ---
  {
    id: "schol-faq-1",
    category: "Scholarships",
    question: "What scholarships and fee concessions are available (MahaDBT & EBC)?",
    summary: "MITAOE facilitates all official Maharashtra State Government scholarship schemes through the MahaDBT portal.",
    bullets: [
      "Rajarshi Shahu Maharaj Yojna (EBC): 50% tuition fee waiver for General category with annual family income up to Rs. 8 Lakhs.",
      "Social Welfare Schemes: 100% tuition and exam fee waiver for SC/ST students; 50% fee waiver for OBC/VJNT/SBC students.",
      "Apply online on mahadbt.maharashtra.gov.in and submit hard-copy verified dossiers to the Scholarship Section by October/November.",
    ],
    documentName: "MITAOE Scholarship & Financial Aid Handbook.pdf",
    pageNumber: 3,
    articleRef: "Chapter 2",
  },
  {
    id: "schol-faq-2",
    category: "Scholarships",
    question: "What is TFWS (Tuition Fee Waiver Scheme) and how does it work?",
    summary: "A government-sanctioned merit scheme providing complete 100% tuition fee relief for high-ranking CAP applicants.",
    bullets: [
      "5% supernumerary seats in every branch are reserved under the TFWS scheme via Centralized Allotment Process (CAP).",
      "Parental annual income from all sources must be strictly below Rs. 8 Lakhs.",
      "100% Tuition Fee is waived throughout all 4 years of engineering; only development & examination fees are payable.",
    ],
    documentName: "MITAOE Scholarship & Financial Aid Handbook.pdf",
    pageNumber: 7,
    articleRef: "Chapter 4",
  },
  {
    id: "schol-faq-3",
    category: "Scholarships",
    question: "Does MITAOE offer merit awards for top academic rankers?",
    summary: "Annual cash awards are presented to the top 3 academic rankers in each department.",
    bullets: [
      "1st Rank: Rs. 25,000 cash award and certificate of merit.",
      "2nd Rank: Rs. 15,000 cash award.",
      "3rd Rank: Rs. 10,000 cash award.",
      "Criteria: Minimum annual CGPA of 9.0 without any backlogs or disciplinary infractions.",
    ],
    documentName: "MITAOE Scholarship & Financial Aid Handbook.pdf",
    pageNumber: 9,
    articleRef: "Chapter 5",
  },

  // --- Campus & Hostel ---
  {
    id: "hostel-faq-1",
    category: "Campus & Hostel",
    question: "What hostel facilities, room types, and security amenities are provided?",
    summary: "Secure on-campus and affiliated hostel facilities for both boys and girls.",
    bullets: [
      "Twin-sharing and triple-sharing rooms with study tables, beds, personal wardrobes, and attached/common washrooms.",
      "24/7 high-speed Wi-Fi, biometric turnstile security, CCTV surveillance, and solar hot water.",
      "Water purifiers on every floor, indoor sports rooms (table tennis, chess, carrom), reading halls, and weekly laundry service.",
    ],
    documentName: "MITAOE Campus Facilities & Hostel Handbook.pdf",
    pageNumber: 5,
    articleRef: "Section 3.1",
  },
  {
    id: "hostel-faq-2",
    category: "Campus & Hostel",
    question: "What are the hostel mess timings and meal rules?",
    summary: "Hygienic vegetarian and nutritious dining services managed by the Institute Mess Committee.",
    bullets: [
      "Breakfast: 7:30 AM – 9:00 AM | Lunch: 12:00 PM – 2:00 PM",
      "Evening Snacks & Tea: 5:00 PM – 6:15 PM | Dinner: 7:45 PM – 9:30 PM",
      "Special feast meals served every Sunday and festival days. Night entry biometric curfew is strictly 9:30 PM.",
    ],
    documentName: "MITAOE Campus Facilities & Hostel Handbook.pdf",
    pageNumber: 8,
    articleRef: "Section 4.2",
  },
  {
    id: "hostel-faq-3",
    category: "Campus & Hostel",
    question: "What are the central library and digital learning center timings?",
    summary: "State-of-the-art Central Library with extensive physical collections and IEEE/ScienceDirect digital access.",
    bullets: [
      "Regular Hours: Monday to Saturday 8:00 AM to 10:00 PM; Extended 24-hour reading hall during exam periods.",
      "Undergraduate students can borrow up to 4 books simultaneously for 14 days with online auto-renewal.",
      "Digital learning center with 60 high-performance workstations for research paper access and coding projects.",
    ],
    documentName: "MITAOE Campus Facilities & Hostel Handbook.pdf",
    pageNumber: 11,
    articleRef: "Section 5.0",
  },

  // --- Admissions & Fees ---
  {
    id: "adm-faq-1",
    category: "Admissions & Fees",
    question: "Can college fees be paid in installments, and what is the breakdown?",
    summary: "Fee structure determined annually by the Maharashtra Fees Regulating Authority (FRA).",
    bullets: [
      "B.Tech tuition fee: Rs. 1,65,000 + Development fee: Rs. 25,000 (approx. approved annual structure).",
      "Tuition fees may be paid in up to 2 equal installments per semester upon submitting a formal request to Accounts.",
      "Full fee clearance is required prior to End-Semester Examination hall ticket issuance.",
    ],
    documentName: "MITAOE Admissions & Fee Structure Guide.pdf",
    pageNumber: 7,
    articleRef: "Schedule B",
  },
  {
    id: "adm-faq-2",
    category: "Admissions & Fees",
    question: "What is the fee refund policy if an admission is cancelled?",
    summary: "Refund rules strictly adhere to State CET Cell Maharashtra and AICTE regulatory norms.",
    bullets: [
      "Cancellation before the cutoff date announced by State CET Cell: 100% refund after deducting max Rs. 1,000 processing fee.",
      "Cancellation after cutoff date: Tuition and development fees are retained if seat remains vacant.",
      "Hostel fee refund is calculated pro-rata on a monthly basis after deducting 1 month lock-in charge.",
    ],
    documentName: "MITAOE Admissions & Fee Structure Guide.pdf",
    pageNumber: 12,
    articleRef: "Schedule D",
  },

  // --- Placements & Careers ---
  {
    id: "place-faq-1",
    category: "Placements",
    question: "What is the placement eligibility criteria and Dream Company policy?",
    summary: "Comprehensive training and campus recruitment guidelines managed by the Training & Placement Cell.",
    bullets: [
      "Eligibility: Minimum cumulative CGPA of 6.50 with zero active backlogs at the start of Semester 7.",
      "Dream Company Policy: Securing an offer up to Rs. 7 LPA permits participating in Dream Drives (Rs. 8–15 LPA) and Super Dream (>15 LPA).",
      "Over 180 recruiters visit annually, including IBM, Veritas, Cisco, TCS, Cognizant, Infosys, and BMC Software.",
    ],
    documentName: "MITAOE Training & Placement Policy.pdf",
    pageNumber: 4,
    articleRef: "Policy 2.1",
  },
  {
    id: "place-faq-2",
    category: "Placements",
    question: "How do 8th semester industry internships count towards degree credits?",
    summary: "The autonomous curriculum offers a full-semester industry internship in Semester 8.",
    bullets: [
      "Carries 12 academic credits in the final semester curriculum.",
      "Internships must be approved by T&P Cell and HOD with verified monthly mentorship logs and mid-term evaluation.",
      "Final assessment includes an industry mentor score, technical project report, and external viva presentation.",
    ],
    documentName: "MITAOE Training & Placement Policy.pdf",
    pageNumber: 9,
    articleRef: "Policy 5.3",
  },
];

const CATEGORIES = [
  "All",
  "Academics",
  "Examinations",
  "Scholarships",
  "Campus & Hostel",
  "Admissions & Fees",
  "Placements",
] as const;

const OFFICIAL_DOCUMENTS_LIST = [
  {
    title: "MITAOE Academic Regulations & Attendance Policy",
    category: "Academics",
    version: "2025.1",
    pages: 18,
    desc: "Attendance rules, condonation, honor degrees, and probation.",
  },
  {
    title: "MITAOE Examination & Evaluation Manual",
    category: "Examinations",
    version: "2025.1",
    pages: 24,
    desc: "ISE/ESE weightage, 10-point scale, ATKT, revaluation.",
  },
  {
    title: "MITAOE Scholarship & Financial Aid Handbook",
    category: "Scholarships",
    version: "2025.1",
    pages: 12,
    desc: "MahaDBT, EBC 50% waiver, TFWS 100% waiver, merit prizes.",
  },
  {
    title: "MITAOE Campus Facilities & Hostel Handbook",
    category: "Campus & Hostel",
    version: "2025.1",
    pages: 16,
    desc: "Boys/Girls hostel, mess timings, 24/7 medical, library.",
  },
  {
    title: "MITAOE Admissions & Fee Structure Guide",
    category: "Admissions & Fees",
    version: "2025.1",
    pages: 20,
    desc: "CAP eligibility, FRA fees, installments, refund rules.",
  },
  {
    title: "MITAOE Training & Placement Cell Guidelines",
    category: "Placements",
    version: "2025.1",
    pages: 14,
    desc: "6.50 CGPA threshold, Dream company rule, 180+ companies.",
  },
];

interface Props {
  onAskQuestion: (question: string) => void;
}

export const FaqView: React.FC<Props> = ({ onAskQuestion }) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("All");
  const [expandedId, setExpandedId] = useState<string | null>("acad-faq-1");
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const toggleExpand = (id: string) => {
    setExpandedId((prev) => (prev === id ? null : id));
  };

  const handleCopy = (faq: FaqItem) => {
    const text = `${faq.question}\n\n${faq.summary}\n\nKey Points:\n${faq.bullets.map((b) => `• ${b}`).join("\n")}\n\nSource: ${faq.documentName} (p.${faq.pageNumber})`;
    navigator.clipboard.writeText(text);
    setCopiedId(faq.id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const filteredFaqs = useMemo(() => {
    const q = searchQuery.toLowerCase().trim();
    return FAQS_DATA.filter((item) => {
      const matchesCat = selectedCategory === "All" || item.category === selectedCategory;
      if (!matchesCat) return false;
      if (!q) return true;

      const inQuestion = item.question.toLowerCase().includes(q);
      const inSummary = item.summary.toLowerCase().includes(q);
      const inBullets = item.bullets.some((b) => b.toLowerCase().includes(q));
      return inQuestion || inSummary || inBullets;
    });
  }, [searchQuery, selectedCategory]);

  return (
    <div className="faq-page-view">
      <div className="faq-page-inner">
        {/* Header Hero */}
        <header className="faq-hero">
          <div className="faq-hero-badge">
            <Sparkles size={13} />
            <span>Authoritative College Regulations & FAQs</span>
          </div>
          <h1 className="faq-hero-title">Most Asked Questions</h1>
          <p className="faq-hero-sub">
            Instant, verified answers from official MITAOE handbooks. Tap any question to read or ask follow-ups in chat.
          </p>

          {/* Search Bar */}
          <div className="faq-search-wrap">
            <Search size={16} className="faq-search-icon" />
            <input
              type="text"
              className="faq-search-input"
              placeholder="Search attendance, ATKT, scholarships, hostels, exams..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            {searchQuery && (
              <button className="faq-search-clear" onClick={() => setSearchQuery("")} title="Clear search">
                <X size={14} />
              </button>
            )}
          </div>

          {/* Category Chips */}
          <div className="faq-category-chips">
            {CATEGORIES.map((cat) => (
              <button
                key={cat}
                className={`faq-cat-chip ${selectedCategory === cat ? "active" : ""}`}
                onClick={() => setSelectedCategory(cat)}
              >
                {cat}
              </button>
            ))}
          </div>
        </header>

        {/* FAQs Accordion List */}
        <section className="faq-list-section">
          <div className="faq-list-header">
            <span className="faq-count-label">
              Showing {filteredFaqs.length} {filteredFaqs.length === 1 ? "question" : "questions"}
            </span>
            <span className="faq-offline-badge">
              <span className="status-dot green" />
              Instant 0ms verified answers
            </span>
          </div>

          {filteredFaqs.length === 0 ? (
            <div className="faq-empty-state">
              <BookOpen size={36} className="faq-empty-icon" />
              <h3>No matching questions found</h3>
              <p>Try searching for "attendance", "scholarship", or "revaluation".</p>
              <button className="faq-reset-btn" onClick={() => { setSearchQuery(""); setSelectedCategory("All"); }}>
                Reset filters
              </button>
            </div>
          ) : (
            <div className="faq-accordion-container">
              {filteredFaqs.map((faq) => {
                const isExpanded = expandedId === faq.id;
                return (
                  <article key={faq.id} className={`faq-card ${isExpanded ? "expanded" : ""}`}>
                    {/* Clickable Header */}
                    <button
                      className="faq-card-trigger"
                      onClick={() => toggleExpand(faq.id)}
                      aria-expanded={isExpanded}
                    >
                      <div className="faq-trigger-content">
                        <div className="faq-card-category-row">
                          <span className="faq-category-tag">{faq.category}</span>
                          {faq.articleRef && <span className="faq-article-tag">{faq.articleRef}</span>}
                        </div>
                        <h2 className="faq-card-question">{faq.question}</h2>
                      </div>
                      <div className={`faq-chevron-wrap ${isExpanded ? "open" : ""}`}>
                        <ChevronDown size={17} />
                      </div>
                    </button>

                    {/* Expandable Body */}
                    {isExpanded && (
                      <div className="faq-card-body">
                        <p className="faq-summary-text">{faq.summary}</p>

                        <div className="faq-bullets-list">
                          {faq.bullets.map((point, idx) => (
                            <div key={idx} className="faq-bullet-item">
                              <span className="faq-bullet-dot" />
                              <span className="faq-bullet-text">{point}</span>
                            </div>
                          ))}
                        </div>

                        {/* Citation & Action Toolbar */}
                        <div className="faq-card-footer">
                          <div className="faq-source-reference" title="Verified College Document">
                            <BookOpen size={12} />
                            <span className="faq-source-doc">{faq.documentName}</span>
                            <span className="faq-source-page">p.{faq.pageNumber}</span>
                          </div>

                          <div className="faq-action-buttons">
                            <button
                              className={`faq-btn-action ${copiedId === faq.id ? "copied" : ""}`}
                              onClick={() => handleCopy(faq)}
                              title="Copy answer to clipboard"
                            >
                              {copiedId === faq.id ? (
                                <>
                                  <Check size={12} />
                                  <span>Copied</span>
                                </>
                              ) : (
                                <>
                                  <Copy size={12} />
                                  <span>Copy</span>
                                </>
                              )}
                            </button>

                            <button
                              className="faq-btn-action primary"
                              onClick={() => onAskQuestion(faq.question)}
                              title="Open this question in the AI Chat"
                            >
                              <MessageSquare size={12} />
                              <span>Ask in Chat ↗</span>
                            </button>
                          </div>
                        </div>
                      </div>
                    )}
                  </article>
                );
              })}
            </div>
          )}
        </section>

        {/* Official College Handbooks Showcase */}
        <section className="faq-handbooks-section">
          <div className="faq-handbooks-header">
            <div>
              <h2 className="faq-handbooks-title">Official Handbooks & Reference Manuals</h2>
              <p className="faq-handbooks-sub">
                Grounded source documents indexed by MIT Academy of Engineering Knowledge Engine
              </p>
            </div>
            <span className="faq-handbooks-count">6 Official Documents</span>
          </div>

          <div className="faq-handbooks-grid">
            {OFFICIAL_DOCUMENTS_LIST.map((doc, idx) => (
              <div key={idx} className="faq-handbook-card">
                <div className="faq-doc-card-top">
                  <span className="faq-doc-category">{doc.category}</span>
                  <span className="faq-doc-version">v{doc.version} · {doc.pages} pages</span>
                </div>
                <h3 className="faq-doc-title">{doc.title}</h3>
                <p className="faq-doc-desc">{doc.desc}</p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
};
