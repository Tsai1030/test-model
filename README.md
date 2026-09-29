# speech-bench：多語語音地端模型評測框架

測試目標：在 Jetson Orin NX 16GB 上挑出 **en / es-ES / es-419 / pt-BR / pt-PT / ja** 各語言最適合的
STT、TTS，以及「語音對話機器人」（STT → LLM → TTS）組合。開發機（i3-10110U）先測，再換算成 Jetson 預估，最後用 Jetson 實測校準。

計畫書：`C:\Users\50019\.claude\plans\1-stt-tts-sts-model-model-vast-tiger.md`

---

## 1. 安裝（Windows 開發機）

1. 安裝 **uv**：`winget install --id astral-sh.uv -e`（Python 本身由 uv 下載，不必另外安裝）
2. 建立主環境：
   ```powershell
   cd C:\Users\50019\speech-bench
   uv python install 3.11
   uv venv .venv-core --python 3.11
   uv pip install -r requirements\core.txt --python .venv-core --index-strategy unsafe-best-match
   .venv-core\Scripts\Activate.ps1
   ```
   - `--index-strategy unsafe-best-match`：requirements 用了 PyTorch / llama-cpp-python 的額外 index，
     uv 預設只從第一個找到套件的 index 安裝，會拿到舊版 requests/certifi；此選項等同 pip 行為
   - 不需要 C++ 編譯器：日語 G2P 改用有預編譯 wheel 的 `pyopenjtalk-plus`（見 `requirements\core.txt` 註解）
3. 不同引擎相依衝突時，請分開建環境：`requirements\nemo.txt`（建議 WSL2 / Colab）、`requirements\tts-extra.txt`。
   同一個 run 只會 import 被選到的引擎，所以各環境只要裝自己要跑的部分。

## 2. 準備資料

```powershell
# FLEURS（en / es-419 / pt-BR / ja），每語 300 句
python data\prepare_fleurs.py --langs en es-419 pt-BR ja --n 300

# es-ES、pt-PT：Common Voice 依方言篩選（mozilladatacollective.com 下載 *Scripted Speech* 版本，不必解壓）
python data\prepare_commonvoice.py --cv D:\cv\<pt 壓縮檔>.tar.gz --lang pt-PT --list-variants
python data\prepare_commonvoice.py --cv D:\cv\<pt 壓縮檔>.tar.gz --lang pt-PT --match Portugal --n 300

# 自錄導覽語料（最重要，最貼近實際情境）：data\recordings\<lang>\transcripts.tsv + wav
python data\prepare_custom.py --lang ja

# 噪音版本（SNR 20/10/5 dB）與幻覺測試集
python -m bench.augment noisy --lang ja --dataset fleurs --snr 20 10 5 --noise-dir data\noise
python -m bench.augment silence --n 21 --noise-dir data\noise
```
`data\noise\` 放 MUSAN 或 DEMAND 的環境噪音 wav。沒有提供時，會改用其他語句混成「人聲嘈雜」噪音來代替。

## 3. 執行流程

**一次跑完一整輪**（建議）：模型清單寫在 `configs\plans\*.yaml`

```powershell
python run_all.py --plan configs\plans\round1.yaml --smoke-only   # 先確認所有模型都能下載、載入、執行
python run_all.py --plan configs\plans\round1.yaml --skip-smoke   # 正式測試 → reports\report.md
```
冒煙測試有錯誤就停下；正式測試每完成一步就更新報告；執行期間 Windows 不會自動睡眠（闔上筆電上蓋仍會）。
log 在 `logs\`。

**手動逐步執行**：

```powershell
# 1) 推論 + 計時（--hw 指定硬體 profile：pc / colab-t4 / jetson-orin-nx）
python run.py --suite configs\suites\smoke_stt.yaml --hw pc

# 2) 評分 → results\<run_id>\summary.csv
python score.py results\<run_id>
python score.py results\<run_id> --asr-judge whisper-large-v3-ct2-int8 --utmos   # TTS / 對話

# 3) 換算 Jetson 預估 → results\_estimates\summary.csv
python estimate_jetson.py

