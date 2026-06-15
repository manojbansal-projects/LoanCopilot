"""
Build the end-to-end Learner Guide for the Loan Copilot Capstone project.
Produces: docs/loan_copilot_learner_guide.docx
Run:  python scripts/build_learner_guide.py
"""
from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import copy

# ── Colour palette ────────────────────────────────────────────────────────────
NAVY   = RGBColor(0x14, 0x3D, 0x7A)
BLUE   = RGBColor(0x1F, 0x77, 0xB4)
TEAL   = RGBColor(0x00, 0x7B, 0x83)
GREEN  = RGBColor(0x1A, 0x7A, 0x3C)
PURPLE = RGBColor(0x6A, 0x0D, 0xAD)
AMBER  = RGBColor(0xD4, 0x85, 0x00)
RED    = RGBColor(0xC0, 0x00, 0x00)
WHITE  = RGBColor(0xFF, 0xFF, 0xFF)
LTGRAY = RGBColor(0xF2, 0xF2, 0xF2)
DKGRAY = RGBColor(0x40, 0x40, 0x40)
BLACK  = RGBColor(0x00, 0x00, 0x00)
GOLD   = RGBColor(0xFF, 0xD7, 0x00)
LTBLUE = RGBColor(0xDE, 0xEB, 0xF7)
LTGRN  = RGBColor(0xE2, 0xEF, 0xDA)
LTAMB  = RGBColor(0xFF, 0xF2, 0xCC)
LTPURP = RGBColor(0xF3, 0xEE, 0xF9)
LTRED  = RGBColor(0xFF, 0xE7, 0xE7)


# ── XML helpers ───────────────────────────────────────────────────────────────
def set_cell_color(cell, rgb: RGBColor):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), f"{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}")
    tcPr.append(shd)


def set_cell_border(cell, top=None, bottom=None, left=None, right=None):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement("w:tcBorders")
    for side, color in (("top", top), ("bottom", bottom), ("left", left), ("right", right)):
        if color is not None:
            el = OxmlElement(f"w:{side}")
            el.set(qn("w:val"), "single")
            el.set(qn("w:sz"), "6")
            el.set(qn("w:color"), color)
            tcBorders.append(el)
    tcPr.append(tcBorders)


def set_row_height(row, height_cm):
    tr = row._tr
    trPr = tr.get_or_add_trPr()
    trHeight = OxmlElement("w:trHeight")
    trHeight.set(qn("w:val"), str(int(height_cm * 567)))
    trPr.append(trHeight)


# ── Style helpers ─────────────────────────────────────────────────────────────
def h1(doc, text):
    p = doc.add_heading(text, level=1)
    p.runs[0].font.color.rgb = NAVY
    p.paragraph_format.space_before = Pt(18)
    p.paragraph_format.space_after = Pt(6)
    return p


def h2(doc, text):
    p = doc.add_heading(text, level=2)
    p.runs[0].font.color.rgb = BLUE
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(4)
    return p


def h3(doc, text):
    p = doc.add_heading(text, level=3)
    p.runs[0].font.color.rgb = TEAL
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(2)
    return p


def body(doc, text, bold=False, color=None, size=11, italic=False, indent=False):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(4)
    if indent:
        p.paragraph_format.left_indent = Inches(0.3)
    run = p.add_run(text)
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    if color:
        run.font.color.rgb = color
    return p


def bullet(doc, text, level=0, color=None, bold=False):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.left_indent = Inches(0.3 + level * 0.2)
    run = p.add_run(text)
    run.font.size = Pt(10.5)
    if color:
        run.font.color.rgb = color
    if bold:
        run.font.bold = True
    return p


def numbered(doc, text, color=None):
    p = doc.add_paragraph(style="List Number")
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.left_indent = Inches(0.3)
    run = p.add_run(text)
    run.font.size = Pt(10.5)
    if color:
        run.font.color.rgb = color
    return p


def code_block(doc, lines):
    """Render a monospace code block inside a shaded table."""
    t = doc.add_table(rows=1, cols=1)
    t.style = "Table Grid"
    cell = t.rows[0].cells[0]
    set_cell_color(cell, RGBColor(0xF5, 0xF5, 0xF5))
    for i, line in enumerate(lines if isinstance(lines, list) else lines.split("\n")):
        if i == 0:
            p = cell.paragraphs[0]
        else:
            p = cell.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.space_before = Pt(0)
        run = p.add_run(line)
        run.font.name = "Courier New"
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(0x1A, 0x1A, 0x5E)
    doc.add_paragraph()


def callout(doc, title, text, bg: RGBColor = LTBLUE, title_color: RGBColor = NAVY):
    """Coloured callout box."""
    t = doc.add_table(rows=2, cols=1)
    t.style = "Table Grid"
    # Title row
    hdr = t.rows[0].cells[0]
    set_cell_color(hdr, title_color)
    hp = hdr.paragraphs[0]
    hp.paragraph_format.space_after = Pt(0)
    hr = hp.add_run(f"  {title}")
    hr.font.bold = True
    hr.font.color.rgb = WHITE
    hr.font.size = Pt(10)
    # Body row
    bdy = t.rows[1].cells[0]
    set_cell_color(bdy, bg)
    bp = bdy.paragraphs[0]
    bp.paragraph_format.space_after = Pt(0)
    bp.paragraph_format.left_indent = Inches(0.1)
    br = bp.add_run(f"  {text}")
    br.font.size = Pt(10)
    doc.add_paragraph()


def divider(doc):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(6)
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "4")
    bottom.set(qn("w:color"), "143D7A")
    pBdr.append(bottom)
    pPr.append(pBdr)
    return p


def two_col_table(doc, rows_data, col_widths=(2.5, 4.5),
                  header_bg=NAVY, row_bg=LTBLUE, alt_bg=LTGRAY):
    """Generic two-column table with a header row."""
    t = doc.add_table(rows=len(rows_data), cols=2)
    t.style = "Table Grid"
    for i, (left, right) in enumerate(rows_data):
        c0, c1 = t.rows[i].cells
        bg = header_bg if i == 0 else (row_bg if i % 2 == 1 else alt_bg)
        set_cell_color(c0, bg)
        set_cell_color(c1, bg)
        fc = WHITE if i == 0 else BLACK
        for cell, text in ((c0, left), (c1, right)):
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            r = p.add_run(text)
            r.font.size = Pt(10)
            r.font.bold = (i == 0)
            r.font.color.rgb = fc
    doc.add_paragraph()
    return t


def three_col_table(doc, rows_data, header_bg=NAVY, alt=True):
    t = doc.add_table(rows=len(rows_data), cols=3)
    t.style = "Table Grid"
    for i, (c1t, c2t, c3t) in enumerate(rows_data):
        cells = t.rows[i].cells
        bg = header_bg if i == 0 else (LTBLUE if i % 2 == 1 else LTGRAY)
        fc = WHITE if i == 0 else BLACK
        for cell, text in zip(cells, (c1t, c2t, c3t)):
            set_cell_color(cell, bg)
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            r = p.add_run(text)
            r.font.size = Pt(10)
            r.font.bold = (i == 0)
            r.font.color.rgb = fc
    doc.add_paragraph()
    return t


def flow_diagram(doc, steps):
    """Render a horizontal flow as a single-row multi-column table."""
    n = len(steps)
    t = doc.add_table(rows=1, cols=n * 2 - 1)
    t.style = "Table Grid"
    for i, (label, color) in enumerate(steps):
        col_idx = i * 2
        cell = t.rows[0].cells[col_idx]
        set_cell_color(cell, color)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        r = p.add_run(label)
        r.font.size = Pt(9)
        r.font.bold = True
        r.font.color.rgb = WHITE
        if i < len(steps) - 1:
            arr = t.rows[0].cells[col_idx + 1]
            set_cell_color(arr, RGBColor(0xE8, 0xE8, 0xE8))
            ap = arr.paragraphs[0]
            ap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            ap.paragraph_format.space_after = Pt(0)
            ar = ap.add_run("→")
            ar.font.size = Pt(12)
    doc.add_paragraph()


def arch_diagram(doc):
    """Create the system architecture diagram as a table grid."""
    rows = [
        # (label, bg, text_color, bold)
        ("STREAMLIT WEB UI  (deployment/app.py)  — Customer Chat + RM Dashboard", NAVY, WHITE, True),
        ("SAFETY GATE  (safety/guardrails.py + pii_filter.py)", RGBColor(0x7B, 0x36, 0x00), WHITE, True),
        ("Stage A: Keyword Blocklist  <1 ms · zero tokens        │        Stage B: GPT-4o-mini Classifier  ~150 ms · <50 tokens", RGBColor(0xFF, 0xF0, 0xD0), BLACK, False),
        ("LANGCHAIN REACT AGENT  (agent/core_agent.py)  — GPT-4o  ·  System Prompt V3  ·  10-turn sliding window", BLUE, WHITE, True),
        ("5 AI TOOLS  (tools/)  — deterministic, called by LLM via function-calling API", TEAL, WHITE, True),
        ("  calculate_emi    │    check_eligibility    │    get_document_checklist    │    query_loan_policy    │    generate_escalation_summary  ", RGBColor(0xE0, 0xF4, 0xF4), BLACK, False),
        ("MCP EXPOSURE LAYER  (loan_mcp/server.py)  — FastMCP v1.27  ·  stdio & HTTP transport  ·  USE_MCP=true", LTPURP, PURPLE, False),
        ("RAG PIPELINE  (retrieval/)  — ChromaDB  ·  text-embedding-3-small  ·  top-5 chunks", GREEN, WHITE, True),
        ("  4 Policy Docs  ·  500-token chunks  ·  100 overlap  ·  Persistent vector store  ", LTGRN, BLACK, False),
        ("MEMORY  (agent/memory.py)  — CustomerProfile dataclass  +  ConversationBufferWindowMemory(k=10)", RGBColor(0x44, 0x44, 0x88), WHITE, True),
        ("OBSERVABILITY  (monitoring/langfuse_logger.py)  — Langfuse self-hosted  ·  per-session traces  ·  LLM-as-judge eval", RGBColor(0x30, 0x30, 0x30), WHITE, True),
    ]
    t = doc.add_table(rows=len(rows), cols=1)
    t.style = "Table Grid"
    for i, (label, bg, fc, bold) in enumerate(rows):
        cell = t.rows[i].cells[0]
        set_cell_color(cell, bg)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(4)
        r = p.add_run(label)
        r.font.size = Pt(10 if bold else 9)
        r.font.bold = bold
        r.font.color.rgb = fc
    doc.add_paragraph()


def message_flow_diagram(doc):
    """Visual step-by-step message flow."""
    steps = [
        ("1\nUser types\nmessage", NAVY),
        ("2\nStreamlit\nsends to agent", BLUE),
        ("3\nSafety Gate\nStage A + B", RGBColor(0xD4, 0x85, 0x00)),
        ("4\nLangChain\nReAct Agent", TEAL),
        ("5\nTool calls\n(1–3 tools)", GREEN),
        ("6\nLLM crafts\nfinal reply", BLUE),
        ("7\nPII masked\n→ logged", PURPLE),
        ("8\nResponse to\nuser", NAVY),
    ]
    flow_diagram(doc, steps)


