import asyncio
import logging
import sys
from clauseguard.openai_assistant import OpenAILegalAssistant

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("test_accuracy")

async def test_github_dpa_retention_accuracy():
    assistant = OpenAILegalAssistant()
    
    # Define contract text with Clause 9.A (Storage/Transfer) and Clause 8 (Retention/Deletion)
    contract_text = (
        "[other] GitHub Data Processing Addendum (DPA)\n\n"
        "[data_transfer] Section 9.A: Data Transfer and Storage\n"
        "GitHub may store and process Customer Personal Data in the United States or any other country in which GitHub "
        "or its subprocessors maintain facilities. This storage is subject to the standard contractual clauses and security "
        "measures described herein.\n\n"
        "[data_retention] Section 8: Retention and Deletion\n"
        "Upon termination or expiration of the Agreement, GitHub will return or delete all Customer Personal Data "
        "within 30 days, unless applicable law requires continued retention of such personal data."
    )
    
    source_context = (
        "clause_id=clause_0 | page=1 | section= | type=other | offsets=0-45 | excerpt=GitHub Data Processing Addendum (DPA)\n"
        "clause_id=clause_1 | page=1 | section=9.A | type=data_transfer | offsets=47-280 | excerpt=Section 9.A: Data Transfer and Storage\\nGitHub may store and process Customer Personal Data...\n"
        "clause_id=clause_2 | page=1 | section=8 | type=data_retention | offsets=282-500 | excerpt=Section 8: Retention and Deletion\\nUpon termination or expiration of the Agreement..."
    )
    
    logger.info("Starting analysis of mock GitHub DPA...")
    review = await assistant.analyze_contract_text(
        contract_text=contract_text,
        filename="mock_github_dpa.txt",
        source_context=source_context
    )
    
    # Print the findings
    print("\n--- Compliance Findings ---")
    retention_finding = None
    for f in review.compliance_findings:
        print(f"Control: {f.control} | Status: {f.status} | Target Clause: {f.target_clause} | Excerpt: {f.contract_excerpt[:100]}...")
        if f.control == "Data Retention & Deletion":
            retention_finding = f
            
    assert retention_finding is not None, "Data Retention & Deletion control not found in review findings"
    
    # Assert correct section targeting
    target = str(retention_finding.target_clause).strip()
    excerpt = str(retention_finding.contract_excerpt).strip()
    
    logger.info(f"Data Retention & Deletion mapped target_clause: '{target}'")
    logger.info(f"Data Retention & Deletion mapped contract_excerpt: '{excerpt}'")
    
    # Assertions
    assert target == "8", f"Expected target_clause to be '8', but got '{target}'"
    assert "9.A" not in target, f"Target clause erroneously contains '9.A' (proximity false positive)"
    assert "9.A" not in excerpt, f"Contract excerpt erroneously contains text from '9.A'"
    assert "delete" in excerpt.lower() or "return" in excerpt.lower(), "Excerpt must contain retention/deletion language"
    assert retention_finding.status == "PRESENT", f"Expected status PRESENT, but got {retention_finding.status}"
    
    logger.info(">> test_github_dpa_retention_accuracy PASSED successfully!")

if __name__ == "__main__":
    try:
        asyncio.run(test_github_dpa_retention_accuracy())
    except AssertionError as ae:
        logger.error(f"Assertion failed: {ae}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Test failed with unexpected exception: {e}")
        sys.exit(1)
