"""下載 Google FLEURS 測試集並產生 manifest（en / es-419 / pt-BR / ja；四語為平行句）。

  python data/prepare_fleurs.py --langs en ja es-419 pt-BR --n 300

輸出：data/audio/fleurs/<lang>/*.wav、data/manifests/<lang>/fleurs.jsonl
注意：每個語言的 test 音檔壓縮包約數百 MB。
"""
import argparse
import json
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bench import languages as L  # noqa: E402
from bench.audio import STT_SR, load_audio, save_wav  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--langs", nargs="+", default=["en", "es-419", "pt-BR", "ja"])
    ap.add_argument("--split", default="test")
    ap.add_argument("--n", type=int, default=300, help="每個語言取幾句")
    args = ap.parse_args()

    from huggingface_hub import hf_hub_download

    for lang in args.langs:
        cfg = L.LANGS[lang]["fleurs"]
        if not cfg:
            print(f"skip {lang}: FLEURS 沒有這個變體（請用 prepare_commonvoice.py 或自錄語料）")
            continue
        tsv = hf_hub_download("google/fleurs", f"data/{cfg}/{args.split}.tsv", repo_type="dataset")
        rows = []
        for line in Path(tsv).read_text(encoding="utf-8").splitlines():
            cols = line.split("\t")
            if len(cols) >= 3:
                rows.append({"fid": cols[0], "file": cols[1], "text": cols[2]})
        rows = rows[: args.n]
        wanted = {r["file"] for r in rows}

        print(f"{lang}: downloading audio ({cfg}/{args.split}) ...")
        tar_path = hf_hub_download("google/fleurs", f"data/{cfg}/audio/{args.split}.tar.gz", repo_type="dataset")
        out_dir = ROOT / "data" / "audio" / "fleurs" / lang
        out_dir.mkdir(parents=True, exist_ok=True)
        with tarfile.open(tar_path) as tar:
            for member in tar:
                name = Path(member.name).name
                if member.isfile() and name in wanted and not (out_dir / name).exists():
                    with tar.extractfile(member) as f:
                        tmp = out_dir / f"_{name}"
                        tmp.write_bytes(f.read())
                    save_wav(out_dir / name, load_audio(tmp), STT_SR)   # 統一為 16k mono
                    tmp.unlink()

        manifest = []
        for r in rows:
            wav = out_dir / r["file"]
            if not wav.exists():
                continue
            audio = load_audio(wav)
            manifest.append({
                "id": f"fleurs-{lang}-{Path(r['file']).stem}", "audio": wav.relative_to(ROOT).as_posix(),
                "text": r["text"], "lang": lang, "fleurs_id": r["fid"],
                "duration": round(len(audio) / STT_SR, 2),
            })
        dst = ROOT / "data" / "manifests" / lang / "fleurs.jsonl"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text("\n".join(json.dumps(m, ensure_ascii=False) for m in manifest) + "\n", encoding="utf-8")
        print(f"wrote {dst} ({len(manifest)} items)")


if __name__ == "__main__":
    main()
