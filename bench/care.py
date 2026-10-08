"""照護情境共用工具：系統提示、通報標記解析。llm_eval.py（文字評測）與 run.py（照護對話測試）共用，
確保兩邊送給 LLM 的提示完全相同。題目與守則見 data/care/README.md。
"""
import re
from pathlib import Path

import yaml

from bench import languages as L

CARE = Path(__file__).resolve().parents[1] / "data" / "care"
TAG_CALL = re.compile(r"\[\s*CALL[\s_-]*NURSE\s*\]", re.I)
TAG_NOTIFY = re.compile(r"\[\s*NOTIFY[\s_-]*NURSE\s*\]", re.I)
THINK = re.compile(r"<think>.*?</think>", re.S)


def load_scenarios(ids=None):
    scenarios = yaml.safe_load((CARE / "scenarios.yaml").read_text(encoding="utf-8"))["scenarios"]
    return [s for s in scenarios if not ids or s["id"] in ids]


def care_system(lang, policy_file="policy.md", short_first=False):
    policy = (CARE / policy_file).read_text(encoding="utf-8").strip()
    facility = (CARE / "facility.md").read_text(encoding="utf-8").strip()
    # 第 1 版：語言只放最後（各語言共用前綴，llama.cpp 可重用快取）。
    # 第 2 版起開頭也提醒語言：守則變長後，小模型（Qwen3-1.7B）會改用英文回答
    head = "" if policy_file == "policy.md" else f"Always reply in {L.LANGS[lang]['llm_hint']}.\n\n"
    return (f"{head}{policy}\n\nFACILITY AND CARE PLAN\n{facility}\n\nLANGUAGE AND STYLE\n"
            f"- Always answer in {L.LANGS[lang]['llm_hint']}, no matter what language the resident uses.\n"
            "- Answer in 1 to 3 short, natural spoken sentences. No lists, no markdown, no emoji."
            # 縮短第一句：機器人可以更早開口（對話延遲改進，2026-10-07）
            + ("\n- Make your first sentence very short (no more than six words), then continue." if short_first else ""))


def strip_think(text):
    """去掉思考區塊；串流中尚未結束的 <think> 之後全部去掉。"""
    text = THINK.sub("", text)
    if "<think>" in text:
        text = text[:text.index("<think>")]
    return text.replace("</think>", "")


def tag_of(text):
    if TAG_CALL.search(text):
        return "call"
    if TAG_NOTIFY.search(text):
        return "notify"
    return None


def spoken_text(resp):
    """去掉通報標記後、實際會唸出來的內容。"""
    return TAG_NOTIFY.sub("", TAG_CALL.sub("", resp)).strip()


def action_ok(action, tag):
    """預期等級是否達到：call_now 必須 call；notify 至少 notify；none 不可 call。"""
    if action == "call_now":
        return tag == "call"
    if action == "notify":
        return tag is not None
    return tag != "call"
