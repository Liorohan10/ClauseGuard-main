import asyncio
import logging
from pathlib import Path
import sys

# Add project root to PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from clauseguard.search import async_web_search, format_search_results
from clauseguard.openai_assistant import OpenAILegalAssistant

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

async def test_ddg_search():
    print("--- TESTING DUCKDUCKGO WEB SEARCH ---")
    query = "GDPR Article 28 data processor contract requirements"
    results = await async_web_search(query, max_results=3)
    print(f"Query: {query}")
    print(f"Results Count: {len(results)}")
    for idx, r in enumerate(results, 1):
        print(f"Result {idx}: {r['title']} ({r['url']})")
    print("Formatted output snippet:")
    print(format_search_results(results[:1]))

async def test_assistant_with_search():
    print("\n--- TESTING ASSISTANT WITH WEB SEARCH PIPELINE ---")
    assistant = OpenAILegalAssistant()
    
    # We will test against the violations contract to trigger search (since it has failing findings)
    contract_path = Path("test_contract_violations.txt")
    if not contract_path.exists():
        print("Violation contract not found at root.")
        return
        
    text = contract_path.read_text(encoding="utf-8", errors="replace")
    print("Analyzing contract and running verification pipeline...")
    review = await assistant.analyze_contract_text(text, filename=contract_path.name)
    
    print("\n--- PIPELINE RUN SUCCESSFUL ---")
    print(f"Safety Score: {review.contract_safety_score}")
    print(f"Final Decision: {review.final_decision.outcome if review.final_decision else 'None'}")
    print(f"Summary: {review.summary}")
    print(f"Number of verified findings: {len(review.compliance_findings)}")
    print("First verified finding:")
    if review.compliance_findings:
        f = review.compliance_findings[0]
        print(f"ID: {f.issue_id} | Severity: {f.severity} | Requirement: {f.requirement}")
        print(f"Explanation: {f.explanation}")

async def main():
    await test_ddg_search()
    await test_assistant_with_search()

if __name__ == '__main__':
    asyncio.run(main())
