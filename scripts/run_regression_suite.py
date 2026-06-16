import asyncio
import logging
import sys
from pathlib import Path
from clauseguard.openai_assistant import OpenAILegalAssistant

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("regression_suite")

async def run_test_case(assistant, file_path):
    print(f"\n========================================\nAnalyzing: {file_path}")
    path = Path(file_path)
    if not path.exists():
        print(f"Error: File {file_path} not found.")
        sys.exit(1)
    
    review = await assistant.analyze_contract(str(path))
    print(f"Summary for {path.name}: {review.summary[:200]}...")
    findings_by_control = {f.control: f for f in review.compliance_findings}
    return findings_by_control

async def main():
    assistant = OpenAILegalAssistant()
    
    # 1. Interflex DPA
    interflex_findings = await run_test_case(assistant, "cd4486a8-779d-436d-a128-7c233fcf5b53.pdf")
    
    print("\n--- Interflex DPA Findings ---")
    for control, f in interflex_findings.items():
        print(f"Control: {control} | Status: {f.status} | Confidence: {f.confidence:.2f}")
        
    # Assertions for Interflex DPA
    # DPA Requirement marked PRESENT
    dpa_req = interflex_findings.get("Data Processing Agreement (DPA) Requirement")
    assert dpa_req is not None, "Data Processing Agreement (DPA) Requirement not found in Interflex DPA findings"
    assert dpa_req.status == "PRESENT", f"Interflex DPA Requirement expected PRESENT, got {dpa_req.status}"
    
    # Data Retention & Deletion marked PRESENT
    deletion = interflex_findings.get("Data Retention & Deletion")
    assert deletion is not None, "Data Retention & Deletion not found in Interflex DPA findings"
    assert deletion.status == "PRESENT", f"Interflex Deletion expected PRESENT, got {deletion.status}"
    
    # Data Subject Rights Access/Rectification or Erasure/Portability marked PRESENT
    ds_access = interflex_findings.get("Data Subject Rights - Access/Rectification")
    ds_erasure = interflex_findings.get("Data Subject Rights - Erasure/Portability")
    assert ds_access is not None or ds_erasure is not None, "Data Subject Rights controls not found in Interflex DPA findings"
    assert (ds_access and ds_access.status == "PRESENT") or (ds_erasure and ds_erasure.status == "PRESENT"), \
        f"Interflex Data Subject Rights expected at least one PRESENT, got Access: {ds_access.status if ds_access else None}, Erasure: {ds_erasure.status if ds_erasure else None}"
        
    # TOMs marked PRESENT
    toms = interflex_findings.get("Technical & Organizational Security Measures")
    assert toms is not None, "Technical & Organizational Security Measures not found in Interflex DPA findings"
    assert toms.status == "PRESENT", f"Interflex TOMs expected PRESENT, got {toms.status}"
    
    print(">> Interflex DPA assertions passed!")
    print("\n========================================")
    print("Interflex DPA Regression Test Case Passed Successfully!")
    print("========================================")

if __name__ == "__main__":
    asyncio.run(main())
