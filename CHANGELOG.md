# 變更紀錄

記錄框架、設定與測試資料的每次修改：改了什麼、為什麼、對結果的影響。
影響測試結果的變更會標示 **⚠️ 影響結果**。

---

## 2026-10-01（第二晚結束後，第三晚準備）

### ⚠️ 影響結果：放寬對話延遲的評分刻度
- **改了什麼**：`configs/scoring.yaml` 的 `turn_latency_ms` 由 `[800, 3000]` 改為 `[1000, 10000]`（1 秒 = 100 分、10 秒 = 0 分）。
- **為什麼**：Jetson 換算下所有對話組合的回合延遲都超過 3 秒，延遲分數全為 0，排名只剩回答品質在比，報告因此推薦延遲 10–15 秒的 turbo 組合。放寬後延遲能分出高下；Jetson 實測後再收緊（計畫目標 1.5 秒）。
- **影響**：只影響對話總分與排名，不影響任何量測值。

### ⚠️ 影響結果：數字寫法統一（es / pt / ja）
- **改了什麼**：`metrics/normalize.py` 在計算錯誤率前統一數字寫法：
  - es / pt：數字文字轉阿拉伯數字（`text2num`），例如 dezenove → 19、mil novecentos e oitenta e cinco → 1985
  - ja：漢字數字〇一…九轉阿拉伯數字（二つ → 2つ；十、百等複合寫法不處理）
  - en 維持 Whisper 官方 EnglishTextNormalizer（原本就會處理數字）
- **為什麼**：第三晚冒煙測試發現 Nemotron 把「19」寫成「dezenove」而被算成錯誤。不同模型對數字的寫法不同（Whisper 多寫數字，Nemotron、Parakeet-ja 等多寫文字或漢字），不統一會讓寫法不同的模型被不公平地多算錯誤；一個「1985」寫成文字會被算成好幾個錯。TTS 也受影響：導覽文本部分數字寫成文字（如 quarenta e cinco），評審 Whisper 常寫成「45」，被誤判成唸錯。
- **影響**：重新評分第一、二晚所有 run（STT、TTS、對話）；TTS 沿用已存的評審轉錄（`score.py` 新增快取機制，`--rejudge` 可強制重跑）。修正前的評分保留為各 run 的 `summary.before_numnorm.csv`。

### SenseVoice 改用 2024-07-17 版
- 2025-09-09 int8 版不論語言設定都把語言判斷成粵語（`<|yue|>`），日語輸出成簡體中文、英語全大寫。2024-07-17 原版（int8）正常。

### 新增第三晚的模型與轉接器
- **新套件**（`.venv-core`，只新增、未更動既有套件）：`onnx-asr[cpu,hub]`、`sherpa-onnx`、`moondream`（Photon）、`supertonic`、`librosa`（Nemotron 的特徵擷取器需要；冒煙測試時發現缺少）。已補進 `requirements/core.txt`。
- **新轉接器**：
  - `engines/stt/onnx_asr_engine.py`：Parakeet v2 / v3（int8）、Parakeet v3 巴西葡語微調版
  - `engines/stt/sherpa_onnx_engine.py`：SenseVoice-Small、Parakeet-ja（int8）
  - `engines/stt/nemotron_engine.py`：Nemotron-3.5-ASR-Streaming，整句與**原生串流**兩種模式（transformers 官方串流用法）
  - `engines/stt/qwen3_asr_engine.py`：Qwen3-ASR-0.6B
  - `engines/stt/hf_seq_engine.py`：Granite-Speech-5.0-470M（CTC）、Moonshine-tiny-ja
  - `engines/stt/photon_engine.py`：Parakeet-Redux。**Windows 版 kestrel 的 CPU 擴充模組沒有 AVX2 / VNNI 核心，三值權重無法在本機執行**，改到 Linux / Jetson 階段測
  - `engines/tts/supertonic_engine.py`：Supertonic-3
- **方言代碼**：`STTEngine.wants_locale`，能區分方言的模型（Nemotron）收到完整語言碼（如 pt-PT、es-419），其餘仍收到基本碼（pt、es）。
- **串流評測**：新增 `configs/suites/stt_stream.yaml`；`score.py` 新增 `stream_err_rate`（串流模式的錯誤率）；報告的 STT、TTS 表格新增「串流」欄（`models.yaml` 的 `streaming` 欄位）。
- **`models.yaml`**：新增 `streaming`（native / chunked / offline / sentence）與 `specialized`（語言專用模型的語言碼）欄位。
- **執行計畫**：`configs/plans/round1_night3.yaml`。
- **注意**：Parakeet v3 巴西葡語版只有 fp32（約 2.4 GB），與 int8 的 Parakeet v3 比較時精度不同；Qwen3-ASR 在 CPU 上用 fp32（約 3.8 GB），GPU 上用 bf16 約減半。

