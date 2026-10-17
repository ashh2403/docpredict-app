"""Reproducible, ILLUSTRATIVE training corpus for the DocPredict classifier.

The documents are synthetic: they are assembled from hand-written sentence templates
with randomised slot values. This is enough to demonstrate a real, trained text
classifier end to end, but it is NOT a representative sample of real-world documents.
Scores measured on this data overstate real-world accuracy.

To make the task less trivial, generated documents include:
  * generic boilerplate shared by every category,
  * "confuser" sentences borrowed from other categories,
  * random sentence dropout and shuffling.
"""
from __future__ import annotations

import random

FILL = {
    "name": ["Maria Lopez", "James Carter", "Aisha Khan", "Chen Wei", "Olivia Brown", "Rahul Mehta",
             "Sophie Martin", "Daniel Kim", "Fatima Noor", "Lucas Silva", "Emma Wilson", "Kwame Mensah"],
    "company": ["Northwind Traders", "Acme Industrial Ltd", "Bluepeak Software", "Greenfield Logistics",
                "Orion Health Partners", "Summit Capital Group", "Riverside Media", "Helix Biotech",
                "Crescent Retail", "Atlas Engineering"],
    "city": ["London", "Mumbai", "Toronto", "Berlin", "Austin", "Singapore", "Sydney", "Nairobi"],
    "amount": ["$1,250.00", "$18,400", "EUR 3,980.50", "$742.10", "$56,000", "GBP 12,300", "$9,875.25",
               "INR 4,50,000", "$215.00", "$1.2 million"],
    "date": ["12 March 2024", "January 5, 2025", "2024-11-30", "30/06/2025", "September 18, 2024",
             "1 February 2025", "April 22, 2024", "2025-03-14"],
    "num": ["1042", "INV-2291", "77310", "A-5583", "2024-118", "PO-90412", "3381", "REF-6620"],
    "pct": ["4.2%", "12%", "18.5%", "0.8%", "27%", "6.1%", "33%", "9.75%"],
    "days": ["7", "14", "30", "45", "60", "10", "21"],
    "quarter": ["Q1", "Q2", "Q3", "Q4", "first half", "fiscal year"],
    "year": ["2023", "2024", "2025"],
    "product": ["cloud hosting subscription", "consulting services", "office furniture", "network switches",
                "annual software licence", "marketing campaign", "maintenance contract", "laptop computers"],
    "role": ["software engineer", "data analyst", "project manager", "marketing specialist",
             "registered nurse", "financial analyst", "UX designer", "operations lead"],
    "skill": ["Python", "SQL", "stakeholder management", "React", "financial modelling", "Agile delivery",
              "machine learning", "customer research", "Excel", "cloud infrastructure"],
    "university": ["University of Toronto", "Delhi University", "University of Manchester", "UT Austin",
                   "National University of Singapore", "Technical University of Munich"],
    "condition": ["hypertension", "type 2 diabetes", "iron deficiency anaemia", "mild asthma",
                  "vitamin D deficiency", "elevated cholesterol", "seasonal allergic rhinitis"],
    "drug": ["metformin", "amlodipine", "salbutamol", "atorvastatin", "cetirizine", "ferrous sulfate"],
    "test": ["complete blood count", "lipid panel", "HbA1c", "chest X-ray", "thyroid function test",
             "urinalysis", "ECG"],
    "topic": ["transformer models", "soil microbiology", "urban heat islands", "graph neural networks",
              "supply chain resilience", "protein folding", "renewable energy storage", "sleep quality"],
    "method": ["randomised controlled trial", "cross-sectional survey", "ablation study",
               "mixed-methods design", "longitudinal cohort analysis", "simulation study"],
    "court": ["High Court", "District Court", "County Court", "Civil Court"],
    "team": ["product", "engineering", "finance", "operations", "marketing", "board"],
}

