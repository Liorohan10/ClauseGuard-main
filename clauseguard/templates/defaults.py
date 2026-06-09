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
}
