#!/usr/bin/env python3
import argparse
import os
from pathlib import Path
import numpy as np
import av  # pip install pyav
from ofdm_linksim.factory import run_link
from ofdm_linksim.source import bits_from_bytes

def bits_from_file(file_path: str) -> BitArray:
    """تبدیل هر فایل به بیت (raw binary)"""
    ext = Path(file_path).suffix.lower().lstrip('.')
    if ext in ('mp4', 'avi', 'mkv'):
        container = av.open(file_path)
        audio = container.streams.audio[0]
        total_samples = audio.frames if audio.frames else 0
        audio_frame = container.streams.audio[0].decode()
        pcm = audio_frame.to_ndarray()
        # تبدیل به int16 (معمول‌ترین فرمت PCM)
        samples = pcm.flatten().astype(np.int16)
        return bits_from_bytes(samples.tobytes())

    elif ext == 'mp3':
        container = av.open(file_path)
        audio = container.streams.audio[0]
        total_samples = audio.frames if audio.frames else 0
        audio_frame = container.streams.audio[0].decode()
        pcm = audio_frame.to_ndarray()
        samples = pcm.flatten().astype(np.int16)
        return bits_from_bytes(samples.tobytes())

    elif ext == 'ts':
        # MPEG-TS ساده: فرض می‌کنیم فایل صوتی است (TS حاوی یک stream صوتی)
        with open(file_path, 'rb') as f:
            raw_data = f.read()
        return bits_from_bytes(raw_data)

    elif ext in ('jpg', 'jpeg', 'png', 'bmp'):
        # تصویر: به صورت خام باینری
        with open(file_path, 'rb') as f:
            raw_data = f.read()
        return bits_from_bytes(raw_data)

    elif ext in ('txt', 'text', 'md', 'py', 'cpp', 'pdf', 'docx'):
        # متن یا فایل متنی: خواندن UTF-8 و تبدیل به بیت
        with open(file_path, 'rb') as f:
            raw_data = f.read()
        return bits_from_bytes(raw_data)

    else:
        # fallback: اگر فرمت ناشناخته بود، به صورت خام باینری
        with open(file_path, 'rb') as f:
            raw_data = f.read()
        return bits_from_bytes(raw_data)


def main():
    parser = argparse.ArgumentParser(description="LInk واقعی با داده فایل")
    parser.add_argument("file", help="مسیر فایل (MP4, MP3, TS, JPEG, TXT و ...)")
    parser.add_argument("--method", default="ace", choices=["none", "clipping", "slm", "pts", "tone_reservation", "ace"])
    parser.add_argument("--n_blocks", type=int, default=64)
    parser.add_argument("--snr_db", type=float, default=15.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n_candidates", type=int, default=16)   # برای SLM/PTS
    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"فایل {args.file} پیدا نشد!")
        return

    print(f"🔄 شروع پردازش فایل: {args.file}")
    print(f"   اکستنشن تشخیص داده شد: {Path(args.file).suffix}")

    # تبدیل فایل به بیت
    bits = bits_from_file(args.file)

    print(f"   تعداد بیت‌ها: {len(bits):,}")

    # اجرای لینک کامل
    result = run_link(
        method=args.method,
        n_blocks=args.n_blocks,
        snr_db=args.snr_db,
        seed=args.seed,
        n_candidates=args.n_candidates,
        source_bits=bits
    )

    print("\n✅ نتیجه لینک:")
    print(f"   PAPR   : {result.get('papr_db', 'N/A'):.2f} dB")
    print(f"   BER    : {result.get('ber', 'N/A'):.2e}")
    print(f"   EVM    : {result.get('evm', 'N/A'):.1f} %")


if __name__ == "__main__":
    main()
