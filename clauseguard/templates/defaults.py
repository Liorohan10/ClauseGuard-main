from clauseguard.models.clause import ClauseType
from clauseguard.models.template import ClauseTemplate

DEFAULT_TEMPLATES: dict[ClauseType, ClauseTemplate] = {
    ClauseType.INDEMNITY: ClauseTemplate(
        clause_type=ClauseType.INDEMNITY,
        name="Mutual Indemnification",
        template_text=(
            "Each party shall indemnify, defend, and hold harmless the other party and its "
            "officers, directors, employees, and agents from and against any and all claims, "
            "damages, losses, liabilities, costs, and expenses (including reasonable attorneys' "
            "fees) arising out of or relating to (a) any breach of this Agreement by the "
            "indemnifying party, or (b) the indemnifying party's negligence or willful misconduct."
        ),
        key_requirements=[
            "Mutual indemnification (both parties covered)",
            "Covers breach of agreement",
            "Covers negligence and willful misconduct",
            "Includes attorneys' fees",
            "Covers officers, directors, employees, and agents",
        ],
        required=True,
    ),
    ClauseType.LIABILITY_CAP: ClauseTemplate(
        clause_type=ClauseType.LIABILITY_CAP,
        name="Limitation of Liability",
        template_text=(
            "IN NO EVENT SHALL EITHER PARTY'S TOTAL AGGREGATE LIABILITY UNDER THIS AGREEMENT "
            "EXCEED THE TOTAL AMOUNTS PAID OR PAYABLE BY CLIENT UNDER THIS AGREEMENT DURING "
            "THE TWELVE (12) MONTH PERIOD PRECEDING THE EVENT GIVING RISE TO THE CLAIM. "
            "IN NO EVENT SHALL EITHER PARTY BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, "
            "CONSEQUENTIAL, OR PUNITIVE DAMAGES."
        ),
        key_requirements=[
            "Cap tied to fees paid in preceding 12 months",
            "Exclusion of indirect/consequential damages",
            "Applies to both parties (mutual)",
            "Carve-outs for indemnification obligations",
        ],
        required=True,
    ),
    ClauseType.TERMINATION: ClauseTemplate(
        clause_type=ClauseType.TERMINATION,
        name="Termination for Convenience and Cause",
        template_text=(
            "Either party may terminate this Agreement (a) for convenience upon thirty (30) "
            "days' prior written notice, or (b) immediately upon written notice if the other "
            "party materially breaches this Agreement and fails to cure such breach within "
            "fifteen (15) days after receiving written notice thereof. Upon termination, all "
            "outstanding fees shall become immediately due and payable."
        ),
        key_requirements=[
            "Termination for convenience with 30-day notice",
            "Termination for cause with cure period",
            "Written notice requirement",
            "Payment obligations survive termination",
        ],
        required=True,
    ),
    ClauseType.CONFIDENTIALITY: ClauseTemplate(
        clause_type=ClauseType.CONFIDENTIALITY,
        name="Mutual Confidentiality",
        template_text=(
            'Each party agrees to hold in strict confidence all Confidential Information '
            'received from the other party. "Confidential Information" means any non-public '
            "information disclosed by either party, whether orally, in writing, or electronically, "
            "that is designated as confidential or that reasonably should be understood to be "
            "confidential. The receiving party shall not disclose Confidential Information to "
            "any third party without prior written consent and shall use it only for purposes "
            "of performing under this Agreement. These obligations shall survive for three (3) "
            "years after termination."
        ),
        key_requirements=[
            "Mutual obligations (both parties)",
            "Clear definition of Confidential Information",
            "Non-disclosure to third parties",
            "Use limited to Agreement purposes",
            "Survival period of at least 3 years",
        ],
        required=True,
    ),
    ClauseType.IP_ASSIGNMENT: ClauseTemplate(
        clause_type=ClauseType.IP_ASSIGNMENT,
        name="Intellectual Property Ownership",
        template_text=(
            "All intellectual property rights in any work product, deliverables, or inventions "
            "created by Provider in the performance of this Agreement shall be owned by Client. "
            "Provider hereby assigns to Client all right, title, and interest in such work product. "
            "Provider retains ownership of its pre-existing intellectual property and grants "
            "Client a non-exclusive, perpetual license to use any such pre-existing IP incorporated "
            "into deliverables."
        ),
        key_requirements=[
            "Work product owned by Client",
            "Assignment of all rights, title, and interest",
            "Pre-existing IP carved out and retained by Provider",
            "License for pre-existing IP in deliverables",
        ],
        required=False,
    ),
    ClauseType.GOVERNING_LAW: ClauseTemplate(
        clause_type=ClauseType.GOVERNING_LAW,
        name="Governing Law and Jurisdiction",
        template_text=(
            "This Agreement shall be governed by and construed in accordance with the laws "
            "of the State of Delaware, without regard to its conflict of laws principles. "
            "Any dispute arising under this Agreement shall be resolved exclusively in the "
            "state or federal courts located in Wilmington, Delaware, and each party consents "
            "to the personal jurisdiction of such courts."
        ),
        key_requirements=[
            "Specifies governing jurisdiction",
            "Excludes conflict of laws principles",
            "Exclusive venue for dispute resolution",
            "Consent to personal jurisdiction",
        ],
        required=True,
    ),
    ClauseType.DATA_PROTECTION: ClauseTemplate(
        clause_type=ClauseType.DATA_PROTECTION,
        name="Data Protection and Privacy",
        template_text=(
            "Each party shall comply with all applicable data protection and privacy laws, "
            "including but not limited to the GDPR and CCPA, with respect to any personal data "
            "processed under this Agreement. The parties shall enter into a Data Processing "
            "Agreement (DPA) as required by applicable law. Each party shall implement appropriate "
            "technical and organizational measures to protect personal data against unauthorized "
            "access, loss, or destruction."
        ),
        key_requirements=[
            "Compliance with GDPR and CCPA",
            "Data Processing Agreement (DPA) requirement",
            "Technical and organizational security measures",
            "Covers all personal data processed under agreement",
        ],
        required=True,
    ),
    ClauseType.FORCE_MAJEURE: ClauseTemplate(
        clause_type=ClauseType.FORCE_MAJEURE,
        name="Force Majeure",
        template_text=(
            "Neither party shall be liable for any failure or delay in performing its obligations "
            "under this Agreement to the extent such failure or delay results from circumstances "
            "beyond the party's reasonable control, including but not limited to acts of God, "
            "natural disasters, war, terrorism, pandemics, government actions, or failures of "
            "third-party telecommunications or power supply. The affected party shall provide "
            "prompt written notice and use reasonable efforts to mitigate the impact. If the "
            "force majeure event continues for more than sixty (60) days, either party may "
            "terminate this Agreement upon written notice."
        ),
        key_requirements=[
            "Covers events beyond reasonable control",
            "Lists specific force majeure events",
            "Requires prompt written notice",
            "Duty to mitigate",
            "Termination right after extended period (60+ days)",
        ],
        required=False,
    ),
    ClauseType.EXPORT_CONTROL: ClauseTemplate(
        clause_type=ClauseType.EXPORT_CONTROL,
        name="Export Control Compliance",
        template_text=(
            "Each party shall comply with all applicable export control laws and regulations, "
            "including without limitation the U.S. Export Administration Regulations (EAR), "
            "OFAC sanctions programs, EU Dual-Use Regulation (EU) 2021/821, and applicable "
            "national export-control laws. No party shall export, re-export, transfer, or "
            "disclose any controlled items, software, source code, or technical data in "
            "violation of applicable law. Each party shall maintain an effective export "
            "compliance programme, including restricted-party screening, classification "
            "of items, and obtaining required licenses or authorisations prior to any "
            "export or transfer. Each party shall promptly notify the other upon becoming "
            "aware of any potential violation or if it becomes subject to any export-control "
            "restriction. Either party may suspend performance if required to comply with "
            "applicable export-control or sanctions laws."
        ),
        key_requirements=[
            "Mutual compliance with all applicable export-control and sanctions laws",
            "Classification responsibility for items, software, and technology",
            "License/authorisation responsibility before export or transfer",
            "No export/reexport/transfer/use in violation of applicable law",
            "Restricted-party and sanctions screening obligations",
            "No dealings with sanctioned/restricted parties or destinations without authorization",
            "No prohibited end use/end user (WMD, military, human-rights-abuse contexts)",
            "Notification if a party becomes listed or restricted",
            "Records retention for export-compliance documentation",
            "Suspension/termination rights for violations",
        ],
        required=False,
    ),
    ClauseType.SANCTIONS: ClauseTemplate(
        clause_type=ClauseType.SANCTIONS,
        name="Sanctions and Restricted-Party Screening",
        template_text=(
            "Each party represents and warrants that it is not, and its officers, directors, "
            "shareholders, and beneficial owners are not, a Sanctioned Person or located in "
            "a Sanctioned Country. 'Sanctioned Person' means any individual or entity "
            "appearing on the OFAC SDN List, the EU Consolidated Sanctions List, the UN "
            "Consolidated Sanctions List, the UK Financial Sanctions List, or any equivalent "
            "national or international restricted-party list. Each party shall conduct "
            "restricted-party screening before engaging any new subcontractor, distributor, "
            "or counterparty in connection with this Agreement. Each party shall immediately "
            "notify the other upon becoming a Sanctioned Person or subject to sanctions-related "
            "restrictions. Either party may terminate this Agreement immediately upon written "
            "notice if the other becomes a Sanctioned Person or if continuing performance "
            "would violate applicable sanctions laws."
        ),
        key_requirements=[
            "Representation that parties are not sanctioned persons or in sanctioned countries",
            "Restricted-party screening before engaging subcontractors or counterparties",
            "Covers OFAC SDN, EU, UN, and UK sanctions lists as minimum",
            "Immediate notification upon becoming sanctioned or restricted",
            "Termination right if a party becomes sanctioned",
        ],
        required=False,
    ),
    ClauseType.DATA_TRANSFER: ClauseTemplate(
        clause_type=ClauseType.DATA_TRANSFER,
        name="Cross-Border Data Transfer Safeguards",
        template_text=(
            "Where personal data is transferred outside the European Economic Area, the United "
            "Kingdom, or any other jurisdiction requiring a transfer mechanism, the parties "
            "shall ensure such transfers are made only: (a) to countries recognised as providing "
            "an adequate level of protection; (b) subject to Standard Contractual Clauses (SCCs) "
            "approved by the European Commission, the UK IDTA, or equivalent transfer tool; or "
            "(c) on the basis of another applicable lawful transfer mechanism. The parties shall "
            "conduct and document a Transfer Impact Assessment (TIA) where required by applicable "
            "law or regulator guidance before any restricted transfer. The data importer shall "
            "notify the data exporter promptly if it cannot comply with the applicable transfer "
            "safeguards, in which case the data exporter may suspend the transfer."
        ),
        key_requirements=[
            "Cross-border transfers only to adequate countries or under approved transfer mechanisms",
            "Standard Contractual Clauses (SCCs) or UK IDTA where required",
            "Transfer Impact Assessment (TIA) documentation where required",
            "Applies to EEA, UK, and other jurisdictions with transfer restrictions",
            "Suspension right if transfer safeguards cannot be maintained",
        ],
        required=True,
    ),
    ClauseType.SUBPROCESSOR: ClauseTemplate(
        clause_type=ClauseType.SUBPROCESSOR,
        name="Subprocessor Authorization and Flow-Down",
        template_text=(
            "The service provider shall not engage any subprocessor to process customer personal "
            "data without the customer's prior written authorisation, or where a general "
            "authorisation is granted, prior written notice with sufficient time to allow "
            "the customer to object. The service provider shall: (a) impose data protection "
            "obligations on each subprocessor equivalent to those in this Agreement, including "
            "appropriate security measures and transfer safeguards; (b) remain fully liable to "
            "the customer for any failure by a subprocessor to fulfil its data protection "
            "obligations; and (c) maintain and provide upon request a current list of engaged "
            "subprocessors. The customer may object to a new subprocessor on reasonable "
            "data-protection grounds, in which case the parties shall engage in good faith "
            "to resolve the objection, and the customer may terminate if the issue cannot "
            "be resolved."
        ),
        key_requirements=[
            "Prior written authorisation or notice before engaging subprocessors",
            "Equivalent data protection obligations flowed down to all subprocessors",
            "Service provider remains fully liable for subprocessor acts",
            "Current subprocessor list maintained and available on request",
            "Customer objection right for new subprocessors on data protection grounds",
            "Termination right if subprocessor objection cannot be resolved",
        ],
        required=True,
    ),
    ClauseType.BREACH_NOTIFICATION: ClauseTemplate(
        clause_type=ClauseType.BREACH_NOTIFICATION,
        name="Data Breach Notification and Incident Response",
        template_text=(
            "The service provider shall notify the customer without undue delay, and in any "
            "event within 24 hours of becoming aware of a personal data breach (or such shorter "
            "period as required by applicable law). Notification shall include: (a) a description "
            "of the nature of the breach, including categories and approximate number of data "
            "subjects and records affected; (b) the name and contact details of the data "
            "protection officer or other point of contact; (c) the likely consequences of the "
            "breach; and (d) measures taken or proposed to address the breach and mitigate its "
            "possible adverse effects. The service provider shall cooperate fully with the "
            "customer and provide all information and assistance reasonably required for the "
            "customer to fulfil its own notification obligations to regulators and data subjects "
            "within applicable timelines (including GDPR's 72-hour supervisory authority "
            "notification deadline). The service provider shall not make any public disclosure "
            "relating to a personal data breach without the customer's prior written consent, "
            "except as required by law."
        ),
        key_requirements=[
            "Notification within 24 hours of becoming aware (supports customer's 72-hour regulatory deadline)",
            "Minimum notification content: nature, categories, numbers affected, contacts, consequences, measures",
            "Full cooperation with customer's regulatory and data-subject notification obligations",
            "No public disclosure without customer prior written consent (unless legally required)",
            "Evidence preservation and investigation cooperation",
        ],
        required=True,
    ),
    ClauseType.DATA_SUBJECT_RIGHTS: ClauseTemplate(
        clause_type=ClauseType.DATA_SUBJECT_RIGHTS,
        name="Data Subject Rights Assistance",
        template_text=(
            "The service provider shall provide reasonable assistance to the customer in "
            "fulfilling its obligations to respond to data subject requests for: access; "
            "correction or rectification; erasure or deletion; restriction of processing; "
            "data portability; objection to processing; and any other rights afforded to "
            "data subjects under applicable privacy law. The service provider shall promptly "
            "forward to the customer any data subject request received directly and shall "
            "not respond to such requests independently except as instructed by the customer "
            "or as required by applicable law. The service provider shall provide assistance "
            "within such time as allows the customer to respond within applicable statutory "
            "deadlines. Any costs reasonably incurred by the service provider in providing "
            "such assistance shall be borne by the customer unless otherwise agreed."
        ),
        key_requirements=[
            "Assistance with all applicable data subject rights (access, rectification, erasure, restriction, portability, objection)",
            "Prompt forwarding of any data subject requests received directly",
            "No independent responses to data subjects without customer instruction",
            "Assistance within timelines supporting customer's statutory response obligations",
            "Covers all applicable jurisdictions' rights frameworks",
        ],
        required=True,
    ),
}
