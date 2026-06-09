from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import logging

from clauseguard.models.openai_legal import NDAGenerationOutput
from clauseguard.openai_assistant import OpenAILegalAssistant
from scripts.generate_legal_pdf import generate_legal_pdf


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ClauseGuard OpenAI legal assistant")
    subparsers = parser.add_subparsers(dest="command", required=True)

    review = subparsers.add_parser("review", help="Run a full contract review and generate a PDF report")
    review.add_argument("file_path", help="Path to the contract file")
    review.add_argument("--output", help="Optional output PDF path")

    risks = subparsers.add_parser("risks", help="Run risk analysis only")
    risks.add_argument("file_path", help="Path to the contract file")

    nda = subparsers.add_parser("nda", help="Generate an NDA from a short description")
    nda.add_argument("description", nargs=argparse.REMAINDER, help="Description of the NDA to draft")

    return parser


async def _run_review(assistant: OpenAILegalAssistant, file_path: str, output: str | None) -> None:
    review = await assistant.analyze_contract(file_path)
    pdf_path = generate_legal_pdf(review, output_path=output)
    print(json.dumps(review.model_dump(), indent=2))
    print(f"PDF report written to {pdf_path}")


async def _run_risks(assistant: OpenAILegalAssistant, file_path: str) -> None:
    risks = await assistant.assess_risks(file_path)
    print(risks.model_dump_json(indent=2))


async def _run_nda(assistant: OpenAILegalAssistant, description: str) -> None:
    nda = await assistant.generate_nda(description)
    print(NDAGenerationOutput.model_validate(nda.model_dump()).model_dump_json(indent=2))


async def main_async(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    assistant = OpenAILegalAssistant()

    if args.command == "review":
        await _run_review(assistant, args.file_path, args.output)
    elif args.command == "risks":
        await _run_risks(assistant, args.file_path)
    elif args.command == "nda":
        description = " ".join(args.description).strip()
        if not description:
            raise SystemExit("Please provide a description for the NDA.")
        await _run_nda(assistant, description)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