# 4) 報告 → reports\report.md、combined.csv、Pareto 圖
python report.py
```

| 套件 | 用途 |
|---|---|
| `smoke_stt / smoke_tts / smoke_dialogue` | 冒煙測試，幾分鐘內確認安裝與流程正常 |
| `stt_quick` | 全部 STT 候選的準確度初篩（乾淨語音、每組 100 句）→ 短名單 |
| `stt_full` | 短名單的完整測試：噪音、幻覺率、速度重複測 |
| `stt_lid` | 自動語言辨識準確率 |
| `tts_quick` | 全部 TTS 候選 |
| `dialogue_quick` | STT + LLM + TTS 組合比較 |

臨時縮小範圍：`--models whisper-small-ct2-int8 --langs ja --limit 20`

## 4. 人工評分（MOS／對話品質）

`score.py` 會在 run 資料夾產生兩個評分表（已存在就不覆寫）：
- `listening_test.csv`：TTS 聽測，順序已打亂。請母語者填 `mos_1to5`（1–5 分）
- `rating_sheet.csv`：對話評分。填 `relevance_1to5`、`naturalness_1to5`、`dialect_ok`

填完後重跑 `score.py`，人工分數會併入 summary，並在計算總分時優先於 UTMOS。

## 5. Jetson 實測與校準

1. Jetson（JetPack 6）建議使用 `dusty-nv/jetson-containers` 提供的 faster-whisper、piper、kokoro、llama.cpp 容器
2. 用 cuda 版本的模型 id（`*-cuda`）跑相同套件：`python run.py --suite ... --hw jetson-orin-nx --models whisper-small-ct2-fp16-cuda ...`
3. 錨點模型（`configs\anchors.yaml`）兩邊都跑完後，執行校準：
   ```bash
   python estimate_jetson.py --calibrate --source results/<pc_run> --target results/<jetson_run>
   python estimate_jetson.py && python report.py
   ```
   校準時會列出舊係數的預估誤差；誤差超過 30% 的類別會被校準值取代。

## 6. 新增模型

1. 在 `engines/stt|tts|llm/` 寫一個轉接器，繼承 `engines/base.py` 的 `STTEngine` / `TTSEngine` / `LLMEngine`
2. 在 `configs/models.yaml` 註冊（engine、params、langs/voices、backend_category、license）
3. 把 id 加進套件 yaml

## 7. 目錄結構

```
configs/      models.yaml（模型註冊）、hardware.yaml（硬體與換算係數）、scoring.yaml（門檻與權重）、suites/
bench/        languages、audio、monitor（資源監控）、augment（噪音）、streaming_sim、text（斷句）、envinfo
engines/      stt/（faster-whisper、HF、NeMo）tts/（Kokoro、Piper、Melo、XTTS、Chatterbox）llm/（llama.cpp）
metrics/      normalize、wer_cer（含 bootstrap CI）、utmos、lang_check
data/         prepare_*.py、tour_texts/（TTS 導覽文本）、dialogue/（場館資訊與提問）
run.py → score.py → estimate_jetson.py → report.py
```

## 8. 指標定義與已知限制

- **RTF** = 處理時間 ÷ 音訊長度；**延遲**不含讀檔時間
- **STT 最終延遲**（離線引擎）= 整句處理時間，不含 VAD 等待；VAD 時間只加在對話回合延遲
- **TTFA**：TTS 依句切分後依序合成，第一句音訊出來的時間。所有模型都用同一規則
- **對話回合延遲** = VAD 等待 + STT + LLM 產出第一句 + TTS 第一段音訊。這裡是依序量測，
  真實系統中 LLM 與 TTS 會並行，在同一顆 CPU 上會互相搶資源，所以此值是下限估計
- **UTMOS** 以英語訓練，其他語言只能當相對參考，要用人工 MOS 驗證
- **lang_ok_rate / fact_recall** 是啟發式檢查：只分辨語言，不分方言；數字寫成文字時可能誤判。方言正確性請看人工評分表
- 對話問題若沒有真人錄音，會用 TTS 合成（row 裡 `question_synthetic=true`）；正式測試請改用真人錄音
- Jetson 預估係數（`hardware.yaml` 中 `source: theory`）是理論推估，**校準前只能用來排序，不能當承諾值**