TEMPLATES: dict[str, dict[str, list[str]]] = {
    "invoice": {
        "title": ["INVOICE", "Tax Invoice", "Invoice #{num}", "Commercial Invoice", "Billing Statement and Invoice"],
        "body": [
            "Invoice number {num} issued on {date}.",
            "Bill to: {name}, {company}, {city}.",
            "Payment is due within {days} days of the invoice date.",
            "Description: {product}. Quantity 3. Unit price {amount}.",
            "Subtotal {amount}, tax {pct}, total amount due {amount}.",
            "Please remit payment to the bank account listed below quoting the invoice number.",
            "Late payments may incur an interest charge of {pct} per month.",
            "Balance due: {amount}. Amount paid: $0.00.",
            "Purchase order {num} referenced on this invoice.",
            "Thank you for your business. Payment terms: net {days}.",
            "VAT registration number {num}. Currency: USD.",
            "Line item: {product}, hours billed 12, rate {amount} per hour.",
            "Remittance advice should be sent to accounts receivable at {company}.",
            "This invoice is overdue; the outstanding balance of {amount} must be paid immediately.",
            "Shipping and handling charges of {amount} have been added to the total.",
        ],
    },
    "contract": {
        "title": ["SERVICE AGREEMENT", "Master Services Agreement", "Employment Contract",
                  "Non-Disclosure Agreement", "Lease Agreement", "Consulting Agreement"],
        "body": [
            "This Agreement is entered into on {date} by and between {company} and {name}.",
            "The parties agree to the following terms and conditions.",
            "The term of this Agreement shall commence on the effective date and continue for {days} months.",
            "Either party may terminate this Agreement with {days} days written notice.",
            "The Contractor shall provide {product} as described in Schedule A.",
            "Confidential Information shall not be disclosed to any third party without prior written consent.",
            "This Agreement shall be governed by the laws of the State of {city}.",
            "In consideration of the services, the Client shall pay a fee of {amount} per month.",
            "Each party shall indemnify and hold harmless the other party against claims arising from breach.",
            "Any dispute arising under this Agreement shall be resolved by binding arbitration.",
            "The obligations of confidentiality shall survive termination of this Agreement.",
            "IN WITNESS WHEREOF, the parties have executed this Agreement as of the date first written above.",
            "Neither party may assign its rights under this Agreement without the consent of the other party.",
            "The Employee agrees to a probation period of {days} days and an annual salary of {amount}.",
            "Signature of authorised representative: {name}, on behalf of {company}.",
            "Force majeure events shall excuse performance for the duration of the event.",
        ],
    },
    "resume": {
        "title": ["{name} - Resume", "CURRICULUM VITAE", "{name}", "Professional Resume", "CV - {role}"],
        "body": [
            "Experienced {role} with 6 years of experience delivering results in fast-paced teams.",
            "Professional summary: motivated {role} skilled in {skill} and {skill}.",
            "Work experience: {role} at {company}, {city}, 2019 to present.",
            "Led a team of 5 engineers and improved delivery speed by {pct}.",
            "Education: Bachelor of Science in Computer Science, {university}, {year}.",
            "Skills: {skill}, {skill}, {skill}, communication, teamwork.",
            "Certifications: AWS Certified Solutions Architect, Scrum Master.",
            "Responsible for designing dashboards and presenting insights to senior stakeholders.",
            "Languages: English (fluent), Spanish (intermediate).",
            "References available upon request.",
            "Contact: {name}, phone +1 555 0100, LinkedIn profile available.",
            "Achievements: increased customer retention by {pct} through process redesign.",
            "Internship: junior {role} at {company}, summer {year}.",
            "Volunteer mentor for early-career professionals in {city}.",
            "Seeking a challenging {role} position where I can grow my career.",
        ],
    },
    "medical_report": {
        "title": ["Clinical Report", "Discharge Summary", "Laboratory Results", "Patient Consultation Note",
                  "Medical Examination Report"],
        "body": [
            "Patient: {name}. Date of visit: {date}.",
            "Chief complaint: fatigue and intermittent headaches for two weeks.",
            "Diagnosis: {condition}.",
            "Blood pressure 138/88 mmHg, heart rate 76 bpm, temperature 36.8 C.",
            "The patient was prescribed {drug} 500 mg twice daily.",
            "Results of the {test} were within normal reference ranges except as noted.",
            "Follow-up appointment recommended in {days} days.",
            "History of present illness: symptoms began gradually without known trigger.",
            "Physical examination revealed no acute distress.",
            "Allergies: no known drug allergies.",
            "Plan: continue current medication, monitor symptoms, repeat {test} in three months.",
            "Attending physician: Dr. {name}, Department of Internal Medicine.",
            "Laboratory findings: haemoglobin 11.2 g/dL, slightly below the reference range.",
            "The patient was advised regarding diet, exercise and medication adherence.",
            "Urgent referral to cardiology is recommended due to abnormal ECG findings.",
            "Discharged in stable condition with instructions to return if symptoms worsen.",
        ],
    },
    "financial_report": {
        "title": ["Quarterly Financial Report", "Annual Report {year}", "Statement of Financial Position",
                  "Earnings Summary {quarter} {year}", "Management Accounts"],
        "body": [
            "Revenue for {quarter} {year} increased {pct} year over year to {amount}.",
            "Operating expenses rose to {amount}, driven by investment in headcount.",
            "Net income was {amount}, representing a net margin of {pct}.",
            "EBITDA improved to {amount} compared with the prior period.",
            "Total assets stood at {amount} and total liabilities at {amount}.",
            "Cash and cash equivalents at the end of the period were {amount}.",
            "The board declared a quarterly dividend of $0.12 per share.",
            "Gross margin contracted by {pct} due to higher input costs.",
            "Earnings per share were $1.42 on a diluted basis.",
            "Guidance for the full fiscal year remains unchanged.",
            "The balance sheet remains strong with a current ratio of 2.1.",
            "Cash flow from operating activities totalled {amount}.",
            "These financial statements have been prepared in accordance with IFRS.",
            "Shareholders' equity increased to {amount} at period end.",
            "Segment results: the {team} segment contributed {pct} of consolidated revenue.",
        ],
    },
    "research_paper": {
        "title": ["A Study of {topic}", "Abstract", "On the Effects of {topic}", "Towards Better {topic}",
                  "An Empirical Analysis of {topic}"],
        "body": [
            "Abstract: This paper investigates {topic} using a {method}.",
            "We propose a novel approach and evaluate it on three benchmark datasets.",
            "Our results show a statistically significant improvement of {pct} over the baseline (p < 0.05).",
            "Related work has explored {topic}, but few studies address its limitations.",
            "The methodology section describes the experimental setup and data collection.",
            "Keywords: {topic}, {method}, evaluation.",
            "Section 4 discusses limitations and directions for future work.",
            "We thank the anonymous reviewers for their helpful comments.",
            "Participants (n = 214) were recruited from {city}.",
            "Table 2 reports the mean and standard deviation for each condition.",
            "These findings contribute to the literature on {topic}.",
            "The hypothesis was tested using a mixed-effects regression model.",
            "References: Smith et al. (2021); Zhang and Patel (2023).",
            "In conclusion, the proposed framework generalises well across settings.",
            "Funding for this research was provided by a national science foundation grant.",
        ],
    },
    "meeting_minutes": {
        "title": ["Meeting Minutes", "Minutes of the {team} Meeting", "Board Meeting Minutes",
                  "Weekly Sync Notes", "Team Meeting - {date}"],
        "body": [
            "Date: {date}. Attendees: {name}, {name}, {name}.",
            "The meeting was called to order at 10:00 by the chair.",
            "Agenda item 1: review of action items from the previous meeting.",
            "Action item: {name} to circulate the revised plan by Friday.",
            "The minutes of the previous meeting were approved without amendment.",
            "Discussion: the {team} team raised concerns about the delivery timeline.",
            "Decision: the committee agreed to postpone the launch by two weeks.",
            "Apologies were received from {name}.",
            "Next meeting scheduled for {date} at 2:00 pm.",
            "Any other business: none raised.",
            "The meeting was adjourned at 11:15.",
            "Action items: update the risk register; schedule a follow-up with {company}.",
            "{name} presented the {quarter} progress update to the group.",
            "The motion was proposed by {name} and seconded by {name}; carried unanimously.",
            "Open questions were parked for the next agenda.",
        ],
    },
    "legal_notice": {
        "title": ["LEGAL NOTICE", "Notice of Demand", "Cease and Desist Notice", "Final Notice Before Legal Action",
                  "Notice of Default"],
        "body": [
            "Take notice that our client, {company}, has instructed us to issue this notice.",
            "You are hereby required to pay the outstanding sum of {amount} within {days} days.",
            "Failing compliance, our client will initiate legal proceedings before the {court} without further notice.",
            "You are directed to cease and desist from the infringing activity immediately.",
            "This notice is issued without prejudice to our client's other rights and remedies.",
            "Despite repeated reminders, you have failed to honour your obligations.",
            "You will be liable for all costs and consequences arising from legal action.",
            "This is a final notice. Please treat this matter as urgent.",
            "Advocate for the claimant: {name}, {company}, {city}.",
            "You are in breach of clause 7 of the agreement dated {date}.",
            "A copy of this notice has been retained in our office for further action.",
            "Kindly acknowledge receipt of this notice within {days} days.",
            "Summons: you are required to appear before the {court} on {date}.",
            "The defendant is notified that a claim has been filed against them.",
            "Our client reserves the right to claim damages, interest and legal costs.",
        ],
    },
}

