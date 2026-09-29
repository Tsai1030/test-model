"""自錄導覽語料 → manifest（最貼近實際情境，建議每語 50–100 句，由母語者錄製）。

資料夾格式：
  data/recordings/<lang>/transcripts.tsv    每行：檔名<TAB>正確文字<TAB>關鍵字1|關鍵字2（關鍵字可省略）
  data/recordings/<lang>/*.wav              任意取樣率，會轉成 16k mono

  python data/prepare_custom.py --lang ja [--name tour]
輸出：data/manifests/<lang>/<name>.jsonl（keywords 用來算專有名詞召回率）
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bench.audio import STT_SR, load_audio, save_wav  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", required=True)
    ap.add_argument("--name", default="tour")
    ap.add_argument("--src", help="預設 data/recordings/<lang>")
    args = ap.parse_args()

    src = Path(args.src) if args.src else ROOT / "data" / "recordings" / args.lang
    out_dir = ROOT / "data" / "audio" / args.name / args.lang
    manifest = []
    for line in (src / "transcripts.tsv").read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        cols = line.split("\t")
        fname, text = cols[0], cols[1]
        keywords = [k for k in cols[2].split("|") if k] if len(cols) > 2 else None
        wav = out_dir / f"{Path(fname).stem}.wav"
        audio = load_audio(src / fname)
        save_wav(wav, audio, STT_SR)
        manifest.append({
            "id": f"{args.name}-{args.lang}-{Path(fname).stem}", "audio": wav.relative_to(ROOT).as_posix(),
            "text": text, "lang": args.lang, "keywords": keywords, "duration": round(len(audio) / STT_SR, 2),
        })
    dst = ROOT / "data" / "manifests" / args.lang / f"{args.name}.jsonl"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text("\n".join(json.dumps(m, ensure_ascii=False) for m in manifest) + "\n", encoding="utf-8")
    print(f"wrote {dst} ({len(manifest)} items)")


if __name__ == "__main__":
    main()
