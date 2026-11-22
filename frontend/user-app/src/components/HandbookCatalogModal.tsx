import React, { useState, useMemo, useEffect } from "react";
import { X, Search, BookOpen, ArrowRight, Layers, FileText, CheckCircle2 } from "lucide-react";

export interface HandbookDoc {
  id: string;
  title: string;
  category: "Academics" | "Examinations" | "Financial Aid" | "Campus Life" | "Admissions" | "Placements";
  version: string;
  pages: number;
  description: string;
  sampleQuestions: string[];
}

export const OFFICIAL_HANDBOOKS: HandbookDoc[] = [
  {
    id: "doc-academic-regulations",
    title: "MITAOE Academic Regulations & Attendance Policy",
    category: "Academics",
    version: "2025.1",
    pages: 18,
    description: "Rules governing attendance requirements (75% mandatory), condonation on medical grounds, credit requirements, and academic probation.",
    sampleQuestions: [
      "What is the minimum attendance requirement?",
      "What happens if my attendance falls below 75%?",
      "What is the procedure for medical leave condonation?",
      "What are the criteria for academic honors and distinction?"
    ]
  },
  {
    id: "doc-exam-evaluation",
    title: "MITAOE Examination & Evaluation Manual",
    category: "Examinations",
    version: "2025.1",
    pages: 24,
    description: "Assessment structure (ISE 40%, ESE 60%), 10-point grading scale, backlog rules (ATKT progression), photocopy and revaluation procedure.",
    sampleQuestions: [
      "Explain the exam revaluation process",
      "What is the grading scale and how is CGPA calculated?",
      "How many backlogs are allowed for ATKT progression?",
      "What are the rules regarding missed mid-semester exams?"
    ]
  },
  {
    id: "doc-scholarships",
    title: "MITAOE Scholarship & Financial Aid Handbook",
    category: "Financial Aid",
    version: "2025.1",
    pages: 12,
    description: "MahaDBT state schemes, EBC 50% tuition waiver (income up to 8L), TFWS 100% tuition waiver, SC/ST/OBC fee benefits, and annual merit awards.",
    sampleQuestions: [
      "Where can I find scholarship information?",
      "What is the eligibility for EBC and TFWS fee concessions?",
      "What documents are required for MahaDBT scholarship renewal?",
      "Are there merit-based scholarships for top rankers?"
    ]
  },
  {
    id: "doc-hostel-campus",
    title: "MITAOE Campus Facilities & Hostel Handbook",
    category: "Campus Life",
    version: "2025.1",
    pages: 16,
    description: "Boys & girls on-campus hostel rules, twin/triple rooms, mess timings (7:30 AM - 9:30 PM), library 8 AM - 10 PM, 24/7 medical & security.",
    sampleQuestions: [
      "What hostel facilities are available?",
      "What are the hostel mess timings and menu rules?",
      "What are the library hours and digital book lending limits?",
      "Is on-campus medical and ambulance assistance available 24/7?"
    ]
  },
  {
    id: "doc-admissions-fees",
    title: "MITAOE Admissions & Fee Structure Guide",
    category: "Admissions",
    version: "2025.1",
    pages: 20,
    description: "B.Tech eligibility, CAP round procedures, DSE lateral entry, approved FRA fee breakdown, installment plans, and cancellation refund slabs.",
    sampleQuestions: [
      "What is the fee structure for B.Tech programmes?",
      "What is the refund policy if I cancel my admission?",
      "Can tuition fees be paid in installments?",
      "What are the eligibility criteria for lateral entry direct second year (DSE)?"
    ]
  },
  {
    id: "doc-placements-internships",
    title: "MITAOE Training & Placement Cell Guidelines",
    category: "Placements",
    version: "2025.1",
    pages: 14,
    description: "Placement eligibility (minimum 6.50 CGPA), Dream Company policy (up to 24 LPA), semester internship credits, and 180+ visiting recruiters.",
    sampleQuestions: [
      "What is the minimum CGPA required to sit for campus placements?",
      "What are the placement statistics and top recruiting companies?",
      "Can I accept a second offer if I receive a dream company package?",
      "How do semester internships count towards degree credits?"
    ]
  }
];

