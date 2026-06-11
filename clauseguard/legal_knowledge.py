"""
clauseguard.legal_knowledge
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Single source of truth for ClauseGuard's legal knowledge base.
Derived from the ClauseGuard Agent Specification (pasted_content.txt).

This module is intentionally dependency-free so it can be imported anywhere
without triggering I/O or network calls.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# § Operating Rules (spec lines 8-17)
# ---------------------------------------------------------------------------

OPERATING_RULES: list[str] = [
    "Do not assume the governing-law clause determines privacy or export-control scope.",
    (
        "First identify all potentially applicable jurisdictions based on: place of incorporation, "
        "customer location, data subject location, service-delivery location, processing location, "
        "hosting location, support location, remote-access location, subprocessor location, "
        "transfer destination end-user location, and sanctions nexus."
    ),
    "Do not infer 'no personal data' unless the contract clearly excludes personal data and the services objectively do not require personal data.",
    "Infer 'export-control issue' only when explicitly the contract mentions or there is access to controlled items by associates.",
    "Where contract wording conflicts with mandatory law, state that mandatory law prevails and mark the clause FAIL unless revised.",
    "If a clause is ambiguous, interpret it against compliance risk and propose clarifying language.",
    "If the contract contemplates onward transfers, subprocessors, affiliates, offshore support, or global shared services, analyze those separately.",
    "If any party, destination, intermediary, beneficial owner, or end user may be sanctioned or restricted, mark CRITICAL and ESCALATE.",
    "Never invent facts, legal obligations, regulatory approvals, or transfer mechanisms.",
]

# ---------------------------------------------------------------------------
# § Guardrails (spec lines 106-111)
# ---------------------------------------------------------------------------

GUARDRAILS: list[str] = [
    "Always cite the exact clause(s) or section(s) you relied on in the contract.",
    (
        "Never state that a contract is 'fully compliant in all jurisdictions' unless every relevant "
        "jurisdiction has been positively analyzed and all material facts are complete. "
        "Prefer 'no material issues identified on current facts' over categorical legal certification."
    ),
    "If internal legal rule library and current facts conflict, flag the conflict and escalate.",
    (
        "If a contract says one party may disclose data 'as required by law,' verify notice, "
        "minimisation, challenge rights, logging, and lawful transfer/disclosure limitations."
    ),
    (
        "If the contract involves AI/ML services, datasets, training data, model weights, telemetry, "
        "or employee monitoring, increase privacy scrutiny by one level and assess whether data-use "
        "clauses allow impermissible secondary use."
    ),
    "You do not provide legal advice or regulatory certification.",
    (
        "You must operate conservatively. If the contract facts are incomplete, the legal position is "
        "ambiguous, or a jurisdiction-specific rule cannot be reliably determined, mark the issue "
        "ESCALATE TO HUMAN PRIVACY COUNSEL / EXPORT CONTROL TEAM and must not conclude the contract is compliant."
    ),
    (
        "You must distinguish: (i) mandatory legal requirements; (ii) regulator guidance / best practice; "
        "and (iii) internal policy preferences. Never present guidance or policy preference as if it were "
        "a statutory requirement."
    ),
]

# ---------------------------------------------------------------------------
# § Jurisdiction-Identification Logic (spec lines 27-32)
# ---------------------------------------------------------------------------

PRIVACY_JURISDICTION_TRIGGERS: list[str] = [
    "a party is established there",
    "goods/services are offered to people there",
    "personal data is collected from people there",
    "processing occurs there",
    "data is stored there",
    "data is accessed there",
    "support is delivered there",
]

EXPORT_CONTROL_JURISDICTION_TRIGGERS: list[str] = [
    "controlled items/software/technology originate there",
    "an export, reexport, transfer, transit, or remote-access event occurs there or under that regime",
    "a sanctioned-country nexus exists",
    "a restricted end user/end use exists",
]

JURISDICTION_SPECIAL_RULES: dict[str, str] = {
    # ── Europe ──────────────────────────────────────────────────────────────
    "European Union / EEA": (
        "GDPR applies to all EU/EEA member states. Identify the specific Member State(s) involved "
        "and check for any national sectoral overlays (e.g., German BDSG, French CNIL guidance, "
        "Dutch Telecommunications Act, Irish DPC requirements). Apply Article 28 processor terms, "
        "Chapter V transfer analysis for any data leaving the EEA, and SCCs or adequacy decisions. "
        "ePrivacy rules apply where electronic communications are involved. Always determine the "
        "lead supervisory authority for cross-border processing."
    ),
    "United Kingdom": (
        "Post-Brexit: apply UK GDPR and the Data Protection Act 2018 separately from EU GDPR. "
        "For restricted transfers out of the UK, verify use of the UK International Data Transfer "
        "Agreement (IDTA) or UK Addendum to EU SCCs — not the EU SCCs alone. A Transfer Risk "
        "Assessment (TRA) is required for UK restricted transfers. The ICO is the UK supervisory "
        "authority. Check whether the EU-UK adequacy decision remains in effect at time of review."
    ),
    # ── Asia-Pacific ────────────────────────────────────────────────────────
    "India": (
        "Apply the Digital Personal Data Protection Act, 2023 (DPDPA) and DPDP Rules, 2025. "
        "Note phased implementation — verify which provisions are currently in force at time of review. "
        "Key obligations: notice/consent or another lawful ground per Schedule 1, Data Fiduciary/Data "
        "Processor roles, Significant Data Fiduciary obligations if triggered (DPO, DPIA, audit), "
        "children's data (under 18) requires verifiable parental consent, cross-border transfer "
        "restrictions apply to countries/territories not notified by the Central Government as permitted. "
        "Grievance mechanism is mandatory. Breach notification to DPBI (Data Protection Board of India) "
        "is required. This is a rapidly evolving law — flag any gaps for counsel confirmation."
    ),
    "Australia": (
        "Apply the Privacy Act 1988 (Cth) and the 13 Australian Privacy Principles (APPs). "
        "APP 8 governs overseas disclosure — requires reasonable steps to ensure the overseas recipient "
        "does not breach APPs or uses a contractual mechanism. The Privacy Act is currently under reform "
        "(Privacy and Other Legislation Amendment Act 2024) — verify the current amendment status at "
        "time of review. Direct marketing obligations under APP 7. Health information is sensitive "
        "data with heightened obligations. State/territory health legislation may impose additional "
        "requirements. The OAIC is the federal regulator."
    ),
    "New Zealand": (
        "Apply Privacy Act 2020 and the 13 Information Privacy Principles (IPPs). Mandatory data "
        "breach notification to the Privacy Commissioner if serious harm is likely. The Act has "
        "extraterritorial reach where an agency 'carries on business' in NZ. Overseas disclosure "
        "(IPP 12) requires the recipient to have comparable safeguards or the individual consents. "
        "Binding scheme applies where a third country has been deemed to have adequate protections."
    ),
    "Canada": (
        "Apply PIPEDA at the federal level and applicable provincial statutes (PIPA-Alberta, PIPA-BC, "
        "Law 25 in Quebec). Quebec's Law 25 has been fully phased in as of September 2023 and has "
        "GDPR-equivalent strength including DPO requirements, PIAs, and cross-border transfer "
        "agreements. PIPEDA modernization (Bill C-27 / Consumer Privacy Protection Act) is pending — "
        "flag for counsel. OPC (federal) and provincial commissioners are the regulators. "
        "Accountability principle means the organization remains responsible for personal information "
        "transferred to third-party processors."
    ),
    "Thailand": (
        "Apply Thailand PDPA (B.E. 2562). Key obligations: lawful basis (consent, contract, "
        "legitimate interest, vital interest, public interest, or legal obligation), data subject "
        "rights (access, rectification, erasure, restriction, portability, objection), breach "
        "notification to PDPC within 72 hours and to data subjects without undue delay where likely "
        "to cause harm. DPO appointment required for certain controllers. Cross-border transfers "
        "require adequacy decision, contractual safeguards, or binding corporate rules. "
        "The PDPC is the regulator. Sensitive data requires explicit consent."
    ),
    "Singapore": (
        "Apply PDPA 2012 as amended by the Personal Data Protection (Amendment) Act 2020. "
        "Key obligations: notification/consent or applicable exceptions, business contact data "
        "exceptions, purpose limitation, access and correction, data portability (for prescribed "
        "organisations), mandatory breach notification to PDPC within 3 calendar days (or next "
        "business day in serious cases) and to affected individuals where significant harm is likely. "
        "Retention limitation: not longer than necessary. Transfer limitation: requires comparable "
        "protection. DPO appointment is a best practice but not always mandatory. "
        "PDPC is the regulator. Financial and health sectors have additional MAS/MOH overlays."
    ),
    "Malaysia": (
        "Apply PDPA 2010 (Act 709) as amended. The Act applies to personal data processed in "
        "commercial transactions. Seven data protection principles apply. Sensitive personal data "
        "requires explicit consent. Cross-border transfer only to countries in the whitelist published "
        "by the Minister — check current whitelist. The Commissioner is the regulator. "
        "Amendment bill is pending — flag for counsel. DPO obligations are sector-dependent. "
        "Breach notification requirements are not yet codified in the main Act — check current position."
    ),
    "Indonesia": (
        "Apply the Personal Data Protection Law (Law No. 27 of 2022) and implementing regulations. "
        "Two-year transition period ended October 2024 — all obligations now fully in force. "
        "Roles: Personal Data Controller and Personal Data Processor. Lawful basis includes consent, "
        "contractual fulfillment, legal obligation, vital interest, public interest, or legitimate interest. "
        "Cross-border transfer requires coordination with the Ministry and a comparable level of protection. "
        "Data localisation requirements may apply for certain strategic sectors — verify current rules. "
        "Breach notification to the minister and data subjects is required. "
        "The Ministry of Communications and Digital (Komdigi) is the primary regulator."
    ),
    "South Korea": (
        "Apply the Personal Information Protection Act (PIPA) as amended in 2023 (effective September 2024). "
        "The 2023 amendments significantly strengthened enforcement and harmonised with GDPR. "
        "Key: lawful basis (consent, contract, legal obligation, legitimate interest — new), "
        "PIPC is the unified regulator (telecom, financial and health sectors may have additional overlays). "
        "Overseas transfer: requires consent or one of the approved mechanisms (standard contracts "
        "approved by PIPC, BCRs, adequacy recognised country, or certification). "
        "Pseudonymisation rules allow data use for statistical/research purposes without consent. "
        "Breach notification to PIPC within 24 hours (72 hours for large breaches to data subjects)."
    ),
    "Philippines": (
        "Apply the Data Privacy Act of 2012 (RA 10173) and NPC issuances/circulars. "
        "Roles: Personal Information Controller (PIC) and Personal Information Processor (PIP). "
        "Data sharing agreements required between PICs sharing data. "
        "Outsourcing agreements required between PIC and PIP. "
        "Breach notification to NPC within 72 hours of discovery; notification to data subjects "
        "without undue delay if likely to adversely affect their rights and freedoms. "
        "DPO registration with NPC is required for covered organisations. "
        "Cross-border transfer requires comparable protection standards."
    ),
    "Japan": (
        "Apply the Act on the Protection of Personal Information (APPI) as amended effective April 2022. "
        "Key changes: opt-out transfers broadened restriction, new 'specially protected' sensitive data "
        "category, mandatory breach reporting to PPC and data subjects within specified timelines "
        "(generally 30 days / 60 days depending on breach type), third-party transfer restrictions, "
        "cross-border transfer conditions (consent, adequacy-equivalent country, or contractual "
        "safeguards per PPC rules), pseudonymised and anonymised information handling rules. "
        "The PPC (Personal Information Protection Commission) is the regulator."
    ),
    "China": (
        "Apply the Personal Information Protection Law (PIPL) effective November 2021, the Cybersecurity "
        "Law (CSL) effective June 2017, and the Data Security Law (DSL) effective September 2021. "
        "Key PIPL obligations: separate consent or lawful basis for each processing purpose, "
        "separate explicit consent for sensitive personal information (biometric, health, finance, "
        "location, minors under 14), DPO appointment for critical information infrastructure operators "
        "or large-volume processors, PIPIA (impact assessment) for certain processing, data localisation "
        "for critical information infrastructure operators and large-volume processors (triggered by "
        "volume thresholds), cross-border transfer requires one of: CAC security assessment (mandatory "
        "in certain cases), PIPC standard contract (SCC equivalent), or certification. "
        "Important law to flag for escalation given rapidly evolving regulatory environment."
    ),
    # ── Middle East ──────────────────────────────────────────────────────────
    "UAE (mainland)": (
        "Apply Federal Decree-Law No. 45 of 2021 on the Protection of Personal Data (PDPL) and its "
        "implementing regulations. The PDPL applies to personal data processed in the UAE or related "
        "to individuals in the UAE. Key obligations: lawful basis (consent, contractual necessity, "
        "legal obligation, vital interest, or public interest), data controller/processor obligations, "
        "cross-border transfer only to adequate countries or with contractual safeguards approved by "
        "the UAE Data Office. Sensitive data (biometric, genetic, health, criminal, financial, children) "
        "requires explicit consent or legal basis. Data subject rights: access, correction, deletion, "
        "objection, portability. Breach notification to UAE Data Office and data subjects is required. "
        "Sectoral regulators (CBUAE for finance, DoH/HAAD for health, TRA for telecom) may impose "
        "additional requirements. The UAE Data Office is the primary regulator."
    ),
    "Dubai / DIFC": (
        "CRITICAL DUAL-REGIME ANALYSIS REQUIRED: determine whether the contract party is a DIFC-licensed "
        "entity (inside the DIFC free zone) or a mainland Dubai entity. These are separate regimes: "
        "(1) DIFC entities: apply DIFC Data Protection Law No. 5 of 2020 and DIFC DP Regulations — "
        "GDPR-equivalent framework, Commissioner of Data Protection is the DIFC regulator. "
        "(2) Mainland Dubai entities: apply UAE Federal PDPL (Federal Decree-Law No. 45 of 2021). "
        "If both DIFC and mainland are involved, analyze BOTH regimes separately. "
        "Do not apply EU GDPR to DIFC contracts — apply DIFC DP Law No. 5 of 2020 instead."
    ),
    "Abu Dhabi / ADGM": (
        "If the contract party is an ADGM-licensed entity, apply the ADGM Data Protection Regulations "
        "2021 — a GDPR-equivalent framework administered by the ADGM Registration Authority. "
        "Do not conflate with UAE Federal PDPL: ADGM has its own separate data protection regime. "
        "If both ADGM and mainland UAE entities are involved, analyze both regimes separately. "
        "For cross-border transfers, ADGM uses an adequacy/safeguards framework similar to GDPR."
    ),
    "Saudi Arabia": (
        "Apply the Personal Data Protection Law (PDPL) (Royal Decree No. M/19) and SDAIA implementing "
        "regulations (currently on their second version). The NDMO/SDAIA is the regulator. "
        "Key obligations: lawful basis (consent, contractual necessity, legal obligation, vital interest, "
        "public interest, or SDAIA-approved legitimate interest), explicit consent for sensitive data "
        "(health, genetic, biometric, financial, criminal, religion, political opinion), purpose "
        "limitation, cross-border transfer requires Data Authority approval or contractual safeguards. "
        "Data subject rights: access, correction, deletion, restriction, objection, portability. "
        "Breach notification within 72 hours to the Data Authority. Direct marketing restrictions apply. "
        "CRITICAL: PDPL and regulations are evolving rapidly — flag for counsel confirmation on "
        "current implementing rules. Sectoral rules (healthcare: MOH; finance: SAMA) apply additionally."
    ),
    "Kuwait": (
        "MANDATORY ESCALATION: Kuwait does not have a single comprehensive omnibus private-sector data "
        "protection statute equivalent to GDPR as of the current date. Apply a conservative, "
        "sector-specific analysis using: Cybercrime Law No. 63 of 2015, telecommunications privacy rules, "
        "Banking Law (for financial data), constitutional privacy provisions (Article 39), and sector "
        "regulatory guidance. All Kuwait-nexus issues must be automatically escalated to local Kuwait "
        "privacy counsel for confirmation — do not conclude compliance without specialist advice. "
        "Flag the absence of an omnibus data protection law in every Kuwait-related finding."
    ),
    "Bahrain": (
        "Apply the Personal Data Protection Law (Law No. 30 of 2018) and implementing regulations. "
        "The PDPL Commissioner is the regulator. Key obligations: lawful basis (consent, contract, "
        "legal obligation, vital interest, public task, or legitimate interests), controller/processor "
        "obligations, sensitive data (health, genetic, biometric, criminal, religious/political beliefs, "
        "children's data) requires explicit consent or legal basis, cross-border transfer requires "
        "adequacy or contractual safeguards. Data subject rights: access, correction, deletion, "
        "restriction, objection. Breach notification required. Financial sector (CBB) has "
        "additional data-related regulatory requirements."
    ),
    "Qatar": (
        "DUAL-REGIME ANALYSIS: determine whether the party is a Qatar Financial Centre (QFC) entity "
        "or an onshore Qatar entity — these are separate regimes: "
        "(1) QFC entities: apply QFC Data Protection Regulations (QDPR) — GDPR-equivalent framework "
        "administered by the QFC Authority. "
        "(2) Onshore Qatar entities: apply Personal Data Privacy Protection Law (Law No. 13 of 2016) "
        "administered by the Ministry of Transport and Communications. "
        "If both QFC and onshore entities are involved, analyze both regimes separately. "
        "Flag for counsel if facts are unclear about which regime applies."
    ),
    "Oman": (
        "Apply the Personal Data Protection Law (Royal Decree 6/2022) and implementing rules "
        "as issued by the Information Technology Authority (ITA). Key obligations: lawful basis, "
        "controller/processor responsibilities, cross-border transfer restrictions (transfer only to "
        "adequate countries or with ITA approval/contractual safeguards), data subject rights, "
        "security measures, breach notification. Registration/licensing of databases may be required "
        "in certain sectors. Law is relatively new — flag for counsel on current implementing rules."
    ),
    "Israel": (
        "Apply the Privacy Protection Law 5741-1981, the Privacy Protection (Data Security) Regulations "
        "2017, and cross-border transfer rules. The Privacy Protection Authority (PPA) is the regulator. "
        "Database registration is required for certain databases under the Privacy Protection Law. "
        "Data security regulations impose tiered security obligations based on database type/sensitivity. "
        "Cross-border transfers only to countries on the approved whitelist or with PPA approval. "
        "Israel is currently harmonising its data protection framework closer to GDPR standards "
        "(new Privacy Protection Law is in legislative process — flag for counsel). "
        "Note: EU has recognised Israel as having adequate protection for EU→Israel transfers."
    ),
    "Egypt": (
        "Apply the Personal Data Protection Law No. 151 of 2020 and Executive Regulations "
        "(Ministerial Decree No. 151 of 2020). The MCIT is the supervisory authority. "
        "Key obligations: lawful basis (consent or legal basis), prior notification/registration "
        "of databases with the Authority in certain cases, licence requirement for certain data "
        "processing activities, cross-border transfer requires Authority approval or contractual "
        "safeguards meeting Egyptian standards. Sensitive data (health, genetic, biometric, "
        "financial, children) has heightened protections. "
        "CRITICAL: Licensing and registration requirements are unique to Egypt — always flag for "
        "Egypt-specific legal counsel as non-compliance with registration/licensing creates criminal risk."
    ),
    # ── Africa ──────────────────────────────────────────────────────────────
    "South Africa": (
        "Apply the Protection of Personal Information Act 4 of 2013 (POPIA), fully in force since "
        "July 2021. The Information Regulator is the enforcement authority. Roles: responsible party "
        "(controller) and operator (processor). Eight conditions for lawful processing apply "
        "(accountability, processing limitation, purpose specification, further processing limitation, "
        "information quality, openness, security safeguards, data subject participation). "
        "Prior authorisation from the Information Regulator is required for certain high-risk processing "
        "activities before commencement. Cross-border transfer requires comparable protection or "
        "consent or contractual safeguards. Security compromise notification to Information Regulator "
        "and data subjects as soon as reasonably possible."
    ),
    # ── Americas ────────────────────────────────────────────────────────────
    "United States": (
        "Do not assume one single U.S. privacy law applies. Determine applicability based on "
        "business model, data types, sector, and state nexus: "
        "(1) Federal sector-specific laws: HIPAA (health), GLBA (financial), COPPA (children under 13), "
        "FERPA (educational records), FCRA (consumer reports), ECPA (communications). "
        "(2) FTC Act Section 5 — unfair/deceptive practices: applies broadly to all consumer-facing "
        "entities and covers privacy policy representations. "
        "(3) State comprehensive privacy laws: determine which apply based on revenue/data volume "
        "thresholds and residency of data subjects — California (CCPA/CPRA, enforced by CPPA), "
        "Virginia (VCDPA), Colorado (CPA), Connecticut (CTDPA), Texas (TDPSA), Oregon (OCPA), "
        "Montana, Iowa, Indiana, Tennessee, Florida, Delaware, New Hampshire, New Jersey, "
        "Nebraska, Kentucky, Maryland, Minnesota and others. Check current enacted state laws. "
        "(4) Biometric data: Illinois BIPA has particularly onerous requirements with private right of action. "
        "(5) Health data: state mini-HIPAA laws and the My Health My Data Act (Washington) may apply. "
        "When multiple states apply, identify the strictest requirements and apply them."
    ),
    "Brazil": (
        "Apply the Lei Geral de Proteção de Dados (LGPD) — Law No. 13.709/2018, as amended by "
        "Law 13.853/2019. ANPD (National Data Protection Authority) is the regulator. "
        "Roles: controller and operator (equivalent to GDPR controller/processor). "
        "Ten lawful bases: consent, compliance with legal obligation, public policy execution, "
        "research, contract performance, regular exercise of rights in legal proceedings, "
        "protection of life, health protection, legitimate interests, or credit protection. "
        "International transfers require: adequacy decision, specific contractual clauses "
        "(SCCs equivalent, approved by ANPD), BCRs, regulatory cooperation, or consent. "
        "ANPD has published standard contractual clauses. Data subject rights mirror GDPR. "
        "DPO (Encarregado) appointment is required for controllers. ANPD authority is growing — "
        "flag significant data processing for counsel review."
    ),
    "Colombia": (
        "Apply Law 1581 of 2012 (Statutory Law on Personal Data Protection) and related decrees "
        "(Decree 1377 of 2013, Decree 1074 of 2015). The SIC (Superintendence of Industry and Commerce) "
        "is the regulator. Key: prior informed authorization (habeas data consent) is required from "
        "data subjects before collecting sensitive data, and for international transfers unless the "
        "destination country has adequate protection. Database registration with the RNBDyP (National "
        "Registry of Databases) is required for responsible parties processing data of Colombian nationals. "
        "Transmission agreements (between controller and processor) are required. "
        "Data subject rights: access, correction, deletion, and complaints. "
        "Health data, sexual orientation, racial/ethnic origin, political opinions, religious beliefs, "
        "union membership, and biometric data are sensitive and require explicit consent."
    ),
}

# ---------------------------------------------------------------------------
# § Keywords that trigger Export Control review (spec lines 12, 81-85)
# ---------------------------------------------------------------------------

EXPORT_TRIGGER_KEYWORDS: list[str] = [
    # Direct regulatory references
    "EAR", "OFAC", "ITAR", "dual-use", "dual use",
    "export control", "export licence", "export license",
    "reexport", "re-export", "deemed export",
    "sanction", "sanctions", "restricted party", "denied party",
    "embargoed", "embargo",
    # Controlled technology indicators
    "encryption", "cryptography", "source code", "technical data",
    "controlled item", "controlled technology", "controlled software",
    "ECCN", "EAR99", "dual-use category",
    "model weights", "AI model", "model sharing",
    # High-risk sectors
    "semiconductor", "aerospace", "telecom core", "satellite",
    "defense", "defence", "nuclear", "chemical", "biological",
    "cyber-surveillance", "advanced computing",
    # Export events
    "remote support", "remote access to controlled", "cloud access to controlled",
    "license exception", "general license",
    "brokering", "technical assistance",
]

# ---------------------------------------------------------------------------
# § Baseline Data Privacy Review Tests (spec lines 33-48)
# ---------------------------------------------------------------------------

BASELINE_PRIVACY_TESTS: list[str] = [
    "Test whether the contract clearly defines party roles and permitted processing purposes.",
    (
        "Test whether the contract prohibits the service provider from using customer personal data "
        "for unrelated independent purposes unless clearly allowed by law and contractually disclosed."
    ),
    (
        "Test for transparency support: notices, privacy information, and cooperation where the "
        "customer relies on the supplier for factual disclosures."
    ),
    (
        "Test for lawful processing allocation: consent / contractual necessity / legitimate interest "
        "/ statutory ground or local equivalent, where relevant."
    ),
    "Test for data minimisation, purpose limitation, storage limitation, and accuracy support.",
    "Test for confidentiality obligations binding personnel and subprocessors.",
    (
        "Test for security obligations: appropriate technical and organisational measures, secure "
        "development/operations, encryption/access control where appropriate, vulnerability management, "
        "logging, backup, resilience, and personnel confidentiality."
    ),
    (
        "Test for subprocessor controls: prior authorisation or notice, flow-down obligations, "
        "responsibility for subprocessor acts, and objection/termination rights where required."
    ),
    (
        "Test for cross-border transfer compliance: adequacy / whitelists / contractual safeguards "
        "/ local transfer approvals / assessments / localisation restrictions / regulator filings "
        "where applicable."
    ),
    (
        "Test for data-subject-rights assistance: access, correction, deletion/erasure, "
        "restriction/objection, portability where applicable, complaint handling, and response support."
    ),
    (
        "Test for breach/incident management: notification trigger, timeline, content requirements, "
        "cooperation, remediation, evidence preservation, regulator / data-subject support, and "
        "allocation of investigation costs."
    ),
    "Test for retention, deletion, return, and backup handling at end of services.",
    (
        "Test for audit rights or acceptable assurance substitutes (certifications, audit reports, "
        "questionnaires, regulator inspection cooperation)."
    ),
    "Test for recordkeeping and DPIA / TIA / transfer-risk-assessment / ROPA support if applicable.",
    (
        "Test for government-access / compelled-disclosure handling, including notice where lawful, "
        "challenge rights, minimisation, and logging."
    ),
]

# ---------------------------------------------------------------------------
# § Jurisdiction-Specific Privacy Instructions (spec lines 49-77)
# ---------------------------------------------------------------------------

JURISDICTION_PRIVACY_INSTRUCTIONS: dict[str, str] = {
    "European Union / EEA": (
        "Apply GDPR territorial-scope logic, controller/processor obligations, Article 28-equivalent "
        "processor terms where required, Chapter V transfer analysis, SCCs/adequacy if data leaves "
        "the EEA, and local Member State/sectoral overlays where facts indicate."
    ),
    "United Kingdom": (
        "Apply UK GDPR and DPA 2018; if restricted transfers occur, verify use of IDTA or UK Addendum "
        "to EU SCCs (or another lawful mechanism) and require transfer-risk analysis where needed."
    ),
    "India": (
        "Apply the DPDP Act, 2023 and DPDP Rules, 2025, recognising phased implementation and any "
        "then-effective provisions; test notice/consent or another lawful ground, grievance handling, "
        "security safeguards, children's-data requirements, processor obligations, and cross-border "
        "restrictions/current government notifications."
    ),
    "United States": (
        "Determine applicable federal, state, and sectoral laws. At minimum test for FTC "
        "unfair/deceptive-practices risk, state privacy law notice/rights/service-provider language "
        "where applicable, and sector-specific obligations (HIPAA, GLBA, COPPA, FERPA, etc.) if "
        "triggered by the facts."
    ),
    "Australia": (
        "Apply Privacy Act 1988 and APPs, including overseas disclosure considerations and direct "
        "marketing / cross-border handling where relevant."
    ),
    "New Zealand": (
        "Apply Privacy Act 2020, including information privacy principles, breach notification, "
        "and overseas disclosure rules."
    ),
    "Canada": (
        "Apply PIPEDA and any applicable provincial private-sector law; test meaningful "
        "consent/appropriate purposes, service-provider clauses, safeguards, breach handling, "
        "and cross-border processing disclosures/limitations."
    ),
    "Thailand": (
        "Apply PDPA; test lawful basis, consent where required, processor terms, DPO triggers if "
        "applicable, 72-hour breach-support requirements if applicable, and cross-border transfer rules."
    ),
    "Singapore": (
        "Apply PDPA; test consent/notification or applicable exceptions, business-contact-data "
        "exceptions where relevant, DPO support, retention limitation, transfer-limitation clause, "
        "and breach-notification support."
    ),
    "Malaysia": (
        "Apply PDPA 2010 as amended; test notice/consent, security, retention, data integrity, "
        "access/correction, cross-border transfer restrictions/current framework, breach-support "
        "requirements if applicable, and DPO obligations if then in force for the relevant entity."
    ),
    "Indonesia": (
        "Apply PDP Law and implementing rules; test lawful basis, controller/processor roles, rights "
        "support, security, breach reporting, cross-border transfer/localisation requirements if "
        "applicable, and contract terms for electronic and non-electronic processing."
    ),
    "South Korea": (
        "Apply PIPA and relevant regulator guidance; test notice/consent or lawful basis, "
        "outsourcing/provision/entrustment terms, overseas transfer rules, data-subject rights, "
        "breach handling, and localisation/sector overlays if triggered."
    ),
    "Philippines": (
        "Apply the Data Privacy Act and NPC issuances; test transparency, lawful processing criteria, "
        "outsourcing/data-sharing agreements, breach management, security, and cross-border considerations."
    ),
    "Japan": (
        "Apply APPI; test purpose specification, use restrictions, security controls, third-party "
        "transfer rules, cross-border transfer conditions, pseudonymised/anonymised information "
        "handling if relevant, and data-subject rights support."
    ),
    "UAE (mainland)": (
        "Apply Federal PDPL and sectoral rules (health, banking, telecom, consumer rules as "
        "applicable). Test consent or lawful exceptions, security, processor terms, data-subject "
        "rights, and cross-border transfer conditions."
    ),
    "Dubai / DIFC": (
        "If DIFC nexus exists, apply DIFC Data Protection Law No. 5 of 2020 and associated "
        "obligations. If the entity is in mainland Dubai, apply UAE federal PDPL. If both are "
        "involved, analyze both regimes separately."
    ),
    "Abu Dhabi / ADGM": (
        "If ADGM nexus exists, apply ADGM Data Protection Regulations 2021 separately from "
        "federal UAE rules."
    ),
    "China": (
        "Apply PIPL and, where facts indicate, Cybersecurity Law / Data Security Law obligations. "
        "Test separate-consent / lawful basis requirements, processor obligations, "
        "localisation/security-assessment or standard-contract requirements for cross-border "
        "transfers, personal-information handling rules, sensitive personal information handling, "
        "and government-access restrictions."
    ),
    "Brazil": (
        "Apply LGPD; test controller/operator obligations, lawful basis, international transfers, "
        "ANPD-related cooperation, DPO/contact requirements where applicable, and data-subject rights."
    ),
    "Colombia": (
        "Apply Law 1581 of 2012 and related decrees; test prior informed authorisation where "
        "required, processor/controller roles, rights procedures, international transfers/transmissions, "
        "and database registration/filing obligations if applicable."
    ),
    "Saudi Arabia": (
        "Apply PDPL and SDAIA rules/guidance; test lawful basis, privacy notice, processor terms, "
        "retention, security, direct marketing where relevant, and cross-border transfer conditions."
    ),
    "Kuwait": (
        "Perform a conservative, sector-specific analysis only and automatically escalate to counsel "
        "for Kuwait-specific legal confirmation. Apply sectoral/privacy, cybercrime, telecom and "
        "constitutional privacy rules conservatively."
    ),
    "Bahrain": (
        "Apply the Personal Data Protection Law; test lawful basis, processor/controller terms, "
        "rights, security, and transfer restrictions."
    ),
    "Israel": (
        "Apply Privacy Protection Law, data security regulations, and cross-border transfer rules; "
        "test database registration / security / transfer restrictions if triggered."
    ),
    "Qatar": (
        "Apply Personal Data Privacy Protection Law and, if QFC nexus exists, QFC Data Protection "
        "Regulations. Analyze mainland and QFC separately if both appear."
    ),
    "Oman": (
        "Apply Personal Data Protection Law and implementing rules; test consent/lawful basis, "
        "transfer rules, security, rights, and registration/approvals if applicable."
    ),
    "Egypt": (
        "Apply Personal Data Protection Law No. 151 of 2020 and executive regulations; test "
        "licences/permits if required, cross-border transfer restrictions, security, and rights support."
    ),
    "South Africa": (
        "Apply POPIA; test responsible-party/operator roles, processing conditions, prior "
        "authorisation triggers, security compromise notification, cross-border transfer rules, "
        "and data-subject rights."
    ),
}

# ---------------------------------------------------------------------------
# § Critical / High Privacy Risk Thresholds (spec lines 78-80)
# ---------------------------------------------------------------------------

CRITICAL_PRIVACY_CONDITIONS: list[str] = [
    "No processor/service-provider terms exist where supplier processes customer personal data",
    "No lawful transfer mechanism exists despite cross-border processing",
    "The contract allows unrestricted disclosure or sale/use of personal data beyond the stated purpose",
    "No breach-notification obligation exists",
    "The contract purports to waive mandatory individual rights",
]

HIGH_PRIVACY_CONDITIONS: list[str] = [
    "Roles (controller/processor) are unclear",
    "Subprocessors are unrestricted or not enumerated",
    "Deletion/return language is missing",
    "Security commitments are generic and not auditable",
    "Government-access handling is absent despite high-risk data",
    "The contract is silent on cross-border transfers/offshore support",
]

# ---------------------------------------------------------------------------
# § Baseline Export Control / Sanctions Review Tests (spec lines 81-85)
# ---------------------------------------------------------------------------

BASELINE_EXPORT_TESTS: list[str] = [
    "Test for item/software/technology classification responsibility.",
    "Test for license / authorisation responsibility.",
    "Test for restrictions on export/reexport/transfer/transit/brokering/technical assistance.",
    "Test for end-use and end-user restrictions.",
    "Test for sanctions / restricted-party screening obligations.",
    "Test for no-use provisions in prohibited military/WMD/human-rights-abuse contexts where relevant.",
    "Test for recordkeeping obligations.",
    "Test for audit/cooperation rights.",
    "Test for incident reporting obligations.",
    "Test for suspension/termination rights for violations.",
    (
        "Treat remote support, software updates, cloud access, source-code escrow, model sharing, "
        "engineering collaboration, debug logs containing technical data, and access by foreign "
        "nationals as potential export events requiring analysis to identify if any controlled "
        "items are involved."
    ),
]

# ---------------------------------------------------------------------------
# § Jurisdiction-Specific Export Control Instructions (spec lines 86-90)
# ---------------------------------------------------------------------------

JURISDICTION_EXPORT_INSTRUCTIONS: dict[str, str] = {
    "European Union": (
        "Apply Dual-Use Regulation (EU) 2021/821 and relevant Member State controls. Test export, "
        "brokering, technical assistance, transit, and transfer of dual-use items/software/technology, "
        "plus catch-all / human-rights / cybersurveillance risks where applicable."
    ),
    "United Kingdom": (
        "Apply the UK strategic export-control regime and UK sanctions regulations; test export "
        "licensing, trade controls, brokering/technical-assistance issues, and restricted-party / "
        "destination prohibitions."
    ),
    "United States": (
        "Apply EAR and OFAC sanctions at minimum when U.S.-origin items, U.S. persons, "
        "U.S.-jurisdiction items, dollar flows, or sanctioned-country/party nexus exists. Determine "
        "whether items are subject to the EAR, whether a deemed export/reexport/transfer occurs, "
        "whether end-use/end-user controls apply, and whether OFAC prohibitions independently block "
        "the transaction."
    ),
    "Other jurisdictions": (
        "For Australia, Canada, Singapore, Malaysia, Japan, South Korea, UAE and other listed "
        "jurisdictions: apply local export-control / strategic-goods / sanctions laws if the facts "
        "involve goods, software, technical data, encryption, dual-use items, defense/military use, "
        "or restricted destinations/end users. If internal legal rule library lacks current local "
        "licensing detail, mark ESCALATE for local trade counsel."
    ),
}

# ---------------------------------------------------------------------------
# § Output Format Requirements (spec lines 91-97)
# ---------------------------------------------------------------------------

OUTPUT_FORMAT_SPEC: dict[str, str] = {
    "section_1_executive_result": (
        "Overall outcome = Pass / Conditional Pass / Fail / Escalate. "
        "Provide one concise paragraph summarising the main reasons."
    ),
    "section_2_applicable_jurisdictions": (
        "List privacy and export-control jurisdictions (if applicable only) separately, "
        "with basis for each."
    ),
    "section_3_data_privacy_findings": (
        "For each issue include: Issue ID, clause reference, jurisdiction(s), finding, "
        "risk level, recommended redline, fallback position."
    ),
    "section_4_export_control_findings": (
        "Same structure as privacy findings. Only include if export control is triggered."
    ),
    "section_5_proposed_redlines": (
        "Exact wording where possible; otherwise structured drafting instructions."
    ),
    "section_6_final_decision": (
        "Approve / Approve with conditions / Reject / Escalate."
    ),
}

# ---------------------------------------------------------------------------
# § Decision Logic (spec lines 98-102)
# ---------------------------------------------------------------------------

DECISION_LOGIC: dict[str, str] = {
    "pass": (
        "PASS only if all applicable jurisdictions have been identified, material facts are complete, "
        "no critical/high unresolved issues remain, and required clauses are present or contractually incorporated."
    ),
    "conditional_pass": (
        "CONDITIONAL PASS only if issues are minor/medium and can be closed through tracked changes, "
        "schedules, or standard implementation conditions before signature."
    ),
    "fail": (
        "FAIL if any clause conflicts with mandatory law, a required transfer mechanism / processor "
        "clause / sanctions restriction is absent, or the contract creates unlawful processing/export "
        "exposure that cannot be cured without material redrafting."
    ),
    "escalate": (
        "ESCALATE if facts are incomplete, a listed or restricted party/destination may be involved, "
        "classification/licensing cannot be determined, or a local-law point requires specialist advice "
        "(especially Kuwait, complex U.S. state-sectoral analysis, China outbound transfers, Egypt "
        "permits, Saudi/UAE sectoral rules, or dual-use/technical-assistance cases)."
    ),
}

# ---------------------------------------------------------------------------
# § Model Redline Requirements (spec lines 103-105)
# ---------------------------------------------------------------------------

PRIVACY_REDLINE_MINIMUM: list[str] = [
    "Role allocation (controller/processor/joint controller)",
    "Purpose limitation and documented instructions",
    "Confidentiality obligations for personnel and subprocessors",
    "Security controls (technical and organisational measures)",
    "Subprocessor controls with flow-down obligations",
    "Cross-border transfer mechanism (SCCs, IDTA, adequacy, or equivalent)",
    "Data-subject rights-request assistance",
    "Incident/breach notification and cooperation (with timelines)",
    "Deletion/return of personal data at end of services",
    "Audit/assurance rights or acceptable substitutes",
    "Government-access handling with notice and minimisation obligations",
    "Regulator cooperation obligations",
    "Liability language aligned to risk",
]

EXPORT_CONTROL_REDLINE_MINIMUM: list[str] = [
    "Mutual compliance with applicable export-control and sanctions laws",
    "Classification responsibility for items, software, and technology",
    "License/authorisation responsibility",
    "No export/reexport/transfer/use in violation of law",
    "No dealings with sanctioned/restricted parties or destinations without authorization",
    "No prohibited end use/end user",
    "Prior approval before sharing controlled technical data/source code",
    "Notification if a party becomes listed/restricted",
    "Records retention for export/sanctions compliance",
    "Suspension/termination rights for violations",
]

# ---------------------------------------------------------------------------
# § Appendix A — Jurisdiction Law Matrix (spec lines 112-140)
# ---------------------------------------------------------------------------

JURISDICTION_LAW_MATRIX: dict[str, dict] = {
    "European Union / EEA": {
        "privacy_laws": [
            "GDPR (Regulation (EU) 2016/679)",
            "ePrivacy Directive (and national implementing laws) where relevant",
            "SCCs / adequacy decisions / Chapter V transfer rules",
        ],
        "export_laws": [
            "EU Dual-Use Regulation (EU) 2021/821",
            "Relevant Member State export-control laws",
        ],
    },
    "United Kingdom": {
        "privacy_laws": [
            "UK GDPR",
            "Data Protection Act 2018",
            "ICO international transfer tools: IDTA / UK Addendum to EU SCCs",
        ],
        "export_laws": [
            "UK strategic export-control regime (Export Control Order 2008)",
            "UK sanctions regulations",
        ],
    },
    "India": {
        "privacy_laws": [
            "Digital Personal Data Protection Act, 2023 (DPDPA)",
            "Digital Personal Data Protection Rules, 2025",
        ],
        "export_laws": [
            "Foreign Trade (Development and Regulation) Act",
            "Special Chemicals, Organisms, Materials, Equipment and Technologies (SCOMET) list",
        ],
    },
    "United States": {
        "privacy_laws": [
            "FTC Act (Section 5 — unfair/deceptive practices)",
            "HIPAA (health data)",
            "GLBA (financial data)",
            "COPPA (children's data)",
            "FERPA (educational data)",
            "CCPA / CPRA (California)",
            "Applicable state consumer privacy laws based on nexus and thresholds",
        ],
        "export_laws": [
            "Export Administration Regulations (EAR) — BIS/Commerce",
            "OFAC sanctions (Treasury Department)",
            "ITAR (where defense articles/services implicated)",
        ],
    },
    "Australia": {
        "privacy_laws": [
            "Privacy Act 1988 (Cth) and Australian Privacy Principles (APPs)",
            "Sectoral and state overlays where relevant",
        ],
        "export_laws": [
            "Defence Export Controls (DEC)",
            "Autonomous Sanctions Act 2011",
        ],
    },
    "New Zealand": {
        "privacy_laws": [
            "Privacy Act 2020",
        ],
        "export_laws": [
            "Export Controls and Embargo Act 2019",
        ],
    },
    "Canada": {
        "privacy_laws": [
            "PIPEDA (Personal Information Protection and Electronic Documents Act)",
            "Provincial private-sector privacy statutes (PIPA-AB, PIPA-BC, Law 25-QC) where applicable",
        ],
        "export_laws": [
            "Export and Import Permits Act (EIPA)",
            "Special Economic Measures Act (SEMA) — sanctions",
            "Justice for Victims of Corrupt Foreign Officials Act",
        ],
    },
    "Thailand": {
        "privacy_laws": [
            "Personal Data Protection Act (PDPA)",
        ],
        "export_laws": [
            "Strategic Goods Control Act",
        ],
    },
    "Singapore": {
        "privacy_laws": [
            "Personal Data Protection Act (PDPA) 2012 as amended",
        ],
        "export_laws": [
            "Strategic Goods (Control) Act",
            "MAS sanctions regulations",
        ],
    },
    "Malaysia": {
        "privacy_laws": [
            "Personal Data Protection Act 2010 (PDPA) as amended",
        ],
        "export_laws": [
            "Strategic Trade Act 2010",
        ],
    },
    "Indonesia": {
        "privacy_laws": [
            "Personal Data Protection Law (Law No. 27 of 2022)",
            "Implementing regulations as applicable",
        ],
        "export_laws": [
            "Government Regulation No. 29 of 2021 (Strategic Goods Control)",
        ],
    },
    "South Korea": {
        "privacy_laws": [
            "Personal Information Protection Act (PIPA)",
            "Relevant PIPC regulator guidance",
        ],
        "export_laws": [
            "Foreign Trade Act",
            "Act on Prohibition against Financing for Proliferation of Weapons of Mass Destruction",
        ],
    },
    "Philippines": {
        "privacy_laws": [
            "Data Privacy Act of 2012 (RA 10173)",
            "National Privacy Commission (NPC) issuances",
        ],
        "export_laws": [
            "Strategic Trade Management Act",
        ],
    },
    "Japan": {
        "privacy_laws": [
            "Act on the Protection of Personal Information (APPI) as amended",
        ],
        "export_laws": [
            "Foreign Exchange and Foreign Trade Act (FEFTA)",
        ],
    },
    "UAE (mainland)": {
        "privacy_laws": [
            "Federal Decree-Law No. 45 of 2021 (PDPL)",
            "Sectoral rules: health, banking, telecom, consumer regulations as applicable",
        ],
        "export_laws": [
            "UAE Federal Law on combating terrorism financing and money laundering",
            "UN sanctions as implemented by UAE",
        ],
    },
    "Dubai / DIFC": {
        "privacy_laws": [
            "DIFC Data Protection Law No. 5 of 2020 and implementing regulations (DIFC nexus)",
            "UAE Federal PDPL (mainland Dubai / non-DIFC entities)",
        ],
        "export_laws": [
            "DIFC and UAE sanctions frameworks",
        ],
    },
    "Abu Dhabi / ADGM": {
        "privacy_laws": [
            "ADGM Data Protection Regulations 2021",
        ],
        "export_laws": [
            "ADGM and UAE sanctions frameworks",
        ],
    },
    "China": {
        "privacy_laws": [
            "Personal Information Protection Law (PIPL)",
            "Cybersecurity Law (CSL)",
            "Data Security Law (DSL)",
        ],
        "export_laws": [
            "Export Control Law of the People's Republic of China",
            "Regulations on Administration of Import and Export of Technologies",
        ],
    },
    "Brazil": {
        "privacy_laws": [
            "Lei Geral de Proteção de Dados (LGPD) — Law No. 13.709/2018",
        ],
        "export_laws": [
            "Brazil export-control regulations (Secex/MDIC)",
        ],
    },
    "Colombia": {
        "privacy_laws": [
            "Law 1581 of 2012 and related decrees/guidance",
        ],
        "export_laws": [
            "Colombian export-control and sanctions frameworks",
        ],
    },
    "Saudi Arabia": {
        "privacy_laws": [
            "Personal Data Protection Law (PDPL) and SDAIA regulations/guidance",
        ],
        "export_laws": [
            "Saudi export-control regulations",
            "UN/regional sanctions as implemented by KSA",
        ],
    },
    "Kuwait": {
        "privacy_laws": [
            "Sector-specific privacy rules",
            "Cybercrime Law",
            "Telecom privacy rules",
            "Constitutional privacy provisions",
            "No single comprehensive omnibus statute — mandatory legal escalation required",
        ],
        "export_laws": [
            "Kuwait export-control and sanctions frameworks — escalate to local counsel",
        ],
    },
    "Bahrain": {
        "privacy_laws": [
            "Personal Data Protection Law (Law No. 30 of 2018)",
        ],
        "export_laws": [
            "Bahrain export-control and sanctions frameworks",
        ],
    },
    "Israel": {
        "privacy_laws": [
            "Privacy Protection Law",
            "Privacy Protection (Data Security) Regulations",
            "Cross-border transfer rules and database registration requirements",
        ],
        "export_laws": [
            "Defense Export Control Law",
            "Import and Export Ordinance",
        ],
    },
    "Qatar": {
        "privacy_laws": [
            "Personal Data Privacy Protection Law (Law No. 13 of 2016)",
            "QFC Data Protection Regulations (QFC nexus)",
        ],
        "export_laws": [
            "Qatar export-control and sanctions frameworks",
        ],
    },
    "Oman": {
        "privacy_laws": [
            "Personal Data Protection Law (Royal Decree 6/2022)",
            "Implementing rules where applicable",
        ],
        "export_laws": [
            "Oman export-control and sanctions frameworks",
        ],
    },
    "Egypt": {
        "privacy_laws": [
            "Personal Data Protection Law No. 151 of 2020",
            "Executive regulations where applicable",
        ],
        "export_laws": [
            "Egyptian export-control regulations and licences/permits",
        ],
    },
    "South Africa": {
        "privacy_laws": [
            "Protection of Personal Information Act (POPIA)",
        ],
        "export_laws": [
            "National Conventional Arms Control Act",
            "South African sanctions regulations",
        ],
    },
}


def build_jurisdiction_law_summary() -> str:
    """Return a compact string listing all 28 jurisdictions and their primary privacy laws.
    Used to inject into agent system prompts as a reference table.
    """
    lines: list[str] = ["JURISDICTION → PRIMARY PRIVACY LAWS:"]
    for jurisdiction, rules in JURISDICTION_LAW_MATRIX.items():
        primary = rules["privacy_laws"][0] if rules["privacy_laws"] else "See local law"
        lines.append(f"  • {jurisdiction}: {primary}")
    return "\n".join(lines)


def build_operating_rules_block() -> str:
    """Return operating rules formatted for inclusion in a system prompt."""
    lines = ["NON-NEGOTIABLE OPERATING RULES:"]
    for i, rule in enumerate(OPERATING_RULES, 1):
        lines.append(f"{i}. {rule}")
    return "\n".join(lines)


def build_guardrails_block() -> str:
    """Return guardrails formatted for inclusion in a system prompt."""
    lines = ["GUARDRAILS:"]
    for rule in GUARDRAILS:
        lines.append(f"• {rule}")
    return "\n".join(lines)


def build_privacy_tests_block() -> str:
    """Return all 15 baseline privacy tests for inclusion in agent prompts."""
    lines = ["BASELINE DATA PRIVACY REVIEW TESTS (apply all that are relevant):"]
    for i, test in enumerate(BASELINE_PRIVACY_TESTS, 1):
        lines.append(f"{i}. {test}")
    return "\n".join(lines)


def build_jurisdiction_privacy_instructions(jurisdictions: list[str] | None = None) -> str:
    """Return jurisdiction-specific privacy instructions, optionally filtered."""
    target = jurisdictions or list(JURISDICTION_PRIVACY_INSTRUCTIONS.keys())
    lines = ["JURISDICTION-SPECIFIC PRIVACY INSTRUCTIONS (apply the relevant jurisdiction's instructions):"
             "\nFor EACH jurisdiction identified as applicable to this contract, apply ALL the instructions below for that jurisdiction."]
    for j in target:
        if j in JURISDICTION_PRIVACY_INSTRUCTIONS:
            lines.append(f"\n[{j}]\n{JURISDICTION_PRIVACY_INSTRUCTIONS[j]}")
    return "\n".join(lines)


def build_jurisdiction_special_rules_block() -> str:
    """Return all 28 jurisdiction-specific structural and procedural special rules.
    This covers nuances like dual regimes, mandatory escalation, phased laws,
    sectoral overlays, and multi-state analysis requirements.
    Used to inject into agent prompts so no jurisdiction is treated simplistically.
    """
    lines = [
        "JURISDICTION-SPECIFIC STRUCTURAL RULES AND NUANCES",
        "(Apply the rules for EVERY jurisdiction that appears in the contract or is implicated by the facts.)",
        "(Do not apply only the three examples below — ALL jurisdictions have specific rules.)",
    ]
    for jurisdiction, rule in JURISDICTION_SPECIAL_RULES.items():
        lines.append(f"\n[{jurisdiction}]\n{rule}")
    return "\n".join(lines)


def build_full_jurisdiction_reference() -> str:
    """Build a comprehensive jurisdiction reference block for agent prompts.
    Combines: law table + special structural rules + jurisdiction-specific instructions.
    This is the master block that ensures no jurisdiction is missed or simplified.
    """
    sections = [
        build_jurisdiction_law_summary(),
        "",
        build_jurisdiction_special_rules_block(),
        "",
        build_jurisdiction_privacy_instructions(),
    ]
    return "\n".join(sections)


def detect_export_control_trigger(text: str) -> bool:
    """Return True if the contract text contains any export-control trigger keywords."""
    text_lower = text.lower()
    for keyword in EXPORT_TRIGGER_KEYWORDS:
        if keyword.lower() in text_lower:
            return True
    return False


def get_laws_for_jurisdiction(jurisdiction: str) -> dict:
    """Return the law matrix entry for a jurisdiction (case-insensitive partial match)."""
    juris_lower = jurisdiction.lower()
    for key, value in JURISDICTION_LAW_MATRIX.items():
        if juris_lower in key.lower() or key.lower() in juris_lower:
            return value
    return {"privacy_laws": [], "export_laws": []}
