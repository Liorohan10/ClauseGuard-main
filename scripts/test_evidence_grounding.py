from clauseguard.openai_assistant import OpenAILegalAssistant


def assistant() -> OpenAILegalAssistant:
    return object.__new__(OpenAILegalAssistant)


def test_atlassian_style_dpa_controls_pass() -> None:
    reviewer = assistant()
    security = reviewer._assessment_to_finding(
        {
            "control": "Technical & Organizational Security Measures",
            "applicable": True,
            "applicability_reason": "DPA processes customer personal data.",
            "contract_evidence": [],
            "law_evidence": ["GDPR Art. 32"],
            "evidence_status": "ABSENT",
            "adequacy_evaluation": "Semantic evidence satisfies Article 32.",
            "finding": "Security measures are present.",
            "regulatory_basis": "GDPR Art. 32",
            "confidence": 0.9,
        },
        {
            "semantic_contract_evidence": [
                "Atlassian has implemented and will maintain appropriate technical and organizational measures designed to protect the security, confidentiality, integrity and availability of Customer Data and protect against Security Incidents."
            ]
        },
        [],
    )
    breach = reviewer._assessment_to_finding(
        {
            "control": "Data Breach Notification Timeframe",
            "applicable": True,
            "applicability_reason": "DPA processes customer personal data.",
            "contract_evidence": [],
            "law_evidence": ["GDPR Art. 33"],
            "evidence_status": "ABSENT",
            "adequacy_evaluation": "Semantic evidence satisfies breach timing.",
            "finding": "Breach timing is present.",
            "regulatory_basis": "GDPR Art. 33",
            "confidence": 0.9,
        },
        {
            "semantic_contract_evidence": [
                "Atlassian must notify Customer without undue delay and where feasible within 72 hours after becoming aware of a Security Incident."
            ]
        },
        [],
    )
    assert security["status"] == "pass"
    assert breach["status"] == "pass"


def test_inapplicable_consent_is_not_a_missing_protection() -> None:
    reviewer = assistant()
    consent = reviewer._assessment_to_finding(
        {
            "control": "Consent Management",
            "applicable": False,
            "applicability_reason": "Processor DPA does not use consent as the lawful basis.",
            "contract_evidence": [],
            "law_evidence": ["GDPR Art. 7"],
            "evidence_status": "NOT_APPLICABLE",
            "adequacy_evaluation": "Not triggered.",
            "finding": "Consent management is not applicable.",
            "regulatory_basis": "GDPR Art. 7",
            "confidence": 0.9,
        },
        {},
        [],
    )
    assert consent["status"] == "not-applicable"
    assert consent["severity"] == "info"
    assert consent["target_clause"] == "Not applicable"


if __name__ == "__main__":
    test_atlassian_style_dpa_controls_pass()
    test_inapplicable_consent_is_not_a_missing_protection()
    print("Evidence-grounding benchmark checks passed.")