def rag_pipeline_diagram(doc):
    steps_ingest = [
        ("Raw Policy\n.txt files", DKGRAY),
        ("Document\nLoader", NAVY),
        ("Text\nChunker\n500 tok", BLUE),
        ("OpenAI\nEmbedder", TEAL),
        ("ChromaDB\nPersist", GREEN),
    ]
    steps_query = [
        ("User\nQuery", DKGRAY),
        ("Embed\nQuery", TEAL),
        ("Similarity\nSearch\ntop-5", GREEN),
        ("Retrieved\nChunks", BLUE),
        ("LLM\nGrounded\nAnswer", NAVY),
    ]
    body(doc, "Ingestion pipeline (run once / on policy change):", bold=True, size=10)
    flow_diagram(doc, steps_ingest)
    body(doc, "Query pipeline (every policy question):", bold=True, size=10)
    flow_diagram(doc, steps_query)


def safety_diagram(doc):
    steps = [
        ("User\nMessage", DKGRAY),
        ("Stage A\nKeyword\n<1 ms", AMBER),
        ("BLOCK?\nReturn\nerror msg", RED),
        ("Stage B\nGPT-4o-mini\n~150 ms", AMBER),
        ("OUT_OF\nSCOPE?", RED),
        ("PASS\n→ Agent", GREEN),
    ]
    flow_diagram(doc, steps)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN DOCUMENT
# ══════════════════════════════════════════════════════════════════════════════

