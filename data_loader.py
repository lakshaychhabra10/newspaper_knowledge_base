"""Download and OCR Economic Times newspaper PDFs."""

import argparse
import asyncio
import os
import re
from pathlib import Path

import pytesseract
from dotenv import load_dotenv
from pdf2image import convert_from_path
from PIL import Image
from tqdm import tqdm

load_dotenv()

DATA_DIR = Path("data")
SESSION_NAME = "telegram_session"
DATE_PATTERN = re.compile(r"(\d{2}-\d{2}-\d{4})")

Image.MAX_IMAGE_PIXELS = 150_000_000


def normalize_filename(name: str) -> str:
    """Map 'ET Delhi 11-06-2026.pdf' -> 'Delhi_ET_11-06-2026.pdf'."""
    match = DATE_PATTERN.search(name)
    if match:
        return f"Delhi_ET_{match.group(1)}.pdf"
    return name


def ocr_pdf(path: Path, dpi: int = 150) -> Path:
    txt_path = path.with_suffix(".txt")
    if txt_path.exists():
        return txt_path

    pages = convert_from_path(path, dpi=dpi)
    page_texts = [
        pytesseract.image_to_string(page)
        for page in tqdm(pages, desc=path.name, leave=False)
    ]
    txt_path.write_text("\n\n".join(page_texts), encoding="utf-8")
    return txt_path


def ocr_pdfs(pdf_paths: list[Path]) -> list[Path]:
    if not pdf_paths:
        return []
    return [ocr_pdf(path) for path in tqdm(pdf_paths, desc="OCR PDFs")]


def pdfs_needing_ocr() -> list[Path]:
    return sorted(
        path for path in DATA_DIR.glob("*.pdf")
        if not path.with_suffix(".txt").exists()
    )


def manual_load(limit: int | None = None) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    to_process = pdfs_needing_ocr()
    if limit is not None:
        to_process = to_process[:limit]

    if not to_process:
        print("No PDFs need OCR (all have matching .txt files).")
        return

    print(f"OCR {len(to_process)} PDF(s)...")
    ocr_pdfs(to_process)
    print("Done.")


def get_telegram_filename(message) -> str | None:
    from telethon.tl.types import DocumentAttributeFilename

    if not message.document:
        return None
    for attr in message.document.attributes:
        if isinstance(attr, DocumentAttributeFilename):
            return attr.file_name
    return None


async def download_from_telegram(limit: int | None = None) -> list[Path]:
    from telethon import TelegramClient

    api_id = int(os.environ["TELEGRAM_API_ID"])
    api_hash = os.environ["TELEGRAM_API_HASH"]
    phone = os.environ.get("TELEGRAM_PHONE")
    group = os.environ["TELEGRAM_GROUP"]
    prefix = os.getenv("TELEGRAM_FILE_PREFIX", "ET Delhi")

    DATA_DIR.mkdir(exist_ok=True)
    downloaded: list[Path] = []

    async with TelegramClient(SESSION_NAME, api_id, api_hash) as client:
        if not await client.is_user_authorized():
            if not phone:
                raise ValueError("TELEGRAM_PHONE is required for first-time Telegram login")
            await client.send_code_request(phone)
            code = input("Enter Telegram code: ")
            await client.sign_in(phone, code)

        async for message in client.iter_messages(group):
            if limit is not None and len(downloaded) >= limit:
                break

            filename = get_telegram_filename(message)
            if not filename or not filename.startswith(prefix):
                continue
            if not filename.lower().endswith(".pdf"):
                continue

            dest = DATA_DIR / normalize_filename(filename)
            if dest.exists():
                continue

            await message.download_media(file=dest)
            downloaded.append(dest)
            print(f"Downloaded: {dest}")

    return downloaded


async def telegram_load(limit: int | None = None) -> None:
    downloaded = await download_from_telegram(limit=limit)
    if not downloaded:
        print("No new PDFs downloaded from Telegram.")
        return

    print(f"OCR {len(downloaded)} downloaded PDF(s)...")
    ocr_pdfs(downloaded)
    print("Done.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download and OCR newspaper PDFs")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--manual", action="store_true", help="OCR PDFs already in data/")
    mode.add_argument(
        "--telegram",
        action="store_true",
        help="Download PDFs from Telegram (ET Delhi prefix) and OCR them",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max PDFs to process (manual: OCR count, telegram: download count)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.manual:
        manual_load(limit=args.limit)
    else:
        asyncio.run(telegram_load(limit=args.limit))


if __name__ == "__main__":
    main()
