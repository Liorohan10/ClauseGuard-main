import logging
import asyncio
from pathlib import Path

from clauseguard.openai_assistant import OpenAILegalAssistant

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

async def main():
    assistant = OpenAILegalAssistant()
    path = Path("sample_contracts/sample_nda.txt")
    if not path.exists():
        print("Sample file not found:", path)
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    review = await assistant.analyze_contract_text(text, filename=path.name)
    print(review.model_dump_json(indent=2))

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as e:
        import traceback

        print("Error running sample review:")
        traceback.print_exc()