# Additional, more conversational phrasings per category (plain-language variants).
EXTRA_BODY: dict[str, list[str]] = {
    "invoice": [
        "Amount payable: {amount}. Please pay by card or bank transfer.",
        "Charges for work completed: {product}.",
        "Labour and parts are itemised below with the total cost.",
        "This bill covers services provided during the billing period.",
        "Your account has been charged {amount}; a receipt is attached.",
        "Kindly settle the balance by the due date to avoid a late fee.",
        "Customer account number {num}. Billing period ending {date}.",
        "Price per unit, quantity and sales tax are shown for each item.",
        "Fee for {product}: {amount}, payable on receipt.",
        "Statement of charges for {name}.",
    ],
    "contract": [
        "The landlord agrees to let the property to the tenant for a fixed term.",
        "The supplier will deliver {product} and the customer will pay the agreed price.",
        "Both parties agree to keep the terms of this arrangement private.",
        "Ownership of all deliverables transfers to the client upon full payment.",
        "This memorandum of understanding sets out how the two organisations will work together.",
        "The tenant shall pay rent monthly in advance and must not sublet the premises.",
        "Liability under this agreement is limited to the fees paid in the preceding twelve months.",
        "The agreement renews automatically unless either party gives notice of cancellation.",
        "Each party confirms it has authority to enter into these terms.",
        "Obligations of the provider and responsibilities of the client are listed in the schedules.",
        "By signing below, the parties accept these terms.",
    ],
    "resume": [
        "Education: Master's degree in {skill}, graduated {year} with distinction.",
        "Final year project focused on {topic}.",
        "Placement year as a trainee {role} at {company}.",
        "Interests include hiking, chess and volunteering.",
        "Key strengths: problem solving, leadership and {skill}.",
        "Employment history: {role}, {company} ({year} to date); assistant {role}, {company}.",
        "I am a reliable and enthusiastic professional looking for my next opportunity.",
        "Qualifications: diploma and professional certificate in {skill}.",
        "Career highlights include winning an industry award for innovation.",
        "Referees can be provided on request.",
        "Personal profile: graduate {role} keen to develop practical experience.",
    ],
    "medical_report": [
        "The patient reports pain and stiffness that worsens in the morning.",
        "Imaging shows no fracture; mild soft tissue swelling noted.",
        "Impression: findings consistent with {condition}.",
        "Treatment started with {drug}; review response at the next clinic.",
        "Referral letter: thank you for seeing this patient in clinic.",
        "Examination: chest clear, abdomen soft and non-tender.",
        "Specimen received for histology; microscopy report to follow.",
        "Medication changes: stop {drug}, start {drug}.",
        "The patient was admitted to the ward for observation and discharged the following day.",
        "Symptoms have improved since the last appointment.",
        "Clinical history and examination findings are summarised below.",
    ],
    "financial_report": [
        "Sales grew compared with last year while costs were held flat.",
        "Profit before tax for the period was {amount}.",
        "The company ended the year with net cash and no borrowings.",
        "Income and expenditure for the year are summarised in the table below.",
        "Budget variance: actual spend was {pct} above plan.",
        "The forecast for the remaining quarter has been revised.",
        "Reserves at year end were {amount}.",
        "Directors expect full-year results to be in line with expectations.",
        "Capital expenditure for the period amounted to {amount}.",
        "Revenue by region and operating profit by division are presented below.",
        "Net debt reduced during the year following strong cash generation.",
    ],
    "research_paper": [
        "We examine whether {topic} affects outcomes in a sample of volunteers.",
        "Participants were randomly assigned to an intervention group or a control group.",
        "In this article we analyse {topic} using data collected over ten years.",
        "The effect size was moderate (d = 0.4) and confidence intervals are reported.",
        "We discuss possible mechanisms and the need for larger studies.",
        "Introduction: prior studies of {topic} report mixed findings.",
        "The dataset and code are released to support reproducibility.",
        "Our analysis indicates a significant association between the variables.",
        "Conclusions and implications for policy are discussed.",
        "Experiments show the proposed method outperforms existing approaches.",
        "Background, methods, results and discussion are presented in turn.",
    ],
    "meeting_minutes": [
        "Present: chair, secretary, treasurer and members of the {team} committee.",
        "The treasurer reported on the current balance and recent expenses.",
        "It was agreed that {name} would follow up before the next meeting.",
        "A vote was held and the proposal was approved.",
        "What went well and what could be improved were discussed in the retrospective.",
        "The group will reconvene next month.",
        "Members discussed the issue and agreed on next steps.",
        "Actions arising from the discussion are recorded below with owners.",
        "The chair welcomed everyone and thanked volunteers for their help.",
        "Notes taken by the secretary.",
    ],
    "legal_notice": [
        "We act on behalf of our client in relation to the unpaid sum.",
        "Unless payment is received, our client will commence proceedings and seek costs against you.",
        "You are strongly advised to obtain independent legal advice.",
        "Failure to comply is an offence and may lead to prosecution.",
        "You must remove the infringing material and confirm in writing.",
        "Our client requires possession of the property on the date stated.",
        "This letter before claim sets out the basis of our client's claim.",
        "If you do not respond, we have instructions to issue a claim in court without further warning.",
        "You are formally warned that further breaches will result in action.",
        "Notice is hereby given of our client's intention to pursue damages.",
    ],
}
for _cat, _extra in EXTRA_BODY.items():
    TEMPLATES[_cat]["body"].extend(_extra)

