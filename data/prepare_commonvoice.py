"""從 Mozilla Common Voice 產生 manifest，可依方言篩選（用於 es-ES、pt-PT）。

Common Voice 需先到 Mozilla Data Collective（mozilladatacollective.com）登入下載 *Scripted Speech* 版本。
--cv 可以是：
  - 未解壓的 .tar.gz（建議；西語約 48 GB，不必整包解壓，只取出需要的音檔）
  - 已解壓、內含 <split>.tsv 與 clips/ 的資料夾

  # 1) 先看有哪些 variant / accents 值可以篩（壓縮檔第一次需要掃描一段時間，之後會用快取）
  python data/prepare_commonvoice.py --cv D:/cv/es.tar.gz --lang es-ES --split test dev --list-variants
  # 2) 篩選並產生 manifest；--match 可給多個值，符合任一個即可
  python data/prepare_commonvoice.py --cv D:/cv/pt.tar.gz --lang pt-PT --split test dev --match "Portuguese (Portugal)"
"""
import argparse
import collections
import csv
import io
import json
import re
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bench.audio import STT_SR, load_audio, save_wav  # noqa: E402

TSV_CACHE = ROOT / "data" / "cache" / "commonvoice"

csv.field_size_limit(10 ** 7)


def is_word_list(text: str) -> bool:
    """純詞表：逗號分隔的名詞清單、沒有句末標點，如 "haloalcano, fluoroalcano, cloroalcano, ..."。
    Common Voice 葡語含大量這類專業術語提示句，導覽情境不會出現；含列舉的一般句子（有句號結尾）不受影響。"""
    return text.count(",") >= 3 and not re.search(r"[.?!…]\s*$", text)


def parse_tsv(text):
    return list(csv.DictReader(io.StringIO(text), delimiter="\t", quoting=csv.QUOTE_NONE))


def tsvs_from_archive(archive: Path, splits) -> dict:
    """從壓縮檔取出各 <split>.tsv（只掃描一次）；結果快取在 data/cache，下次不必再掃整個壓縮檔。"""
    caches = {s: TSV_CACHE / f"{archive.name}.{s}.tsv" for s in splits}
    todo = {s for s, c in caches.items() if not c.exists()}
    if todo:
        print(f"scanning {archive.name} for {sorted(todo)}（壓縮檔很大時需要數十分鐘）...")
        with tarfile.open(archive, "r|*") as tar:      # 串流模式：只能依序讀，不需要整包解壓
            for member in tar:
                name = Path(member.name).name
                split = name[:-4] if name.endswith(".tsv") else None
                if member.isfile() and split in todo:
                    caches[split].parent.mkdir(parents=True, exist_ok=True)
                    caches[split].write_text(tar.extractfile(member).read().decode("utf-8"), encoding="utf-8")
                    todo.discard(split)
                    if not todo:
                        break
        if todo:
            raise SystemExit(f"{archive} 裡找不到 {sorted(todo)}.tsv")
    return {s: c.read_text(encoding="utf-8") for s, c in caches.items()}


def clips_from_archive(archive: Path, names, out_dir: Path) -> None:
    """掃描一次壓縮檔，只取出 names 裡的音檔並轉成 16k wav；全部找到就提前結束。"""
    todo = {n for n in names if not (out_dir / f"{Path(n).stem}.wav").exists()}
    if not todo:
        return
    print(f"extracting {len(todo)} clips from {archive.name} ...")
    out_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r|*") as tar:
        for member in tar:
            name = Path(member.name).name
            if member.isfile() and name in todo:
                tmp = out_dir / f"_{name}"
                tmp.write_bytes(tar.extractfile(member).read())
                save_wav(out_dir / f"{Path(name).stem}.wav", load_audio(tmp), STT_SR)
                tmp.unlink()
                todo.discard(name)
                if not todo:
                    break
    if todo:
        print(f"!! {len(todo)} clips not found in archive")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cv", "--cv-dir", dest="cv", required=True, help=".tar.gz 壓縮檔或已解壓的資料夾")
    ap.add_argument("--lang", required=True)
    ap.add_argument("--split", nargs="+", default=["test"],
                    help="可給多個（如 test dev）。只用模型訓練時保留的 test/dev，避免用過 CV 訓練資料的模型占便宜")
    ap.add_argument("--match", nargs="+", help="variant 或 accents 欄位需包含其中任一字串（不分大小寫）")
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--max-per-speaker", type=int, default=10,
                    help="每位說話者最多取幾句，避免少數人的錄音占掉大部分測試資料")
    ap.add_argument("--exclude-word-lists", action="store_true", help="排除純詞表型提示句（見 is_word_list）")
    ap.add_argument("--list-variants", action="store_true")
    args = ap.parse_args()

    cv = Path(args.cv)
    is_archive = cv.is_file()
    texts = (tsvs_from_archive(cv, args.split) if is_archive
             else {s: (cv / f"{s}.tsv").read_text(encoding="utf-8") for s in args.split})
    rows = [{**r, "split": s} for s, text in texts.items() for r in parse_tsv(text)]

    if args.list_variants:
        print(f"{'+'.join(args.split)}: {len(rows)} clips")
        for col in ("variant", "accents"):
            clips = collections.Counter(r.get(col) or "" for r in rows)
            speakers = collections.defaultdict(set)
            for r in rows:
                speakers[r.get(col) or ""].add(r.get("client_id"))
            print(f"== {col} ==   句數  說話者數")
            for value, n in clips.most_common(40):
                print(f"{n:8d}  {len(speakers[value]):6d}  {value!r}")
        return

    if args.match:
        keys = [m.lower() for m in args.match]
        rows = [r for r in rows
                if any(k in (r.get("variant") or "").lower() or k in (r.get("accents") or "").lower() for k in keys)]
    if args.exclude_word_lists:
        before = len(rows)
        rows = [r for r in rows if not is_word_list(r["sentence"])]
        print(f"excluded {before - len(rows)} word-list prompts")
    per_speaker, picked = collections.Counter(), []
    for r in rows:
        if per_speaker[r.get("client_id")] < args.max_per_speaker:
            per_speaker[r.get("client_id")] += 1
            picked.append(r)
        if len(picked) >= args.n:
            break
    rows = picked
    if not rows:
        raise SystemExit("篩選後沒有資料，先用 --list-variants 確認欄位值")
    print(f"selected {len(rows)} clips from {len(per_speaker)} speakers")

    out_dir = ROOT / "data" / "audio" / "commonvoice" / args.lang
    if is_archive:
        clips_from_archive(cv, [r["path"] for r in rows], out_dir)
    manifest = []
    for r in rows:
        stem = Path(r["path"]).stem
        wav = out_dir / f"{stem}.wav"
        if not wav.exists():
            if is_archive:
                continue
            save_wav(wav, load_audio(cv / "clips" / r["path"]), STT_SR)
        audio = load_audio(wav)
        manifest.append({
            "id": f"cv-{args.lang}-{stem}", "audio": wav.relative_to(ROOT).as_posix(), "text": r["sentence"],
            "lang": args.lang, "variant": r.get("variant"), "accents": r.get("accents"),
            "speaker": r.get("client_id"), "split": r["split"], "duration": round(len(audio) / STT_SR, 2),
        })
    dst = ROOT / "data" / "manifests" / args.lang / "commonvoice.jsonl"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text("\n".join(json.dumps(m, ensure_ascii=False) for m in manifest) + "\n", encoding="utf-8")
    print(f"wrote {dst} ({len(manifest)} items)")


if __name__ == "__main__":
    main()