const CATEGORIES = ["All", "Academics", "Examinations", "Financial Aid", "Campus Life", "Admissions", "Placements"] as const;

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSelectQuestion: (question: string) => void;
}

export const HandbookCatalogModal: React.FC<Props> = ({ isOpen, onClose, onSelectQuestion }) => {
  const [selectedCategory, setSelectedCategory] = useState<string>("All");
  const [searchQuery, setSearchQuery] = useState<string>("");

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    if (isOpen) {
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  const filteredHandbooks = useMemo(() => {
    const q = searchQuery.toLowerCase().trim();
    return OFFICIAL_HANDBOOKS.filter((doc) => {
      const matchesCategory = selectedCategory === "All" || doc.category === selectedCategory;
      if (!matchesCategory) return false;
      if (!q) return true;

      const titleMatch = doc.title.toLowerCase().includes(q);
      const descMatch = doc.description.toLowerCase().includes(q);
      const questionsMatch = doc.sampleQuestions.some((sq) => sq.toLowerCase().includes(q));
      return titleMatch || descMatch || questionsMatch;
    });
  }, [selectedCategory, searchQuery]);

  if (!isOpen) return null;

  return (
    <div className="catalog-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="catalog-modal-sheet" onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <div className="catalog-modal-header">
          <div className="catalog-modal-title-row">
            <div className="catalog-icon-box">
              <BookOpen size={20} />
            </div>
            <div>
              <h2 className="catalog-modal-heading">Official College Handbooks & Knowledge Catalog</h2>
              <p className="catalog-modal-sub">
                Grounded repository of authoritative policies, regulations, and official FAQs
              </p>
            </div>
          </div>
          <button className="icon-btn catalog-close-btn" onClick={onClose} title="Close Catalog">
            <X size={18} />
          </button>
        </div>

        {/* Filter Bar & Search */}
        <div className="catalog-filter-bar">
          <div className="catalog-search-wrap">
            <Search size={15} className="catalog-search-icon" />
            <input
              type="text"
              className="catalog-search-input"
              placeholder="Search handbooks or sample questions..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              autoFocus
            />
            {searchQuery && (
              <button className="catalog-search-clear" onClick={() => setSearchQuery("")}>
                <X size={13} />
              </button>
            )}
          </div>

          <div className="catalog-tabs-scroller">
            {CATEGORIES.map((cat) => (
              <button
                key={cat}
                className={`catalog-tab-chip ${selectedCategory === cat ? "active" : ""}`}
                onClick={() => setSelectedCategory(cat)}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        {/* Catalog Grid */}
        <div className="catalog-modal-body">
          {filteredHandbooks.length === 0 ? (
            <div className="catalog-empty-state">
              <Layers size={32} className="catalog-empty-icon" />
              <p className="catalog-empty-title">No matching handbook found</p>
              <p className="catalog-empty-desc">Try searching for "attendance", "scholarship", or "exam".</p>
            </div>
          ) : (
            <div className="catalog-cards-grid">
              {filteredHandbooks.map((doc) => (
                <div key={doc.id} className="catalog-handbook-card">
                  <div className="catalog-card-top">
                    <span className="catalog-badge-category">{doc.category}</span>
                    <span className="catalog-badge-meta">v{doc.version} · {doc.pages} pages</span>
                  </div>

                  <h3 className="catalog-card-title">{doc.title}</h3>
                  <p className="catalog-card-description">{doc.description}</p>

                  <div className="catalog-card-questions">
                    <div className="catalog-questions-label">
                      <FileText size={12} />
                      <span>Common Questions in this Document:</span>
                    </div>
                    <div className="catalog-questions-list">
                      {doc.sampleQuestions.map((q, idx) => (
                        <button
                          key={idx}
                          className="catalog-question-btn"
                          onClick={() => {
                            onSelectQuestion(q);
                            onClose();
                          }}
                        >
                          <span className="catalog-question-text">{q}</span>
                          <ArrowRight size={13} className="catalog-question-arrow" />
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Modal Footer Note */}
        <div className="catalog-modal-footer">
          <div className="catalog-footer-badge">
            <CheckCircle2 size={13} />
            <span>Answers generated from these handbooks cite exact article numbers and official page references.</span>
          </div>
        </div>
      </div>
    </div>
  );
};