---

## 2026-09-30（第一晚結果檢討後，第二晚開始前）

### ⚠️ 影響結果：pt-PT 測試資料排除詞表型句子
- **改了什麼**：`data/prepare_commonvoice.py` 新增 `--exclude-word-lists`，排除「逗號 ≥ 3 且沒有句末標點」的純名詞清單提示句；`configs/plans/round1.yaml` 對 pt-PT、es-ES 啟用。
- **為什麼**：Common Voice 葡語含大量專業術語清單（化學、醫學名詞、古代部族名，例如「haloalcano, fluoroalcano, cloroalcano, …」），導覽情境不會出現。第一晚 whisper-small 在這些句子的錯誤率高達 79.6%，拉高了 pt-PT 整體錯誤率。
- **影響**：
  - pt-PT 資料：190 句 → **177 句**（44 位說話者、12.9 分鐘）；可選句子池排除 27 句詞表，其中 172 句與舊資料相同，另補入 5 句。舊資料清單保留為 `data/manifests/pt-PT/commonvoice.v1-with-wordlists.jsonl.bak`。
  - es-ES：規則排除 0 句（含列舉的一般句子有句號結尾，不受影響），資料不變。
  - 第一晚 pt-PT 的 STT 結果（tiny / base / small）是舊資料的數字，**第二晚用新資料重測**（`stt_small_ptpt` 步驟），以便與大模型在同一份資料上比較。
  - 以第一晚結果試算：排除詞表後 whisper-small 的 pt-PT 錯誤率由 43.4% 降至約 36.7%，仍超過 30% 門檻。

### ⚠️ 影響結果：修正對話測試的記憶體累積
- **改了什麼**：`run.py` 的 `EngineCache.keep_only()` 在每換一個對話組合時，釋放該組合用不到的模型；`engines/llm/llama_cpp_engine.py` 新增 `close()` 明確釋放 GGUF 模型。
- **為什麼**：原本所有用過的模型都留在記憶體，最後一個組合時程序占用約 9 GB（系統 16.9 GB），系統改用分頁檔，越晚執行的組合越慢。Kokoro 每字元合成時間依執行順序為 136 → 152 → 328 → 534 → 2,240 ms。
- **驗證**：修正後同樣的測試為 166–196 ms（無遞增趨勢），最大組合的記憶體峰值約 7.2 GB。
- **影響**：第一晚對話測試的**延遲數據作廢**（回答內容的事實正確率、語言正確率不受影響），第二晚重跑。

### ⚠️ 影響結果：評分新增準確度門檻
- **改了什麼**：`configs/scoring.yaml` 新增 `gates.max_err_rate: 0.30`，STT 的 WER / CER 或 TTS 的 ASR 回測錯誤率超過 30% 即判定不合格（`FAIL:accuracy`）；推薦表在無模型通過時顯示「無模型通過門檻」。
- **為什麼**：錯誤率 ≥ 30% 時準確度為 0 分，若所有模型都如此，排名只剩速度在比，曾把錯誤率 82.9% 的 whisper-tiny 推薦為 pt-PT 的 STT。
- **影響**：tiny 在 es-ES（30.8%）、ja（38.9%）、pt-PT，以及 base、small 在 pt-PT 被判定不合格。

### 報告：同一組合只採用最新結果
- **改了什麼**：`report.py` 合併所有 run 時，同一個「任務 × 模型 × 語言 × 資料集 × 條件 × 硬體」只保留最新一次。
- **為什麼**：修正後重跑（對話、pt-PT）會與舊結果重複；舊結果檔案仍保留在 `results/`，只是不進報告。

### 執行排程改為方案 B
- **改了什麼**：`configs/plans/round1.yaml` 中 medium、large-v3-turbo、large-v3 每語言改測 **50 句**（`limit: 50`，小模型維持 100 句）；新增 `stt_small_ptpt` 步驟；`run_all.py` 支援步驟層級的 `limit`、`langs`。
- **為什麼**：以第一晚乾淨環境的實測速度重估，大模型在本機比預期慢（乾淨環境只比冒煙測試快約 11%），維持 100 句需再 4 個晚上。大模型主要是回答「是否明顯比 small 準」，差距預期夠大，50 句看得出來；且大模型在 Jetson 上會用 GPU，這台 CPU 的速度參考價值有限。
- **影響**：大模型的錯誤率信賴區間較寬。前 50 句是小模型 100 句的子集，分析時另列 small 在相同 50 句上的錯誤率，確保同基準比較。

