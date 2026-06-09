from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from clauseguard.api.review import _build_review_record, _build_workbook
from clauseguard.openai_assistant import OpenAILegalAssistant

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


async def main() -> None:
    assistant = OpenAILegalAssistant()
    sample = Path("sample_contracts/sample_nda.txt")
    text = sample.read_text(encoding="utf-8", errors="replace")
    review = await assistant.analyze_contract_text(text, filename=sample.name)
    record = _build_review_record("sample-nda", sample.name, review)
    workbook = _build_workbook(review, sample.name, record["reviewed_at"])
    output_path = Path("sample_review_export.xlsx")
    output_path.write_bytes(workbook.getvalue())
    print(f"Wrote {output_path} ({output_path.stat().st_size} bytes)")


if __name__ == "__main__":
    asyncio.run(main())
