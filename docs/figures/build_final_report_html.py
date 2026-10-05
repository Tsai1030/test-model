"""把 final_report.template.html 的圖片轉成內嵌 data URI，輸出單一檔案 final_report.html（專案根目錄）。
單一檔案即可用瀏覽器開啟、簡報或寄送，不需附圖片資料夾。

  .venv-core\\Scripts\\python.exe docs\\figures\\make_final_report_figures.py     # 先更新圖表（選用）
  .venv-core\\Scripts\\python.exe docs\\figures\\build_final_report_html.py
"""
import base64
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def inline(match):
    name = match.group(1)
    data = base64.b64encode((HERE / name).read_bytes()).decode("ascii")
    return f'src="data:image/png;base64,{data}"'


def main():
    html = (HERE / "final_report.template.html").read_text(encoding="utf-8")
    html, n = re.subn(r'src="([\w\-]+\.png)"', inline, html)
    out = ROOT / "final_report.html"
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out}（內嵌 {n} 張圖，{out.stat().st_size / 1024:.0f} KB）")


if __name__ == "__main__":
    main()