### 取消第三晚的 Whisper large-v3，改測小型與語言專用 STT 模型
- **改了什麼**：`configs/plans/round1.yaml` 的 `stt_large` 步驟註解停用。
- **為什麼**：large-v3 記憶體約 3.3 GB，超過 STT 預算 2 GB，本來就不是部署候選；且使用者表示評測以小模型為主。第三晚改測排行榜上的其他小型多語模型與各語言專用模型，最後量化比較「專用模型」與「多語模型」。候選清單見 `docs/roadmap.md`。

### 新增試聽頁 `listen.html`
- **改了什麼**：新增 `listen_page.py`；`score.py` 評分完自動在 run 資料夾產生 `listen.html`。
- **內容**：TTS — 每列一句導覽文本，並排各模型的合成語音，附 Whisper 評審聽到的文字（可看出哪些字被判定唸錯）；對話 — 每列一個問題（含問題語音），並排各組合的回答語音，附 STT 聽到的內容、回答文字、事實是否答對。
- **為什麼**：人工聽測時可直接對照，不必逐一找音檔。已為第一晚的 TTS、對話 run 補產生。

### 報告格式
- STT 表格將「錯誤率」與「95% 信賴區間」拆成兩欄，並標示 WER / CER；加註「噪音錯誤率、幻覺率只有 stt_full 會測」。
- 報告最後自動附上 `docs/analysis/*.md` 的人工解讀（重新產生報告不會遺失）。
- 圖表負號改用 ASCII；STT Pareto 圖的對數刻度改顯示一般數字（0.1、1、10），不再使用 10⁻¹ 科學記號。原本數學字型的負號（U+2212）中文字型沒有，每次產生報告都會出現「Font 'default' does not have a glyph for '−'」警告，圖上負號也可能顯示成方框。

---

## 2026-09-29（環境建立與第一輪準備）

### 環境
- 改用 **uv** 建立 `.venv-core`（Python 3.11.16）。安裝需加 `--index-strategy unsafe-best-match`：requirements 使用 PyTorch 與 llama-cpp-python 的額外 index，uv 預設只用第一個找到套件的 index，會裝到舊版 requests / certifi。
- `requirements/core.txt`：
  - 加上 `transformers>=4.40`：不設下限時，解析器為了 huggingface-hub 2.x 退回 2019 年的 transformers 2.3.0，Kokoro 無法使用。
  - `misaki[ja]` 拆開，`pyopenjtalk` 改用有預編譯 wheel 的 `pyopenjtalk-plus`：原版在 Windows 需 MSVC 編譯。Kokoro 日語預設走 cutlet（fugashi + unidic），pyopenjtalk 只需能 import，不影響合成結果。
  - 預裝 spaCy 英語模型 `en_core_web_sm`：misaki 英語 G2P 需要，原本在執行時以 pip 下載，uv 環境沒有 pip 會失敗。
  - 安裝後需下載 unidic 日語字典（約 500 MB）。
- `.vscode/settings.json`：停用 C/C++ 擴充功能的 IntelliSense，排除 `.venv` 等大型資料夾的監看，避免背景占用 CPU 干擾速度測試。

### 測試資料
- FLEURS：en、es-419、pt-BR、ja 各 300 句。
- Common Voice 27.0（es-ES、pt-PT；FLEURS 沒有這兩個變體）：`data/prepare_commonvoice.py` 改為可直接讀取未解壓的 `.tar.gz`（西語壓縮檔 48 GB，D 槽空間不足以解壓），支援多個 split（test + dev）、多個篩選值、每位說話者句數上限。篩選規則見 `configs/plans/round1.yaml`。

### 執行框架
- 新增 `run_all.py`：準備資料 → 冒煙測試 → 正式測試（推論 + 評分）→ Jetson 換算 → 報告；執行期間防止 Windows 自動睡眠；正式測試前檢查背景 CPU 占用與電源設定。
- 新增 `configs/plans/round1.yaml`：第一輪的模型清單與排程。
- 對話測試的評分移除 `--asr-judge`（對話總分未使用此指標，可省約 3 小時）。

### 第一晚
- 2026-09-29 14:53 開始，8 小時 54 分完成：TTS、對話、STT 小模型。結果解讀見 `docs/analysis/round1_night1.md`。