# Boilerplate that appears in every kind of document; carries no category signal.
GENERIC = [
    "Please contact us if you have any questions.",
    "This document is confidential and intended only for the named recipient.",
    "Page 1 of 2.",
    "Prepared by {name} on {date}.",
    "For more information visit our website.",
    "{company}, 221 Main Street, {city}.",
    "Phone: +1 555 0142. Email: info@example.com.",
    "All rights reserved.",
    "Please keep this document for your records.",
    "Reference number {num}.",
]


def _fill(template: str, rng: random.Random) -> str:
    out = template
    while "{" in out:
        start = out.index("{")
        end = out.index("}", start)
        key = out[start + 1:end]
        out = out[:start] + rng.choice(FILL[key]) + out[end + 1:]
    return out


def generate_document(category: str, rng: random.Random) -> str:
    spec = TEMPLATES[category]
    n_body = rng.randint(3, 8)
    sentences = rng.sample(spec["body"], k=n_body)
    sentences += rng.sample(GENERIC, k=rng.randint(1, 3))
    # Confusers: sentences from another category (noise / mixed documents).
    if rng.random() < 0.5:
        other = rng.choice([c for c in TEMPLATES if c != category])
        sentences += rng.sample(TEMPLATES[other]["body"], k=rng.randint(1, 2))
    rng.shuffle(sentences)
    lines = [_fill(rng.choice(spec["title"]), rng)] if rng.random() < 0.85 else []
    lines += [_drop_words(_fill(s, rng), rng) for s in sentences]
    return "\n".join(lines)


def _drop_words(sentence: str, rng: random.Random, p: float = 0.12) -> str:
    """Randomly drop words so the model cannot rely on exact template phrases."""
    words = sentence.split()
    kept = [w for w in words if rng.random() >= p]
    return " ".join(kept or words)


def generate_corpus(n_per_class: int = 160, seed: int = 42) -> tuple[list[str], list[str]]:
    rng = random.Random(seed)
    texts: list[str] = []
    labels: list[str] = []
    for category in TEMPLATES:
        for _ in range(n_per_class):
            texts.append(generate_document(category, rng))
            labels.append(category)
    return texts, labels