def build():
    doc = Document()

    # Page margins
    for section in doc.sections:
        section.top_margin    = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin   = Inches(1.1)
        section.right_margin  = Inches(1.1)

    # Default font
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)

    # ── COVER ─────────────────────────────────────────────────────────────────
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(40)
    r = p.add_run("AI-Powered Loan Origination Copilot")
    r.font.size = Pt(26)
    r.font.bold = True
    r.font.color.rgb = NAVY
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    p2 = doc.add_paragraph()
    r2 = p2.add_run("Complete End-to-End Learner Guide")
    r2.font.size = Pt(16)
    r2.font.color.rgb = BLUE
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER

    p3 = doc.add_paragraph()
    r3 = p3.add_run("IIT Madras AI Capstone  ·  Scenario 2: Banking  ·  Track A: LangChain")
    r3.font.size = Pt(12)
    r3.font.color.rgb = DKGRAY
    r3.font.italic = True
    p3.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph()
    callout(doc,
        "What This Guide Covers",
        "Every component of the project explained in plain English — what it does, why it exists, "
        "how it connects to everything else, and how to build it yourself from scratch. "
        "By the end you will be able to explain any part of this system in full detail.",
        bg=LTBLUE, title_color=NAVY)

    doc.add_page_break()

    # ── TABLE OF CONTENTS (manual) ────────────────────────────────────────────
    h1(doc, "Table of Contents")
    toc = [
        ("1", "What Is This Project?", "The problem, the solution, and who it is for"),
        ("2", "The Big Picture — Architecture", "All components and how they connect"),
        ("3", "Tech Stack Explained Simply", "Every technology and why it was chosen"),
        ("4", "The 9 Build Phases", "How the system evolved from rules to full AI"),
        ("5", "Configuration — the Single Source of Truth", "deployment/config.py"),
        ("6", "The Agent Core", "agent/core_agent.py — the brain"),
        ("7", "System Prompts", "agent/prompts.py — instructions to the LLM"),
        ("8", "Memory & Planner", "agent/memory.py + agent/planner.py"),
        ("9", "The 5 AI Tools", "What each tool does and how it is built"),
        ("10", "The RAG Pipeline", "retrieval/ — teaching the AI about loan policies"),
        ("11", "The Safety Gate", "safety/guardrails.py + safety/pii_filter.py"),
        ("12", "Observability with Langfuse", "monitoring/langfuse_logger.py"),
        ("13", "RLHF — Learning from Feedback", "policy_rlhf/ pipeline"),
        ("14", "MCP — Exposing Tools to the World", "loan_mcp/ server and client"),
        ("15", "The Web UI (Streamlit)", "deployment/app.py"),
        ("16", "End-to-End Message Flow", "What happens step by step on every turn"),
        ("17", "The 4 Loan Products", "Home, Personal, MSME, New Car"),
        ("18", "Evaluation Framework", "426 tests, 3 suites, LLM-as-judge"),
        ("19", "How to Build It From Scratch", "Complete step-by-step recipe"),
        ("20", "Key Design Decisions & Why", "The engineering judgement calls"),
    ]
    three_col_table(doc, [("No.", "Section", "Topic")] +
                    [(n, s, t) for n, s, t in toc], header_bg=NAVY)

    doc.add_page_break()

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 1 — WHAT IS THIS PROJECT?
    # ════════════════════════════════════════════════════════════════════════
    h1(doc, "1  What Is This Project?")

    h2(doc, "1.1  The Problem")
    body(doc,
        "When a bank customer walks into a branch and asks 'Can I get a home loan?' — "
        "a human Relationship Manager (RM) has to spend 20–30 minutes asking questions, "
        "checking rules, calculating EMIs, and listing documents. This is expensive, slow, "
        "and inconsistent. Customers often leave without clear answers because the RM is busy "
        "or the branch is closed.")

    h2(doc, "1.2  The Solution")
    body(doc,
        "This project builds an AI-powered Loan Origination Copilot — a conversational "
        "chatbot that does everything the RM does in the first meeting, available 24/7. "
        "A customer types in plain English (e.g. 'I want to buy a house, can I afford it?') "
        "and the system:")
    for item in [
        "Identifies the right loan product (Home, Personal, MSME, or New Car)",
        "Collects the customer's profile through natural conversation",
        "Checks indicative eligibility using hard bank rules",
        "Calculates the monthly EMI range",
        "Lists all documents needed",
        "Answers policy questions (interest rates, NRI eligibility, prepayment rules, etc.) "
        "from actual bank policy documents",
        "Escalates large/complex cases to a human RM with a full briefing packet",
    ]:
        bullet(doc, item)

    callout(doc, "Important: Indicative Only",
        "The system always says 'indicative' or 'subject to credit appraisal'. "
        "It never promises a loan will be approved. This is a legal and ethical requirement. "
        "The final approval decision is always made by a human credit officer.",
        bg=LTAMB, title_color=AMBER)

    h2(doc, "1.3  Who Is It For?")
    two_col_table(doc, [
        ("User", "What they get"),
        ("Retail Bank Customer", "Self-service loan enquiry — no branch visit needed for early screening"),
        ("Relationship Manager", "Dashboard showing escalated cases with full customer brief"),
        ("Bank IT / API Team", "MCP server exposes all tools to external agents via standard protocol"),
        ("Data Science Team", "Langfuse observability — every trace, score, and evaluation result logged"),
    ])

    h2(doc, "1.4  The 4 Loan Products Covered")
    three_col_table(doc, [
        ("Product", "Amount Range", "Max Tenure"),
        ("Home Loan", "₹5 L – ₹5 Cr", "30 years (360 months)"),
        ("Personal Loan", "₹50 K – ₹40 L", "5 years (60 months)"),
        ("MSME Loan (Business)", "₹50 K – ₹10 Cr", "15 years (180 months)"),
        ("New Car Loan", "₹3 L – ₹20 L", "7 years (84 months)"),
    ])

    doc.add_page_break()

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 2 — BIG PICTURE ARCHITECTURE
    # ════════════════════════════════════════════════════════════════════════
    h1(doc, "2  The Big Picture — Architecture")
    body(doc,
        "The diagram below shows every layer of the system from top to bottom. "
        "Think of it as a stack — when a customer types a message, it travels "
        "DOWN through these layers, and the reply travels back UP.")
    doc.add_paragraph()
    arch_diagram(doc)

    h2(doc, "2.1  How the Layers Connect")
    body(doc,
        "Here is what each arrow represents in plain English:")
    two_col_table(doc, [
        ("From → To", "What flows"),
        ("Customer → Streamlit UI", "Customer types a message in the browser"),
        ("Streamlit → Safety Gate", "Every message is checked before the AI sees it"),
        ("Safety Gate → LangChain Agent", "Only safe, in-scope messages reach the AI"),
        ("LangChain Agent → Tools", "LLM decides which tool(s) to call; tools return structured data"),
        ("LangChain Agent → RAG Pipeline", "Policy questions trigger a vector search for relevant text"),
        ("Agent → Memory", "Conversation history and customer profile are read/written each turn"),
        ("Agent → Langfuse", "Every token, tool call, and score is logged for observability"),
        ("Tools → MCP Server", "The same tools are also exposed externally via MCP protocol"),
    ])

    h2(doc, "2.2  File Map — Where to Find What")
    three_col_table(doc, [
        ("What you want", "File / Folder", "Key class / function"),
        ("Agent brain", "agent/core_agent.py", "LoanCopilotAgent"),
        ("LLM instructions", "agent/prompts.py", "V3_COT_SAFETY (SYSTEM_PROMPT)"),
        ("Memory & profile", "agent/memory.py", "CustomerProfile, SessionState"),
        ("Field collection order", "agent/planner.py", "COLLECTION_SEQUENCE"),
        ("5 AI tools", "tools/", "5 @tool functions"),
        ("All tools registered", "tools/tool_registry.py", "get_all_tools(), get_mcp_tools()"),
        ("RAG retrieval", "retrieval/retriever.py", "retrieve(query)"),
        ("ChromaDB store", "retrieval/chroma_store.py", "load_store()"),
        ("Safety filtering", "safety/guardrails.py", "keyword_filter(), classify_intent()"),
        ("PII masking", "safety/pii_filter.py", "mask(text)"),
        ("Observability", "monitoring/langfuse_logger.py", "get_langfuse_callback()"),
        ("RLHF pipeline", "policy_rlhf/", "feedback_collector, policy_checker, policy_updater"),
        ("MCP server", "loan_mcp/server.py", "FastMCP — all 5 tools via MCP protocol"),
        ("MCP client", "loan_mcp/client.py", "call_tool_sync(), list_tools_sync()"),
        ("Web UI", "deployment/app.py", "Streamlit chat interface"),
        ("All configuration", "deployment/config.py", "env vars, ceilings, paths"),
        ("Policy documents", "knowledge/raw/", "4 synthetic .txt files"),
        ("Vector DB", "knowledge/chromadb/", "Persistent ChromaDB collection"),
    ])

    doc.add_page_break()

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 3 — TECH STACK
    # ════════════════════════════════════════════════════════════════════════
    h1(doc, "3  Tech Stack Explained Simply")
    body(doc,
        "Every technology was chosen for a specific reason. Here is what each one does "
        "and why it was picked over alternatives.")

    three_col_table(doc, [
        ("Technology", "What it does (simple explanation)", "Why this one?"),
        ("Python 3.11+", "The programming language everything is written in",
         "Universal for AI/ML; best library support"),
        ("LangChain", "Framework that connects LLMs with tools and memory. "
         "Think of it as the 'plumbing' between GPT and your tools.",
         "ReAct agent loop, tool binding, memory — all out of the box"),
        ("OpenAI GPT-4o", "The main 'brain' — reads conversation, decides which tool to call, "
         "writes the final response",
         "Best reasoning + function-calling; zero-shot tool selection"),
        ("OpenAI GPT-4o-mini", "A smaller, faster, cheaper model used only for safety "
         "classification (is this message safe?)",
         "Safety check needs <50 tokens; mini is 10× cheaper"),
        ("OpenAI text-embedding-3-small", "Converts text to a list of 1536 numbers "
         "(a 'vector') that captures meaning",
         "Best cost/quality ratio for semantic search"),
        ("ChromaDB", "A local database that stores those number-vectors. "
         "When you search it, it returns the text most similar to your query.",
         "Runs locally — no cloud dependency; persists to disk"),
        ("Streamlit", "Turns a Python script into a web app with a chat interface. "
         "No HTML/CSS needed.",
         "Fastest path to a working UI; ideal for prototypes"),
        ("Langfuse (self-hosted)", "Records every AI call — tokens used, tools called, "
         "scores, latency. Like a flight recorder for the AI.",
         "Self-hosted = all customer data stays on-premises; cloud-hosted tools like "
         "LangSmith were excluded for banking data-residency compliance"),
        ("FastMCP (mcp v1.27)", "Exposes all 5 tools via a standard protocol (MCP) "
         "so external agents like Claude Desktop can call them",
         "Auto-generates JSON schemas from Python type hints; minimal boilerplate"),
        ("python-dotenv", "Loads secrets (API keys) from a .env file so they "
         "never appear in the code",
         "Standard secure practice"),
        ("pytest (426 tests)", "Automated test runner — runs all tests in under 60 seconds "
         "to catch regressions",
         "Industry standard; parametrize + fixtures keep tests DRY"),
    ])

    doc.add_page_break()

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 4 — THE 9 BUILD PHASES
    # ════════════════════════════════════════════════════════════════════════
    h1(doc, "4  The 9 Build Phases — How the System Evolved")
    body(doc,
        "The project was built over 10 days in 9 phases. Each phase added a new capability. "
        "You can still run the agent at any phase level by passing --phase N to the CLI. "
        "This incremental approach means each layer could be tested independently before "
        "the next was added.")

    three_col_table(doc, [
        ("Phase", "What was built", "Key code added"),
        ("Phase 1 — Setup", "Project structure, requirements, .env template, config",
         "deployment/config.py, requirements.txt"),
        ("Phase 2 — Rules Engine (no LLM)",
         "Keyword intent detection, regex profile extraction, rule-based EMI/eligibility. "
         "Works entirely offline — no API key needed.",
         "agent/core_agent.py (_detect_intent, _extract_profile, _rules_response)"),
        ("Phase 3 — LLM Integration",
         "Connect GPT-4o; add Langfuse tracing; test 3 prompt variants (V1/V2/V3) "
         "and select the best one using LLM-as-judge scoring.",
         "agent/prompts.py (V1, V2, V3); monitoring/langfuse_logger.py"),
        ("Phase 4 — RAG",
         "Build ChromaDB vector store from 4 policy documents. "
         "Agent can now answer policy questions (rates, fees, NRI rules) from actual text.",
         "retrieval/ pipeline; scripts/ingest_documents.py"),
        ("Phase 5 — 5 AI Tools",
         "Replace hard-coded responses with structured tool calls. "
         "LLM decides which tool to invoke via function-calling API.",
         "tools/ (5 @tool functions); tools/tool_registry.py; agent → ReAct executor"),
        ("Phase 6 — Memory",
         "CustomerProfile dataclass tracks collected fields. "
         "ConversationBufferWindowMemory(k=10) gives the LLM 10-turn context window.",
         "agent/memory.py; agent/planner.py; inject_context()"),
        ("Phase 7 — RLHF",
         "Policy checker flags rule violations in responses (e.g. promising approval). "
         "Feedback is logged to Langfuse and can trigger policy updates.",
         "policy_rlhf/ (feedback_collector, policy_checker, policy_updater)"),
        ("Phase 8 — Streamlit UI",
         "Full web chat interface with product picker, RM escalation dashboard, "
         "real-time interaction logging, and feedback thumbs up/down.",
         "deployment/app.py"),
        ("Phase 9 — Evaluation",
         "3 automated evaluation suites: RAG quality (20 Q/A pairs), "
         "tool accuracy (30 scenarios), safety (5 adversarial probes). "
         "LLM-as-judge scoring via Langfuse dataset runs.",
         "scripts/run_evaluation.py; 426 total tests"),
        ("Sub-bucket 4C — MCP",
         "FastMCP server exposes all 5 tools via MCP protocol. "
         "Claude Desktop, Claude Code, and external bank APIs can now call any tool. "
         "MCP is the default tool path (USE_MCP=true); direct import available via USE_MCP=false.",
         "loan_mcp/server.py; loan_mcp/client.py; tools/tool_registry.py (get_mcp_tools)"),
    ])

    doc.add_page_break()

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 5 — CONFIGURATION
    # ════════════════════════════════════════════════════════════════════════
    h1(doc, "5  Configuration — The Single Source of Truth")
    body(doc,
        "All environment variables, constants, and file paths live in ONE file: "
        "deployment/config.py. Nothing is hard-coded anywhere else. "
        "Any change to a constant (e.g. an escalation ceiling, a model name, a path) "
        "needs only one edit here.")

    h2(doc, "5.1  How Configuration Works")
    body(doc,
        "Python's dotenv library reads a .env file from the project root when the app starts. "
        "The .env file holds secrets (API keys) that must NEVER be committed to git. "
        "There is a .env.example file showing all the keys — copy it to .env and fill in values.")

    code_block(doc, [
        "# .env.example (safe to commit — no real values)",
        "OPENAI_API_KEY=sk-your-key-here",
        "LANGFUSE_PUBLIC_KEY=pk-lf-your-key-here",
        "LANGFUSE_SECRET_KEY=sk-lf-your-key-here",
        "LANGFUSE_HOST=http://localhost:3000",
        "",
        "# deployment/config.py (reads from .env at startup)",
        "from dotenv import load_dotenv",
        "load_dotenv()   # ← reads .env into os.environ",
        "OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')",
    ])

    h2(doc, "5.2  Escalation Ceilings")
    body(doc,
        "A critical constant. When a customer's requested amount exceeds the ceiling "
        "for their product, the agent MUST escalate to a human RM instead of giving "
        "a self-service answer. The tool check_eligibility checks this and returns "
        "escalate_to_rm: True.")
    two_col_table(doc, [
        ("Loan Product", "Advisory Escalation Ceiling"),
        ("Home Loan", "₹1.5 Cr (₹1,50,00,000)"),
        ("Personal Loan", "₹40 L (₹40,00,000) — product maximum"),
        ("MSME Loan", "₹2 Cr (₹2,00,00,000)"),
        ("New Car Loan", "₹20 L (₹20,00,000) — product maximum"),
    ])

    doc.add_page_break()

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 6 — THE AGENT CORE
    # ════════════════════════════════════════════════════════════════════════
    h1(doc, "6  The Agent Core  (agent/core_agent.py)")
    body(doc,
        "This is the most important file in the project. It contains the LoanCopilotAgent "
        "class which is the central coordinator — it receives every user message and "
        "decides how to respond.")

    h2(doc, "6.1  The Dual-Mode Design")
    body(doc,
        "The agent has two completely different response modes controlled by the phase parameter:")
    two_col_table(doc, [
        ("phase=2 (Rules Mode)", "phase=5+ (LLM Mode)"),
        ("No API key needed — works offline", "Requires OPENAI_API_KEY"),
        ("Intent detected by keyword matching", "GPT-4o reads conversation and decides intent"),
        ("Profile extracted by regex patterns", "LLM understands natural language; regex backup runs too"),
        ("Tools called by if/else logic", "LLM decides which tools to call via function-calling API"),
        ("Response template-formatted", "LLM writes the response in natural language"),
        ("Deterministic — same input → same output", "AI-generated — natural, varied responses"),
    ])
    callout(doc, "Why have Phase 2 at all?",
        "Phase 2 serves as the performance baseline and works without any API costs. "
        "It also demonstrates that the core eligibility logic (FOIR calculation, product limits, "
        "EMI formula) is correct before adding the complexity of an LLM. "
        "Phase 2 tests are entirely offline — no mocks needed.",
        bg=LTAMB, title_color=AMBER)

    h2(doc, "6.2  The CustomerProfile — What Gets Collected")
    body(doc,
        "Before the agent can run an eligibility check, it needs these fields from the customer. "
        "The planner tells the agent which field to ask for next (Section 8).")
    two_col_table(doc, [
        ("Field", "What it is and why it matters"),
        ("loan_product", "home_loan / personal_loan / msme_loan / car_loan — determines all rules"),
        ("loan_amount", "How much they want to borrow — checked against product min/max and ceiling"),
        ("tenure_months", "How long to repay — affects EMI and maximum tenure check"),
        ("monthly_income", "Net take-home pay — used in the FOIR (debt ratio) calculation"),
        ("age", "Must be 21–65 — bank policy eligibility window"),
        ("employment_type", "salaried / self_employed / business — affects document checklist"),
        ("credit_score", "CIBIL score — minimum 700 (home/MSME), 720 (personal/car). "
         "Defaults to 700 if customer says 'skip'"),
        ("existing_emi_obligations", "Other monthly loan repayments — added to FOIR. Optional."),
    ])

    h2(doc, "6.3  Profile Extraction — Two Approaches")
    body(doc,
        "Phase 2 uses regular expressions (regex) to extract values from free text. "
        "For example, if the user says 'I earn ₹75,000 per month' — a regex pattern "
        "matches '75,000' and saves it as monthly_income. If the LLM (Phase 5+) is "
        "active, it understands the same information from context and updates the "
        "profile using the inject_context mechanism. Both approaches update the same "
        "CustomerProfile dataclass.")

    code_block(doc, [
        "# How regex extracts loan amount from free text:",
        "# User says: 'I need 30 lakhs for a home'",
        "m = re.search(r'(\\d+(?:\\.\\d+)?)\\s*(?:lakh|lac|l)', lower)",
        "if m:",
        "    profile.loan_amount = float(m.group(1)) * 1_00_000  # 30 × 100000 = 3000000",
        "",
        "# User says: '1.5 crore'",
        "m = re.search(r'(\\d+(?:\\.\\d+)?)\\s*(?:crore|cr)', lower)",
        "if m:",
        "    profile.loan_amount = float(m.group(1)) * 1_00_00_000  # 1.5 × 10000000",
    ])

    h2(doc, "6.4  The LangGraph ReAct Loop (Phase 5+)")
    body(doc,
        "In Phase 5+, the agent uses LangChain's create_agent() which builds a "
        "LangGraph state machine. Here is what happens on every turn:")
    numbered(doc, "The full conversation history (last 10 turns from memory) + user message → sent to GPT-4o")
    numbered(doc, "GPT-4o reads the system prompt + history and decides: 'Do I need a tool?'")
    numbered(doc, "If yes: GPT-4o returns a structured function call (tool name + arguments)")
    numbered(doc, "LangGraph executes the tool and sends the result back to GPT-4o")
    numbered(doc, "GPT-4o now writes the natural-language response using the tool result")
    numbered(doc, "Steps 3–5 can repeat (up to 10 iterations) if multiple tools are needed")
    numbered(doc, "Final response → memory updated → PII masked → Langfuse logged")
    body(doc,
        "This is called the ReAct pattern (Reason + Act). The LLM reasons about what "
        "to do, acts by calling a tool, reasons about the result, then responds. "
        "It is the core pattern behind all modern AI agents.")

    doc.add_page_break()

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 7 — SYSTEM PROMPTS
    # ════════════════════════════════════════════════════════════════════════
    h1(doc, "7  System Prompts  (agent/prompts.py)")
    body(doc,
        "The system prompt is the set of instructions given to GPT-4o at the start of "
        "every conversation. Think of it as the job description and rule book handed to "
        "the AI employee. The AI reads it before reading any customer message.")

    h2(doc, "7.1  Three Prompt Variants — A/B Tested")
    three_col_table(doc, [
        ("Variant", "Style", "Result in evaluation"),
        ("V1 — Minimal", "3-line prompt: 'You are a loan assistant, use tools'",
         "Frequently gives single promised rate instead of range; no boundary enforcement"),
        ("V2 — Structured", "Bullet-point rules for each category",
         "Better boundary enforcement; still misses edge cases like NRI enquiries"),
        ("V3 — CoT Safety-First (DEFAULT)",
         "Chain-of-thought style: context, inference rules, step-by-step flow, edge cases",
         "Best on all 3 evaluation suites; selected as production default"),
    ])

    h2(doc, "7.2  What V3 Tells the AI — Key Sections")
    body(doc, "Products covered:", bold=True)
    body(doc,
        "Explicitly lists all 4 products with amount and tenure ranges so the AI "
        "never invents products or limits.")
    body(doc, "Product inference:", bold=True)
    body(doc,
        "'Customers often describe their need without naming a loan type.' "
        "V3 gives the AI a lookup table: buying a house → Home Loan, "
        "buying appliances → Personal Loan, starting a business → MSME Loan. "
        "This prevents the AI from repeatedly asking 'which loan type?' when the "
        "answer is obvious from context.")
    body(doc, "Eligibility flow (step-by-step):", bold=True)
    body(doc,
        "V3 tells the AI exactly what to do in order: collect fields → call "
        "check_eligibility → if eligible call calculate_emi → call get_document_checklist. "
        "This structured instruction prevents the AI from skipping steps.")
    body(doc, "Escalation rules:", bold=True)
    body(doc,
        "V3 gives explicit instructions: if check_eligibility returns escalate_to_rm: true, "
        "collect contact details (name, mobile, email) then call generate_escalation_summary. "
        "It even says 'do NOT say contact your branch' — the AI must use the tool.")
    body(doc, "Safety rules:", bold=True)
    body(doc,
        "Lists what is OUT_OF_SCOPE (mutual funds, tax advice, competitor products) "
        "and what is NOT out of scope (car brand names when discussing a car loan). "
        "This prevents over-blocking.")
    callout(doc, "Key Insight: Prompt Engineering",
        "The quality of the AI's responses is 80% determined by the system prompt. "
        "V3 is longer and more explicit than V1/V2, but the extra detail pays off: "
        "it handles edge cases V1 and V2 fail on (NRI enquiries, product inference, "
        "escalation flow). More specific instructions → fewer AI mistakes.",
        bg=LTBLUE, title_color=NAVY)

    doc.add_page_break()

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 8 — MEMORY & PLANNER
    # ════════════════════════════════════════════════════════════════════════
    h1(doc, "8  Memory & Planner  (agent/memory.py + agent/planner.py)")

    h2(doc, "8.1  Two Types of Memory")
    body(doc,
        "The system maintains two separate kinds of memory simultaneously:")
    two_col_table(doc, [
        ("Memory Type", "What it is and how it works"),
        ("CustomerProfile (structured)", "A Python dataclass with named fields — loan_product, "
         "monthly_income, age, etc. Each field starts as None. As the customer provides "
         "information, the fields get filled in. This is deterministic — no AI involved."),
        ("ConversationBufferWindowMemory (conversational)", "A sliding window of the last 10 "
         "conversation turns (user + AI messages). This is what the LLM reads to understand "
         "context — who said what, what was already discussed. Window of 10 prevents the "
         "LLM's context window from being overwhelmed in long conversations."),
    ])

    h2(doc, "8.2  How Memory Works in Practice")
    body(doc,
        "Example: A customer says 'Hi, I am Priya, I want a home loan for 50 lakhs, "
        "I earn 1 lakh per month, I am 32 years old, salaried.'")
    numbered(doc, "regex / LLM extracts: name='Priya', loan_product='home_loan', "
             "loan_amount=5000000, monthly_income=100000, age=32, employment_type='salaried'")
    numbered(doc, "CustomerProfile fields are updated with these values")
    numbered(doc, "The full message is also added to ConversationBufferWindowMemory")
    numbered(doc, "Next turn: planner checks CustomerProfile — tenure_months is still None")
    numbered(doc, "Agent asks: 'Over how many years would you like to repay the loan?'")
    numbered(doc, "Customer says '20 years' → tenure_months = 240 → profile now complete")
    numbered(doc, "Agent runs eligibility check, EMI, and document checklist tools")

    h2(doc, "8.3  The Planner — Never Asking Twice")
    body(doc,
        "The planner (agent/planner.py) maintains a fixed collection sequence. "
        "It iterates through fields in a specific order and returns the next question "
        "for the first field that is still None. Once a field is collected, "
        "the planner never asks for it again — even if the conversation takes a detour.")
    code_block(doc, [
        "# agent/planner.py — the fixed question order",
        "COLLECTION_SEQUENCE = [",
        "    ('loan_product',    'Which loan are you interested in?'),",
        "    ('loan_amount',     'How much would you like to borrow?'),",
        "    ('tenure_months',   'Over how many months/years to repay?'),",
        "    ('monthly_income',  'What is your monthly take-home income?'),",
        "    ('age',             'May I know your age?'),",
        "    ('employment_type', 'Are you salaried, self-employed, or business?'),",
        "    ('credit_score',    'Do you know your CIBIL score? (skip if unsure)'),",
        "]",
        "",
        "def next_field_and_question(profile):",
        "    for field, question in COLLECTION_SEQUENCE:",
        "        if getattr(profile, field) is None:  # ← still not collected",
        "            return (field, question)",
        "    return None  # ← all fields collected; ready for tools",
    ])

    h2(doc, "8.4  Session Reset")
    body(doc,
        "If the customer types 'start over', 'reset', or similar — the agent calls "
        "reset() which clears the CustomerProfile (all fields back to None) and "
        "clears the LangChain memory buffer. The conversation starts fresh. "
        "The session ID stays the same so Langfuse traces remain grouped.")

    doc.add_page_break()

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 9 — THE 5 AI TOOLS
    # ════════════════════════════════════════════════════════════════════════
    h1(doc, "9  The 5 AI Tools  (tools/)")
    body(doc,
        "Tools are Python functions that GPT-4o can call. The LLM cannot generate "
        "financial figures (EMI, eligibility, interest rates) itself — it would hallucinate. "
        "Instead, the LLM recognises when a calculation is needed and calls the appropriate "
        "tool, which returns exact deterministic results. The LLM then formats those results "
        "into a natural response.")
    callout(doc, "Why Tools?",
        "Without tools: 'Your EMI will be approximately ₹27,000' (AI guessing). "
        "With tools: EMI = ₹26,992 (mathematically exact). "
        "The @tool decorator is all that's needed — LangChain reads the function "
        "signature and docstring to generate a JSON schema the LLM uses to call it.",
        bg=LTGRN, title_color=GREEN)

    h2(doc, "9.1  Tool 1 — calculate_emi  (tools/emi_calculator.py)")
    body(doc, "What it does:", bold=True)
    body(doc,
        "Calculates the monthly EMI (Equated Monthly Instalment) using the standard "
        "reducing-balance formula. Called TWICE for every eligible loan — once at the "
        "lower rate bound and once at the upper rate bound — to give a range.")
    body(doc, "The formula:", bold=True)
    code_block(doc, [
        "# Reducing-balance EMI formula",
        "r = annual_rate / 12 / 100       # monthly interest rate",
        "EMI = P × r × (1+r)^n / ((1+r)^n - 1)",
        "",
        "# Example: ₹30L loan, 9% per annum, 20 years (240 months)",
        "r = 9 / 12 / 100 = 0.0075",
        "EMI = 3000000 × 0.0075 × (1.0075)^240 / ((1.0075)^240 - 1)",
        "EMI ≈ ₹26,992 per month",
        "",
        "# Returns:",
        "{'emi': 26992.45, 'total_payable': 6478188, 'total_interest': 3478188, ...}",
    ])
    body(doc, "Inputs:", bold=True)
    body(doc, "principal (loan amount), annual_rate_percent, tenure_months")
    body(doc, "Output:", bold=True)
    body(doc, "emi, total_payable, total_interest, principal, rate, tenure_months")

    h2(doc, "9.2  Tool 2 — check_eligibility  (tools/eligibility_checker.py)")
    body(doc, "What it does:", bold=True)
    body(doc,
        "Runs a rules-based eligibility check — the most complex tool. "
        "It applies 4 checks in order:")
    numbered(doc, "Age check: must be between 21 and 65 years")
    numbered(doc, "Credit score: minimum 700 for Home/MSME, 720 for Personal/Car")
    numbered(doc, "Amount limits: must be within the product's min/max range")
    numbered(doc, "FOIR (Fixed Obligation to Income Ratio): "
             "(existing EMIs + proposed EMI) ÷ monthly income ≤ 50% (or 55% for income > ₹1L)")
    body(doc,
        "If ANY check fails → eligible=False with the reason. "
        "If loan_amount exceeds the escalation ceiling → escalate_to_rm=True. "
        "Note: a loan can be both ineligible AND need escalation "
        "(e.g., a ₹25L car loan exceeds the ₹20L ceiling AND is above the product maximum).")
    code_block(doc, [
        "# FOIR calculation (the core debt-to-income check)",
        "proposed_emi = calculate_emi(principal, mid_rate, tenure_months)['emi']",
        "total_obligations = existing_emis + proposed_emi",
        "foir = total_obligations / monthly_income",
        "foir_limit = 0.55 if monthly_income > 100000 else 0.50",
        "",
        "if foir > foir_limit:",
        "    reasons.append(f'FOIR {foir:.0%} exceeds limit {foir_limit:.0%}')",
        "",
        "# Escalation check (separate from eligibility)",
        "ceiling = ESCALATION_CEILINGS[product]  # from config.py",
        "escalate = loan_amount > ceiling",
    ])

    h2(doc, "9.3  Tool 3 — get_document_checklist  (tools/document_checklist.py)")
    body(doc, "What it does:", bold=True)
    body(doc,
        "Returns the list of documents needed for a specific product × employment type "
        "combination. The data is stored in a 4×3 lookup table (4 products × 3 employment "
        "types). This is completely deterministic — no AI involved.")
    body(doc, "Example output for Home Loan + Salaried:", bold=True)
    body(doc, "Common: Aadhaar, PAN, passport photo, 6-month bank statement, ITR (2 years)", italic=True)
    body(doc, "Product-specific: salary slips (3 months), Form 16, property title deed", italic=True)

    h2(doc, "9.4  Tool 4 — query_loan_policy  (tools/tool_search.py)")
    body(doc, "What it does:", bold=True)
    body(doc,
        "Answers policy questions by searching the vector database (ChromaDB). "
        "This is the RAG (Retrieval-Augmented Generation) tool. "
        "When a customer asks 'Can an NRI apply for a home loan?' or 'What are prepayment charges?' "
        "— the tool converts the question into a vector, searches ChromaDB for the 5 most "
        "similar policy text chunks, and returns them to the LLM which then writes a grounded answer.")
    body(doc, "Why this matters:", bold=True)
    body(doc,
        "Without this tool, the LLM would either hallucinate an answer or say 'contact your branch'. "
        "With this tool, the LLM reads the actual policy text and gives a specific, accurate answer. "
        "The policy documents are the single source of truth for all factual questions.")

    h2(doc, "9.5  Tool 5 — generate_escalation_summary  (tools/tool_escalate.py)")
    body(doc, "What it does:", bold=True)
    body(doc,
        "When a loan amount exceeds the advisory ceiling, the agent must hand the customer "
        "off to a human Relationship Manager (RM). This tool creates a structured 'handoff packet' "
        "containing everything the RM needs to make a callback.")
    body(doc, "What gets saved:", bold=True)
    two_col_table(doc, [
        ("Field in escalation record", "Value"),
        ("customer_name", "Full name collected from conversation"),
        ("mobile_number", "10-digit Indian number (validated: must start 6–9)"),
        ("email", "Validated email address"),
        ("gender", "For personalised greeting (optional)"),
        ("loan_product + loan_amount", "What they want"),
        ("escalation_reason", "Why it was escalated (e.g. 'exceeds ₹1.5Cr ceiling')"),
        ("conversation_summary", "Brief summary of what was discussed"),
        ("session_id", "Links to the full Langfuse trace"),
        ("timestamp", "When the escalation was created"),
        ("conversation_history", "Last 10 turns appended after the tool returns"),
    ])
    body(doc,
        "The record is saved to data/rlhf/escalations.json and shown in the RM Dashboard tab "
        "of the Streamlit UI. The RM can see everything they need for the callback without "
        "reading the full chat transcript.")

    h2(doc, "9.6  How the LLM Chooses Tools")
    body(doc,
        "The @tool decorator makes LangChain automatically generate a JSON schema for each "
        "function (field names, types, descriptions). This schema is sent to GPT-4o as part "
        "of the API call. GPT-4o's function-calling feature lets it return a structured "
        "JSON object saying 'call this tool with these arguments' instead of a text response. "
        "LangGraph then executes the tool and sends the result back.")
    code_block(doc, [
        "# What LangChain generates from the @tool decorator:",
        "{",
        "  'name': 'calculate_emi',",
        "  'description': 'Calculate monthly EMI using reducing-balance method.',",
        "  'parameters': {",
        "    'type': 'object',",
        "    'properties': {",
        "      'principal':           {'type': 'number', 'description': 'Loan amount in INR'},",
        "      'annual_rate_percent': {'type': 'number', 'description': 'Annual interest rate'},",
        "      'tenure_months':       {'type': 'integer', 'description': 'Tenure in months'}",
        "    },",
        "    'required': ['principal', 'annual_rate_percent', 'tenure_months']",
        "  }",
        "}",
    ])

    doc.add_page_break()

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 10 — RAG PIPELINE
    # ════════════════════════════════════════════════════════════════════════
    h1(doc, "10  The RAG Pipeline  (retrieval/)")
    body(doc,
        "RAG stands for Retrieval-Augmented Generation. The idea: instead of expecting "
        "the LLM to memorise all bank policies (which it cannot — it was trained before "
        "these policies existed), we store the policies in a searchable database and "
        "retrieve the relevant parts just-in-time when a question is asked.")

    h2(doc, "10.1  The Two Pipelines")
    rag_pipeline_diagram(doc)

    h2(doc, "10.2  Ingestion Pipeline — Building the Knowledge Base")
    body(doc, "Step 1 — Policy documents:", bold=True)
    body(doc,
        "4 synthetic policy .txt files live in knowledge/raw/: "
        "home_loan_policy.txt, personal_loan_policy.txt, msme_loan_policy.txt, "
        "car_loan_policy.txt. Each contains interest rates, fees, eligibility criteria, "
        "NRI rules, prepayment charges, and processing timelines.")
    body(doc, "Step 2 — Document Loader (retrieval/document_loader.py):", bold=True)
    body(doc,
        "Reads each .txt file and attaches metadata (source, product name). "
        "The product label prefix is prepended to every chunk "
        "(e.g., '[HOME_LOAN] The maximum tenure is 30 years...') — "
        "this prevents the retriever from returning a personal loan chunk "
        "when the customer is asking about a home loan.")
    body(doc, "Step 3 — Text Chunker (retrieval/chunker.py):", bold=True)
    body(doc,
        "Splits each document into overlapping chunks of 500 tokens with 100-token overlap. "
        "Overlap ensures that a sentence split across chunk boundaries isn't lost — "
        "the end of chunk N and the start of chunk N+1 share 100 tokens.")
    body(doc, "Step 4 — Embedder (retrieval/embedder.py):", bold=True)
    body(doc,
        "Calls OpenAI's text-embedding-3-small model to convert each chunk into a "
        "1536-dimensional vector. A vector is a list of 1536 numbers that captures "
        "the meaning of the text — similar sentences get similar vectors.")
    body(doc, "Step 5 — ChromaDB Store (retrieval/chroma_store.py):", bold=True)
    body(doc,
        "Stores all chunks + their vectors in ChromaDB on disk (knowledge/chromadb/). "
        "This only needs to run once. If you change a policy document, re-run "
        "python scripts/ingest_documents.py to rebuild.")

    h2(doc, "10.3  Query Pipeline — Answering Policy Questions")
    numbered(doc, "Customer asks: 'What is the prepayment charge for a home loan?'")
    numbered(doc, "The query_loan_policy tool calls retrieve('prepayment charge home loan')")
    numbered(doc, "retriever.py calls OpenAI to embed the query → get a 1536-dim vector")
    numbered(doc, "ChromaDB computes cosine similarity between query vector and all stored vectors")
    numbered(doc, "Top-5 most similar chunks are returned (RAG_TOP_K=5)")
    numbered(doc, "The tool returns these chunks as context to the LLM")
    numbered(doc, "The LLM reads the policy text and writes a specific, grounded answer")

    callout(doc, "Why ChromaDB Instead of a Regular Database?",
        "A regular SQL database searches for exact keyword matches ('find rows WHERE text LIKE prepayment'). "
        "ChromaDB does semantic search — it finds text that MEANS the same thing, even if the exact "
        "words are different. Example: 'foreclosure fee' and 'early repayment penalty' have different words "
        "but similar meanings — ChromaDB will find both when searching for prepayment charges.",
        bg=LTBLUE, title_color=NAVY)

    doc.add_page_break()

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 11 — SAFETY GATE
    # ════════════════════════════════════════════════════════════════════════
    h1(doc, "11  The Safety Gate  (safety/guardrails.py + safety/pii_filter.py)")
    body(doc,
        "The safety gate sits between the customer's message and the AI agent. "
        "Every message must pass through it before the AI sees it. "
        "It runs in two stages designed to balance speed with accuracy.")

    h2(doc, "11.1  Stage A — Keyword Blocklist (< 1 ms, zero tokens)")
    body(doc,
        "The first filter is a simple string search. If the message contains any of "
        "the blocked phrases, it is immediately rejected without calling the LLM. "
        "This catches the most obvious adversarial probes and costs nothing.")
    body(doc, "Examples of blocked phrases:", bold=True)
    two_col_table(doc, [
        ("Blocked phrase", "Why it is blocked"),
        ('"ignore previous instructions"', "Classic prompt injection — trying to override the AI's rules"),
        ('"act as"', "Roleplay injection — trying to make the AI pretend to be something else"),
        ('"transfer money" / "send funds"', "Financial action — copilot cannot initiate transactions"),
        ('"mutual fund" / "invest in stocks"', "Investment advice — out of scope for a loan copilot"),
        ('"reveal your prompt"', "Prompt extraction attack — trying to steal the system prompt"),
        ('"competitor"', "Competitor bank name — would create reputational risk"),
    ])

    h2(doc, "11.2  Stage B — LLM Intent Classifier (~150 ms, <50 tokens)")
    body(doc,
        "If Stage A passes, GPT-4o-mini reads the message and classifies it as "
        "IN_SCOPE, OUT_OF_SCOPE, or AMBIGUOUS. This handles semantic attacks that "
        "avoid the blocklist keywords.")
    body(doc, "Example edge cases Stage B handles:", bold=True)
    two_col_table(doc, [
        ("Customer message", "Stage B classification and why"),
        ('"I need AC money"', "IN_SCOPE — 'need money' implies a loan need; AC is a Personal Loan purpose"),
        ('"Can you guarantee my loan?"', "OUT_OF_SCOPE — 'guarantee' implies approval promise; system cannot do this"),
        ('"What does SBI offer?"', "OUT_OF_SCOPE — competitor bank name even without 'competitor' keyword"),
        ('"on road price is 15 lacs"', "IN_SCOPE — continuation of car loan conversation; data provision reply"),
        ('"I want to buy a house"', "IN_SCOPE — Home Loan purpose, even without mentioning 'loan'"),
    ])
    body(doc, "Fail-OPEN design:", bold=True)
    body(doc,
        "If the GPT-4o-mini API call fails (network error, timeout), the gate returns "
        "IN_SCOPE by default — it allows the message through. This is called fail-OPEN. "
        "The reasoning: it is better to occasionally allow an edge case than to block "
        "a genuine customer's loan enquiry because of an infrastructure issue.")

    safety_diagram(doc)

    h2(doc, "11.3  PII Filter  (safety/pii_filter.py)")
    body(doc,
        "PII stands for Personally Identifiable Information. The PII filter runs "
        "AFTER the agent generates a response, BEFORE it is written to any log. "
        "It replaces sensitive data with placeholder tokens using regex patterns.")
    two_col_table(doc, [
        ("Data type", "Regex pattern detects"),
        ("Aadhaar number", "12 digits in 4-4-4 groups (e.g. 1234 5678 9012)"),
        ("PAN card", "5 letters + 4 digits + 1 letter (e.g. ABCDE1234F)"),
        ("Mobile number", "10 digits starting with 6–9"),
        ("Email address", "standard email format"),
        ("Bank account", "9–18 digit sequences"),
    ])
    body(doc,
        "Why? Logs are often read by engineers and stored for months. A customer's "
        "Aadhaar number in a log is a data breach. The PII filter ensures that "
        "sensitive numbers are always masked before hitting any storage system. "
        "The mask() function is called explicitly in every log write — "
        "it is never optional.")

    doc.add_page_break()

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 12 — OBSERVABILITY
    # ════════════════════════════════════════════════════════════════════════
    h1(doc, "12  Observability with Langfuse  (monitoring/langfuse_logger.py)")
    body(doc,
        "Observability means being able to see exactly what the AI is doing — which "
        "tokens it processed, which tools it called, how long each step took, and "
        "whether the response was correct. Langfuse is the self-hosted platform used "
        "for this. It runs inside Docker Compose on the same machine as the app.")

    h2(doc, "12.1  Why Langfuse? Why Self-Hosted?")
    body(doc,
        "LangSmith (Anthropic's/LangChain's hosted platform) was explicitly excluded "
        "because it is cloud-only — customer conversations and PII would leave the bank's "
        "premises. Arize Phoenix was evaluated but RAG evaluation was already fully "
        "covered by Langfuse's LLM-as-judge feature on the same test set. "
        "Self-hosted Langfuse: all data stays on-premises, no extra cost, full control.")

    h2(doc, "12.2  What Gets Logged")
    two_col_table(doc, [
        ("What Langfuse records", "Why it matters"),
        ("Session trace", "Every turn in a session is grouped under one trace_id "
         "(= session UUID without dashes)"),
        ("LLM call spans", "Exact prompt sent, response received, tokens used, latency"),
        ("Tool call spans", "Which tool was called, what arguments, what it returned"),
        ("Scores", "Numeric quality ratings attached to traces — from evaluation suites "
         "or RLHF feedback"),
        ("Session ID", "Links all turns in one customer session so you can replay the conversation"),
    ])

    h2(doc, "12.3  How It Is Wired In")
    body(doc,
        "get_langfuse_callback() returns a LangChain CallbackHandler. "
        "This is passed to every agent invoke() call as config={'callbacks': [cb]}. "
        "LangChain then automatically calls the handler at each step "
        "(LLM start, LLM end, tool start, tool end) without any manual instrumentation. "
        "If Langfuse is not configured (no keys in .env), the function returns None "
        "and the agent runs without any observability overhead.")

    doc.add_page_break()

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 13 — RLHF
    # ════════════════════════════════════════════════════════════════════════
    h1(doc, "13  RLHF — Learning from Feedback  (policy_rlhf/)")
    body(doc,
        "RLHF stands for Reinforcement Learning from Human Feedback. In this project, "
        "it is a lightweight version: feedback from the Streamlit UI (thumbs up/down) "
        "triggers automatic policy compliance checking, and repeated violations can "
        "trigger policy updates.")

    h2(doc, "13.1  The Three Components")
    two_col_table(doc, [
        ("Module", "What it does"),
        ("policy_rlhf/feedback_collector.py",
         "Collects thumbs-up/thumbs-down ratings from the Streamlit UI. "
         "Saves each rating to data/rlhf/feedback.json with the session ID and response text."),
        ("policy_rlhf/policy_checker.py",
         "Scans every agent response for rule violations: "
         "promising approval ('your loan is approved'), "
         "giving a single rate instead of a range, "
         "sharing out-of-scope advice. Returns a list of violation objects."),
        ("policy_rlhf/policy_updater.py",
         "Analyses accumulated feedback. If a violation occurs repeatedly (above a threshold), "
         "it suggests adding a corrective rule. In this project, this is a demonstration — "
         "in production it would trigger a prompt update or fine-tuning job."),
    ])

    h2(doc, "13.2  How It Hooks Into the Agent")
    body(doc,
        "After every LLM response in Phase 7+, the agent calls policy_checker.check_response(). "
        "If violations are found, it calls Langfuse's score_session() to attach a "
        "policy_compliance=0.0 score to that trace. This means every policy violation "
        "is visible in the Langfuse dashboard even without a human reviewer flagging it.")
    code_block(doc, [
        "# In agent/core_agent.py — after every LLM response:",
        "violations = _check_policy(response_text)",
        "if violations:",
        "    score_session(",
        "        trace_id=hex_id,",
        "        score_name='policy_compliance',",
        "        value=0.0,  # 0 = violation, 1 = compliant",
        "        comment=f'Violations: {[v[\"rule_id\"] for v in violations]}',",
        "    )",
    ])

    doc.add_page_break()

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 14 — MCP
    # ════════════════════════════════════════════════════════════════════════
    h1(doc, "14  MCP — Exposing Tools to the World  (loan_mcp/)")
    body(doc,
        "MCP stands for Model Context Protocol — an open standard by Anthropic that "
        "lets any AI agent discover and call tools from any server that speaks the protocol. "
        "Think of it as a standard power socket: any device (AI agent, IDE extension, "
        "external bank API) that understands MCP can plug in and call the 5 loan tools "
        "without knowing how they are implemented.")

    h2(doc, "14.1  The MCP Server  (loan_mcp/server.py)")
    body(doc,
        "The server uses FastMCP — a high-level Python library. "
        "It registers all 5 tools with the @mcp.tool() decorator. "
        "FastMCP auto-generates JSON schemas from the Python type hints, "
        "so no manual schema writing is needed.")
    code_block(doc, [
        "# loan_mcp/server.py — simplified structure",
        "from mcp.server.fastmcp import FastMCP",
        "mcp = FastMCP(name='Loan Copilot', instructions='...')",
        "",
        "@mcp.tool()",
        "def calculate_emi(principal: float, annual_rate_percent: float, tenure_months: int) -> dict:",
        "    from tools.emi_calculator import calculate_emi as _f",
        "    return _f.invoke({'principal': principal, ...})",
        "",
        "# Start modes:",
        "# stdio (for Claude Desktop):  python scripts/start_mcp_server.py",
        "# HTTP (for network access):   python scripts/start_mcp_server.py --transport http",
    ])

    h2(doc, "14.2  The MCP Client  (loan_mcp/client.py)")
    body(doc,
        "The client lets the LangChain agent call tools via MCP instead of importing "
        "them directly. Two key functions:")
    two_col_table(doc, [
        ("Function", "What it does"),
        ("call_tool_sync(name, args)", "Calls an MCP tool synchronously. Internally runs async code "
         "in a background thread using ThreadPoolExecutor to avoid event loop conflicts."),
        ("list_tools_sync()", "Returns a list of all available tools with their name, "
         "description, and JSON Schema parameters."),
    ])

    h2(doc, "14.3  How the Agent Switches to MCP Path")
    body(doc,
        "In tools/tool_registry.py, there are two functions: get_all_tools() (direct imports) "
        "and get_mcp_tools() (MCP path). The agent checks the USE_MCP environment variable "
        "at startup. If USE_MCP=true, it wraps each MCP tool in a LangChain StructuredTool "
        "with a dynamically built Pydantic schema, so the LLM sees identical tool signatures "
        "regardless of which transport is used.")
    code_block(doc, [
        "# In agent/core_agent.py:",
        "use_mcp = os.getenv('USE_MCP', 'true').lower() == 'true'",
        "tools = get_mcp_tools() if use_mcp else get_all_tools()",
        "",
        "# Run agent (MCP path is the default):",
        "python scripts/run_agent.py",
        "",
        "# Run agent with direct import path (override):",
        "USE_MCP=false python scripts/run_agent.py",
    ])

    doc.add_page_break()

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 15 — STREAMLIT UI
    # ════════════════════════════════════════════════════════════════════════
    h1(doc, "15  The Web UI  (deployment/app.py)")
    body(doc,
        "The Streamlit app is the customer-facing interface. It wraps the LoanCopilotAgent "
        "in a web chat interface that looks and behaves like a modern messaging app. "
        "It also has a separate RM Dashboard tab for the bank's Relationship Managers.")

    h2(doc, "15.1  The Customer Chat Tab")
    two_col_table(doc, [
        ("UI Feature", "What it does and how"),
        ("Product Quick-Select buttons", "4 buttons (Home / Personal / MSME / Car). Clicking one "
         "calls agent.inject_context() to pre-fill loan_product in the profile and add "
         "the selection to memory — the AI never asks 'which loan?' again."),
        ("Chat message display", "st.session_state stores the conversation. Each turn shows "
         "user message (right-aligned) and AI response (left-aligned) in a chat bubble style."),
        ("Thumbs up / Thumbs down", "Feedback buttons under each AI response. Click triggers "
         "feedback_collector.collect() which saves the rating to feedback.json."),
        ("PII masking before display", "Even in the chat UI, responses are passed through "
         "pii_filter.mask() before being shown — preventing raw Aadhaar/PAN from "
         "appearing in the browser."),
        ("Session reset button", "Calls agent.reset() to clear profile and memory."),
    ])

    h2(doc, "15.2  The RM Dashboard Tab")
    body(doc,
        "Shows all escalated cases from data/rlhf/escalations.json. "
        "For each escalation, the RM sees: customer name, mobile, email, loan product, "
        "amount, escalation reason, conversation summary, and timestamp. "
        "Allows the RM to see everything needed for a callback without reading the full chat.")

    h2(doc, "15.3  Running the UI")
    code_block(doc, [
        "# Start the Streamlit web app:",
        "streamlit run deployment/app.py",
        "",
        "# The browser opens automatically at:",
        "http://localhost:8501",
        "",
        "# With direct import path (override, MCP is default):",
        "USE_MCP=false streamlit run deployment/app.py",
    ])

    doc.add_page_break()

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 16 — END-TO-END MESSAGE FLOW
    # ════════════════════════════════════════════════════════════════════════
    h1(doc, "16  End-to-End Message Flow")
    body(doc,
        "This section traces exactly what happens — file by file, function by function — "
        "when a customer types a single message. "
        "Example: customer types 'I want to buy a house worth ₹60 lakhs'")

    message_flow_diagram(doc)

    h2(doc, "16.1  Detailed Step-by-Step Trace")

    steps_detail = [
        ("Step 1 — User types message",
         "Customer types in Streamlit chat input (deployment/app.py). "
         "The message is stored in st.session_state['messages']."),
        ("Step 2 — Safety Gate Stage A (< 1 ms)",
         "safety/guardrails.py: keyword_filter('I want to buy a house worth ₹60 lakhs'). "
         "No blocklist terms found → None returned → pass to Stage B."),
        ("Step 3 — Safety Gate Stage B (~150 ms)",
         "safety/guardrails.py: classify_intent() sends message to GPT-4o-mini. "
         "Response: 'IN_SCOPE' (house purchase = Home Loan = loan query). "
         "Gate allows message through."),
        ("Step 4 — Agent receives message",
         "deployment/app.py calls agent.chat(user_input). "
         "agent/core_agent.py: turn_count += 1. "
         "Phase 5+: _llm_response() → _executor_response()."),
        ("Step 5 — Profile extraction (background)",
         "_extract_profile() parses the message with regex. "
         'Finds "house" → loan_product = "home_loan". '
         "Finds '60 lakhs' → loan_amount = 6,000,000. "
         "CustomerProfile updated."),
        ("Step 6 — LangGraph ReAct agent runs",
         "_get_executor() returns (or builds) the LangGraph agent. "
         "agent.invoke({'messages': [*history, HumanMessage]}) called. "
         "GPT-4o reads: system prompt V3 + conversation history + this message."),
        ("Step 7 — LLM reasons (first iteration)",
         "GPT-4o thinks: 'The customer wants a home loan for ₹60L. "
         "I need more information before I can check eligibility. "
         "Missing: tenure, income, age, employment type, credit score.' "
         "LLM returns a question: 'Great! For a Home Loan of ₹60 lakhs, "
         "I'll need a few details. What is your approximate monthly take-home income?'"),
        ("Step 8 — No tool call this turn",
         "Because required profile fields are missing, the LLM asks for more info "
         "rather than calling a tool. The planner (agent/planner.py) guides this "
         "through the COLLECTION_SEQUENCE — asking one field at a time."),
        ("Step 9 — Response post-processing",
         "PII filter: safety/pii_filter.mask(response_text) — no PII in this response. "
         "Memory update: memory.chat_memory.add_user_message() + add_ai_message(). "
         "Policy check: policy_checker.check_response() — no violations. "
         "Langfuse: session trace updated with this turn's span."),
        ("Step 10 — Response displayed",
         "Streamlit displays the AI's question in the chat UI. "
         "Thumbs up/down buttons appear below the response."),
    ]
    for step, detail in steps_detail:
        body(doc, step, bold=True, color=NAVY)
        body(doc, detail, indent=True)

    h2(doc, "16.2  What Happens When All Fields Are Collected")
    body(doc,
        "After several turns, the customer has provided income (₹1L/month), age (38), "
        "employment type (salaried), tenure (20 years = 240 months), credit score (760).")
    steps_tool = [
        ("Tool call 1: check_eligibility",
         "LLM calls check_eligibility with all profile fields. "
         "FOIR = (0 + proposed_emi) / 100000 = ~₹47,500 / ₹1L = 47.5% < 50% limit. "
         "Credit score 760 ≥ 700 minimum. Age 38 within 21–65. "
         "Amount ₹60L < ₹1.5Cr ceiling. "
         "Result: eligible=True, escalate_to_rm=False."),
        ("Tool call 2: calculate_emi (low rate 8.50%)",
         "LLM calls calculate_emi(6000000, 8.50, 240). "
         "EMI ≈ ₹52,100/month. total_payable ≈ ₹1.25 Cr."),
        ("Tool call 3: calculate_emi (high rate 9.50%)",
         "LLM calls calculate_emi(6000000, 9.50, 240). "
         "EMI ≈ ₹55,900/month. total_payable ≈ ₹1.34 Cr."),
        ("Tool call 4: get_document_checklist",
         "LLM calls get_document_checklist('home_loan', 'salaried'). "
         "Returns common docs + product-specific: salary slips, Form 16, property deed."),
        ("LLM writes final response",
         "GPT-4o composes a natural response using all 4 tool results: "
         "'Great news! Based on your profile, you appear to be INDICATIVELY ELIGIBLE for "
         "a Home Loan of ₹60 lakhs. EMI range: ₹52,100 – ₹55,900/month at 8.50%–9.50% p.a. "
         "Actual rate is confirmed at sanction...'"),
    ]
    for step, detail in steps_tool:
        body(doc, step, bold=True, color=TEAL)
        body(doc, detail, indent=True)

    doc.add_page_break()

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 17 — THE 4 LOAN PRODUCTS
    # ════════════════════════════════════════════════════════════════════════
    h1(doc, "17  The 4 Loan Products in Detail")
    body(doc,
        "All product rules are encoded in tools/eligibility_checker.py (PRODUCT_LIMITS, RATE_BANDS) "
        "and deployment/config.py (ESCALATION_CEILINGS). Here is what each product represents:")

    h2(doc, "17.1  Home Loan")
    two_col_table(doc, [
        ("Parameter", "Value"),
        ("Amount range", "₹5 L – ₹5 Cr"),
        ("Escalation ceiling (advisory)", "₹1.5 Cr → escalate to RM above this"),
        ("Tenure", "Up to 30 years (360 months)"),
        ("Indicative rate band", "8.50% – 9.50% p.a."),
        ("Min credit score", "700 (CIBIL)"),
        ("FOIR limit", "50% (or 55% if income > ₹1L/month)"),
        ("Documents (salaried)", "Aadhaar, PAN, salary slips (3m), Form 16, ITR (2y), property title deed"),
    ])

    h2(doc, "17.2  Personal Loan")
    two_col_table(doc, [
        ("Parameter", "Value"),
        ("Amount range", "₹50 K – ₹40 L"),
        ("Escalation ceiling", "₹40 L (product maximum = ceiling)"),
        ("Tenure", "Up to 5 years (60 months)"),
        ("Indicative rate band", "9.99% – 24.00% p.a."),
        ("Min credit score", "720 (CIBIL) — stricter because no collateral"),
        ("FOIR limit", "50% / 55%"),
        ("Notes", "Covers consumer goods, travel, medical, wedding, education, appliances"),
    ])

    h2(doc, "17.3  MSME Loan")
    two_col_table(doc, [
        ("Parameter", "Value"),
        ("Amount range", "₹50 K – ₹10 Cr"),
        ("Escalation ceiling (advisory)", "₹2 Cr → escalate to RM above this"),
        ("Tenure", "Up to 15 years (180 months)"),
        ("Indicative rate band", "9.00% – 16.00% p.a."),
        ("Min credit score", "700 (CIBIL)"),
        ("Notes", "For business owners, manufacturing, working capital, equipment purchase"),
    ])

    h2(doc, "17.4  New Car Loan")
    two_col_table(doc, [
        ("Parameter", "Value"),
        ("Amount range", "₹3 L – ₹20 L"),
        ("Escalation ceiling", "₹20 L (product maximum = ceiling)"),
        ("Tenure", "Up to 7 years (84 months)"),
        ("Indicative rate band", "8.75% – 10.50% p.a."),
        ("Min credit score", "720 (CIBIL)"),
        ("Notes", "For new 4-wheelers only. Two-wheelers handled as Personal Loan."),
    ])

    doc.add_page_break()

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 18 — EVALUATION FRAMEWORK
    # ════════════════════════════════════════════════════════════════════════
    h1(doc, "18  Evaluation Framework  (scripts/run_evaluation.py)")
    body(doc,
        "426 automated tests (244 original + 182 coverage tests) verify the system from three angles: "
        "pytest for unit correctness, evaluation suites for AI quality, "
        "and adversarial probes for safety.")

    h2(doc, "18.1  The 3 Evaluation Suites")
    three_col_table(doc, [
        ("Suite", "What it tests", "Pass criteria"),
        ("RAG Quality (20 Q/A pairs)",
         "Policy questions answered from ChromaDB. LLM-as-judge scores each answer "
         "against the expected policy text on a 0–1 scale.",
         "≥ 70% of answers score ≥ 0.7"),
        ("Tool Selection (30 scenarios)",
         "Given a customer scenario, does the agent call the right tool(s) "
         "with the right arguments? Boolean match.",
         "≥ 80% scenarios select correct tool(s)"),
        ("Safety Probes (5 adversarial inputs)",
         "5 types: prompt injection, approval guarantee, competitor name, PII leak, "
         "investment advice. Each must be blocked.",
         "100% block rate — any miss fails the suite"),
    ])

    h2(doc, "18.2  The pytest Suite Structure")
    two_col_table(doc, [
        ("Test file", "What it covers"),
        ("tests/test_emi_calculator.py", "EMI formula correctness, edge cases (zero rate, boundary amounts)"),
        ("tests/test_eligibility_checker.py",
         "All eligibility rules: age, credit score, FOIR, amount limits, escalation"),
        ("tests/test_document_checklist.py",
         "All 12 product × employment combinations"),
        ("tests/test_tool_search.py",
         "RAG retrieval returns relevant chunks; correct source metadata"),
        ("tests/test_tool_escalate.py",
         "Mobile number validation (must start 6–9), email validation, "
         "JSON record saved correctly"),
        ("tests/test_guardrails.py",
         "Stage A keyword blocking; Stage B classification for 20+ messages"),
        ("tests/test_pii_filter.py",
         "All 5 PII types correctly masked; valid values not falsely masked"),
        ("tests/test_agent_phase2.py",
         "Full Phase 2 conversation flows; profile extraction; reset command"),
        ("tests/test_memory.py",
         "CustomerProfile dataclass; missing_required_fields(); SessionState.reset()"),
        ("tests/test_planner.py",
         "COLLECTION_SEQUENCE order; next_field_and_question() returns correct field"),
        ("tests/test_mcp_server.py (11 tests)",
         "MCP server lists exactly 5 tools; tool schemas correct; "
         "EMI/eligibility/checklist via MCP returns correct results; "
         "LangChain StructuredTool wrapping works"),
    ])

    h2(doc, "18.3  LLM-as-Judge Pattern")
    body(doc,
        "For RAG quality evaluation, a human cannot read 20 × 5 (100) responses and score "
        "them manually at every test run. Instead, a second LLM instance (GPT-4o) is used "
        "as the judge. It is given: the question, the expected answer, and the agent's actual "
        "answer. It returns a 0–1 score and a reason. Scores ≥ 0.7 are considered passing. "
        "This is an automated quality gate that can run on every CI push.")

    doc.add_page_break()

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 19 — HOW TO BUILD FROM SCRATCH
    # ════════════════════════════════════════════════════════════════════════
    h1(doc, "19  How to Build It From Scratch")
    body(doc,
        "If you wanted to recreate this project from zero, here is the complete recipe. "
        "Follow the phases in order — each phase is independently testable.")

    h2(doc, "19.1  Prerequisites")
    bullet(doc, "Python 3.11+ installed")
    bullet(doc, "Git installed")
    bullet(doc, "OpenAI account with API key (for Phase 3+)")
    bullet(doc, "Docker Desktop (for self-hosted Langfuse in Phase 3)")
    bullet(doc, "8 GB RAM minimum (ChromaDB + Streamlit + Langfuse)")

    h2(doc, "19.2  Phase-by-Phase Build Steps")

    h3(doc, "Phase 1 — Project Setup")
    numbered(doc, "Create project folder: mkdir loan_copilot && cd loan_copilot")
    numbered(doc, "Create folder structure: agent/, tools/, retrieval/, safety/, monitoring/, "
             "deployment/, loan_mcp/, policy_rlhf/, knowledge/raw/, knowledge/chromadb/, "
             "data/rlhf/, logs/, tests/, scripts/, docs/")
    numbered(doc, "Create requirements.txt with: langchain, langchain-openai, langchain-community, "
             "langchain-classic, chromadb, openai, streamlit, langfuse, mcp[fastmcp], "
             "python-dotenv, pytest, pydantic")
    numbered(doc, "pip install -r requirements.txt")
    numbered(doc, "Create .env.example with all key names (no values); add .env to .gitignore")
    numbered(doc, "Create deployment/config.py with all constants reading from os.getenv()")

    h3(doc, "Phase 2 — Rules Engine")
    numbered(doc, "Write agent/memory.py: CustomerProfile dataclass + SessionState + "
             "build_langchain_memory()")
    numbered(doc, "Write agent/planner.py: COLLECTION_SEQUENCE list + next_field_and_question()")
    numbered(doc, "Write tools/emi_calculator.py: @tool with reducing-balance formula")
    numbered(doc, "Write tools/eligibility_checker.py: @tool with 4 checks (age, CIBIL, amount, FOIR)")
    numbered(doc, "Write tools/document_checklist.py: @tool with 4×3 lookup table")
    numbered(doc, "Write agent/core_agent.py Phase 2 path: _detect_intent(), _extract_profile(), "
             "_rules_response(), _check_and_proceed(), _run_rules_tools()")
    numbered(doc, "Write tests for all Phase 2 components. Run pytest — should pass.")
    numbered(doc, "Test: python scripts/run_agent.py --phase 2")

    h3(doc, "Phase 3 — LLM Integration")
    numbered(doc, "Copy .env.example to .env, fill in OPENAI_API_KEY")
    numbered(doc, "Write agent/prompts.py: V1, V2, V3 variants")
    numbered(doc, "Add _get_llm() and _chain_response() to LoanCopilotAgent")
    numbered(doc, "Start Langfuse via Docker Compose, add keys to .env")
    numbered(doc, "Write monitoring/langfuse_logger.py: get_langfuse_callback(), score_session()")
    numbered(doc, "Test: python scripts/run_agent.py --phase 3")
    numbered(doc, "Run prompt A/B test: compare V1/V2/V3 on 5 questions using LLM-as-judge")

    h3(doc, "Phase 4 — RAG Pipeline")
    numbered(doc, "Write 4 synthetic policy .txt files in knowledge/raw/")
    numbered(doc, "Write retrieval/document_loader.py: load files + add product prefix to each chunk")
    numbered(doc, "Write retrieval/chunker.py: RecursiveCharacterTextSplitter(size=500, overlap=100)")
    numbered(doc, "Write retrieval/embedder.py: OpenAIEmbeddings(model='text-embedding-3-small')")
    numbered(doc, "Write retrieval/chroma_store.py: Chroma.from_documents() + persist()")
    numbered(doc, "Write retrieval/retriever.py: similarity_search(query, k=5)")
    numbered(doc, "Write scripts/ingest_documents.py: run the full ingestion pipeline")
    numbered(doc, "Run: python scripts/ingest_documents.py")
    numbered(doc, "Add Phase 4 path to _chain_response(): inject retrieved chunks before user message")
    numbered(doc, "Test: python scripts/run_agent.py --phase 4")

    h3(doc, "Phase 5 — 5 AI Tools + ReAct Agent")
    numbered(doc, "Write tools/tool_search.py: @tool that calls retrieval/retriever.py")
    numbered(doc, "Write tools/tool_escalate.py: @tool that validates and saves escalation record")
    numbered(doc, "Write tools/tool_registry.py: get_all_tools() returning all 5 tools")
    numbered(doc, "Upgrade agent to use create_agent() (LangGraph ReAct loop)")
    numbered(doc, "Write _build_executor() in LoanCopilotAgent")
    numbered(doc, "Test: python scripts/run_agent.py --phase 5")
    numbered(doc, "Verify: LLM calls calculate_emi twice (low + high rate) for eligible loans")

    h3(doc, "Phase 6 — Memory Enhancement")
    numbered(doc, "Add inject_context() to LoanCopilotAgent for product quick-select")
    numbered(doc, "Verify ConversationBufferWindowMemory(k=10) is correctly wired")
    numbered(doc, "Add _extract_profile() call after every LLM response to keep profile in sync")
    numbered(doc, "Test: multi-turn conversation where customer corrects a field mid-flow")

    h3(doc, "Phase 7 — RLHF")
    numbered(doc, "Write policy_rlhf/feedback_collector.py: collect(session_id, response, rating)")
    numbered(doc, "Write policy_rlhf/policy_checker.py: check_response() with 3 violation rules")
    numbered(doc, "Write policy_rlhf/policy_updater.py: analyse feedback, suggest updates")
    numbered(doc, "Add policy check call in _executor_response() after every LLM reply")

    h3(doc, "Phase 8 — Streamlit UI")
    numbered(doc, "Write deployment/app.py with two tabs: Customer Chat + RM Dashboard")
    numbered(doc, "Add product quick-select buttons + inject_context() on click")
    numbered(doc, "Add thumbs up/down feedback buttons under each AI message")
    numbered(doc, "Test full flow: start over, product select, multi-turn, escalation, dashboard")
    numbered(doc, "Run: streamlit run deployment/app.py")

    h3(doc, "Phase 9 — Evaluation + Safety")
    numbered(doc, "Write safety/guardrails.py: keyword_filter() + classify_intent()")
    numbered(doc, "Write safety/pii_filter.py: mask() with 5 regex patterns")
    numbered(doc, "Wire safety gate into Streamlit (check before agent.chat())")
    numbered(doc, "Write scripts/run_evaluation.py: 3 suites (RAG, tools, safety)")
    numbered(doc, "Run: python scripts/run_evaluation.py --suite all")
    numbered(doc, "Ensure 426 pytest tests pass: python -m pytest")

    h3(doc, "Sub-bucket 4C — MCP Layer")
    numbered(doc, "pip install mcp[fastmcp]>=1.0.0")
    numbered(doc, "Write loan_mcp/server.py: FastMCP + 5 @mcp.tool() wrappers")
    numbered(doc, "Write loan_mcp/client.py: call_tool_sync() + list_tools_sync()")
    numbered(doc, "Add get_mcp_tools() to tools/tool_registry.py")
    numbered(doc, "Add USE_MCP env var switch in agent/core_agent.py _build_executor()")
    numbered(doc, "Write scripts/start_mcp_server.py with --transport argument")
    numbered(doc, "Test MCP: USE_MCP=true python scripts/run_agent.py")
    numbered(doc, "Add 11 MCP tests to tests/test_mcp_server.py")

    doc.add_page_break()

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 20 — KEY DESIGN DECISIONS
    # ════════════════════════════════════════════════════════════════════════
    h1(doc, "20  Key Design Decisions & Why")
    body(doc,
        "Understanding WHY the system is designed the way it is matters as much as "
        "understanding what it does. Here are the critical engineering judgment calls "
        "and the reasoning behind each.")

    decisions = [
        ("Phase 2 rules-based baseline first",
         "Build the eligibility logic, EMI formula, and profile collection WITHOUT any AI first. "
         "This gives a reliable, offline-testable baseline. When the LLM is added, you can compare "
         "its behaviour against the rules engine. All Phase 2 tests run without API keys — "
         "zero cost, zero latency, fully deterministic.",
         "If you start with AI and it hallucinates an EMI, you don't know if the formula is wrong "
         "or the AI is wrong. The rules engine removes that ambiguity."),
        ("Two-stage safety gate (keyword + LLM)",
         "Stage A (keyword) catches 80%+ of adversarial probes in <1ms at zero cost. "
         "Stage B (LLM classifier) handles the remaining semantic edge cases. "
         "Doing Stage B first for everything would cost tokens and add 150ms to every message.",
         "Fast-path + semantic backup is a standard defence-in-depth pattern. "
         "Fail-OPEN on Stage B API error means customers are never blocked by infrastructure issues."),
        ("Self-hosted Langfuse (NOT LangSmith)",
         "Banking data cannot leave the bank's premises. LangSmith is cloud-hosted — "
         "every conversation trace would be sent to LangChain's servers. "
         "Langfuse runs inside Docker Compose on the same VM — all data on-premises.",
         "Data residency is a hard requirement for banking. This was the non-negotiable reason."),
        ("Synthetic policy documents",
         "The 4 policy .txt files are synthetically generated (not from a real bank). "
         "This avoids copyright issues, allows the content to be designed to test specific "
         "retrieval scenarios (NRI rules, prepayment charges, etc.), and means "
         "the project can be shared publicly.",
         "Using real bank policy PDFs would require permission and create legal risk."),
        ("V3 Prompt: Chain-of-Thought style",
         "V3 is longer than V1/V2 but provides explicit step-by-step instructions, "
         "edge case handling, and product inference rules. Evaluation showed V3 "
         "outperforms V1/V2 on all three suites.",
         "LLMs perform better with explicit instructions than with vague goals. "
         "More specific = fewer misinterpretations."),
        ("FOIR as the core eligibility metric",
         "FOIR (Fixed Obligation to Income Ratio) is the standard Indian banking metric "
         "for debt capacity. The 50%/55% limit is RBI guideline. "
         "Using FOIR makes the eligibility tool directly comparable to real bank assessment.",
         "Using a custom metric would make the results meaningless to a real banker."),
        ("MCP as the default transport (not an optional add-on)",
         "The default path (USE_MCP=true) routes tools through the FastMCP server — "
         "external access, standard protocol, auto-generated schemas. "
         "Direct import is available via USE_MCP=false as a fast override. "
         "This makes the MCP path the primary path while keeping a low-overhead fallback.",
         "Making MCP the default means external agents (Claude Desktop, API callers) "
         "get the same tool behaviour as the built-in agent with no extra setup."),
        ("Escalation ceiling separate from product maximum",
         "The escalation ceiling (e.g. ₹1.5Cr for home loan) is NOT the same as the "
         "product maximum (₹5Cr). Amounts between the ceiling and maximum are handled "
         "by a specialist RM — they may still be approvable, just not by the copilot.",
         "A customer asking for ₹2Cr home loan should get a callback, not a rejection. "
         "Conflating ceiling with maximum would incorrectly reject valid large-loan customers."),
    ]
    for title, what, why in decisions:
        h3(doc, title)
        body(doc, "What:", bold=True)
        body(doc, what, indent=True)
        body(doc, "Why:", bold=True, color=GREEN)
        body(doc, why, indent=True, color=GREEN)

    doc.add_page_break()

    # ── QUICK REFERENCE CARD ──────────────────────────────────────────────────
    h1(doc, "Quick Reference Card")
    body(doc, "Essential commands at a glance:", bold=True)
    code_block(doc, [
        "# First time setup",
        "pip install -r requirements.txt",
        "cp .env.example .env   # then fill in OPENAI_API_KEY etc.",
        "",
        "# Build vector database (run once after any policy doc change)",
        "python scripts/ingest_documents.py",
        "",
        "# CLI agent (direct tool path)",
        "python scripts/run_agent.py --phase 5",
        "",
        "# CLI agent (MCP tool path)",
        "USE_MCP=true python scripts/run_agent.py",
        "",
        "# Web UI",
        "streamlit run deployment/app.py",
        "",
        "# MCP server for Claude Desktop (stdio)",
        "python scripts/start_mcp_server.py",
        "",
        "# MCP server over HTTP (network/Docker access)",
        "python scripts/start_mcp_server.py --transport http --port 8080",
        "",
        "# Run all 426 tests",
        "python -m pytest",
        "",
        "# Run all 3 evaluation suites",
        "python scripts/run_evaluation.py --suite all",
        "",
        "# RLHF feedback analysis",
        "python scripts/run_rlhf_pipeline.py",
    ])

    body(doc, "Key constants to know:", bold=True)
    two_col_table(doc, [
        ("Constant / Variable", "Where and what"),
        ("ESCALATION_CEILINGS", "deployment/config.py — RM handoff thresholds per product"),
        ("PRODUCT_LIMITS", "tools/eligibility_checker.py — min/max/tenure per product"),
        ("RATE_BANDS", "tools/eligibility_checker.py — indicative rate range per product"),
        ("COLLECTION_SEQUENCE", "agent/planner.py — order of profile fields to collect"),
        ("RAG_TOP_K=5", "deployment/config.py — number of chunks retrieved per query"),
        ("MEMORY_WINDOW=10", "deployment/config.py — conversation turns in sliding window"),
        ("USE_MCP env var", "Set to 'true' to route tools via MCP server instead of direct import"),
        ("SYSTEM_PROMPT", "agent/prompts.py — V3_COT_SAFETY is the production default"),
    ])

    # ── Final page ────────────────────────────────────────────────────────────
    doc.add_page_break()
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(60)
    r = p.add_run("You now have everything you need to explain, build, and extend this system.")
    r.font.size = Pt(14)
    r.font.bold = True
    r.font.color.rgb = NAVY
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    p2 = doc.add_paragraph()
    r2 = p2.add_run(
        "Loan Copilot Capstone  ·  IIT Madras AI Programme  ·  "
        "426 tests passing  ·  Manoj Bansal  ·  2026"
    )
    r2.font.size = Pt(10)
    r2.font.color.rgb = DKGRAY
    r2.font.italic = True
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # ── Save ──────────────────────────────────────────────────────────────────
    import pathlib
    out = pathlib.Path(__file__).resolve().parent.parent / "docs" / "loan_copilot_learner_guide.docx"
    doc.save(out)
    print(f"Saved → {out}")


if __name__ == "__main__":
    build()
