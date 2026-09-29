"""噪音疊加與幻覺測試集。

用法：
  # 依 SNR 產生噪音版 manifest（沒有 --noise-dir 時，用同資料集其他語句混成「人聲嘈雜」噪音）
  python -m bench.augment noisy --lang ja --dataset fleurs --snr 20 10 5 [--noise-dir data/noise]

  # 產生純靜音 / 純噪音片段（expect_empty=True），用於量測 STT 幻覺率
  python -m bench.augment silence --n 20 [--noise-dir data/noise]

建議噪音來源：MUSAN（noise/ 子集）或 DEMAND（戶外、街道、人群），放在 data/noise/*.wav
"""
import argparse
import json
from pathlib import Path

import numpy as np

from bench.audio import STT_SR, load_audio, save_wav

ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = ROOT / "data" / "manifests"


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def rms(x):
    return float(np.sqrt(np.mean(np.square(x)) + 1e-12))


def mix_at_snr(clean, noise, snr_db):
    if len(noise) < len(clean):
        noise = np.tile(noise, int(np.ceil(len(clean) / len(noise))))
    noise = noise[: len(clean)]
    gain = rms(clean) / (rms(noise) * 10 ** (snr_db / 20))
    out = clean + gain * noise
    peak = np.max(np.abs(out))
    return (out / peak * 0.95 if peak > 0.99 else out).astype(np.float32)


def pink_noise(n, rng):
    spec = np.fft.rfft(rng.standard_normal(n))
    freqs = np.arange(len(spec))
    freqs[0] = 1
    x = np.fft.irfft(spec / np.sqrt(freqs), n)
    return (x / (np.max(np.abs(x)) + 1e-9) * 0.5).astype(np.float32)


def load_noise_bank(noise_dir):
    if not noise_dir:
        return []
    return [load_audio(p) for p in sorted(Path(noise_dir).glob("*.wav"))]


def babble(items, exclude_id, rng, n_speakers=4):
    pool = [it for it in items if it["id"] != exclude_id]
    picks = rng.choice(len(pool), size=min(n_speakers, len(pool)), replace=False)
    waves = [load_audio(ROOT / pool[i]["audio"]) for i in picks]
    length = max(len(w) for w in waves)
    mix = np.zeros(length, np.float32)
    for w in waves:
        mix[: len(w)] += w / (rms(w) + 1e-9)
    return mix


def cmd_noisy(args):
    rng = np.random.default_rng(args.seed)
    src = MANIFESTS / args.lang / f"{args.dataset}.jsonl"
    items = read_jsonl(src)
    bank = load_noise_bank(args.noise_dir)
    for snr in args.snr:
        rows = []
        for it in items:
            clean = load_audio(ROOT / it["audio"])
            if bank:
                noise = bank[rng.integers(len(bank))]
                source = "noise-dir"
            else:
                noise = babble(items, it["id"], rng)
                source = "babble-synthetic"
            out_path = Path("data/audio/noisy") / args.lang / args.dataset / f"snr{snr}" / f"{it['id']}.wav"
            save_wav(ROOT / out_path, mix_at_snr(clean, noise, snr), STT_SR)
            rows.append({**it, "audio": out_path.as_posix(), "condition": f"snr{snr}", "noise": source})
        dst = MANIFESTS / args.lang / f"{args.dataset}__snr{snr}.jsonl"
        write_jsonl(dst, rows)
        print(f"wrote {dst} ({len(rows)} items, noise={rows[0]['noise'] if rows else '-'})")


def cmd_silence(args):
    rng = np.random.default_rng(args.seed)
    bank = load_noise_bank(args.noise_dir)
    n = STT_SR * 5
    rows = []
    for i in range(args.n):
        kind = i % 3
        if kind == 0:
            audio, desc = (rng.standard_normal(n) * 1e-3).astype(np.float32), "near-silence"
        elif kind == 1 or not bank:
            audio, desc = pink_noise(n, rng) * 0.3, "pink-noise"
        else:
            src = bank[rng.integers(len(bank))]
            start = rng.integers(max(1, len(src) - n))
            audio, desc = src[start:start + n], "env-noise"
        rel = Path("data/audio/silence") / f"sil_{i:03d}.wav"
        save_wav(ROOT / rel, audio, STT_SR)
        rows.append({"id": f"sil_{i:03d}", "audio": rel.as_posix(), "text": "",
                     "lang": None, "expect_empty": True, "noise": desc})
    dst = MANIFESTS / "_any" / "silence.jsonl"
    write_jsonl(dst, rows)
    print(f"wrote {dst} ({len(rows)} items)")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("noisy")
    a.add_argument("--lang", required=True)
    a.add_argument("--dataset", required=True)
    a.add_argument("--snr", type=int, nargs="+", default=[20, 10, 5])
    a.add_argument("--noise-dir")
    a.add_argument("--seed", type=int, default=0)
    b = sub.add_parser("silence")
    b.add_argument("--n", type=int, default=21)
    b.add_argument("--noise-dir")
    b.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    {"noisy": cmd_noisy, "silence": cmd_silence}[args.cmd](args)


if __name__ == "__main__":
    main()
