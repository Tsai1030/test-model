# 變更紀錄

記錄框架、設定與測試資料的每次修改：改了什麼、為什麼、對結果的影響。
影響測試結果的變更會標示 **⚠️ 影響結果**。

---

## 2026-10-08（延遲改進測試結果）

### 延遲改進正式測試完成
- run `20261007-160931_round3_care_fast_dialogue_care_fast_pc`（Qwen3-4B，快速通道＋第一句縮短＋子句切段），2 小時 04 分，無錯誤；開跑前背景 CPU 39%。解讀見 `docs/analysis/round3_care_fast.md`。
- 緊急回應約 0.5–0.75 秒（Jetson 換算，規則層觸發；上一輪約 4.4 秒）；規則攔截率 95.8%、誤報 2.5%；規則層＋LLM 緊急漏報 0 / 72。
- 第一段前要產生的字詞數 18 → 12（−33%）；依同速度換算，回合延遲約 4.4 → 3.5 秒（Jetson）。
- 通報行為改善：LLM 預期等級達成 86.6% → 90.9%（日語 67% → 87%），通報不足 26.9% → 15.7%；過度緊急 4.9% → 5.9%。
- 兩輪之間電腦速度差異大（每秒字詞數 1.5–3.0），秒數比較只能參考，改以字詞數比較。

## 2026-10-07（照護情境對話測試結果）

### 規劃第二輪 LLM 候選模型（尚未測試）
- 計畫書新增 10.7 節：與 Qwen3-4B 同級（3–4B、Q4_K_M 約 2–2.5 GB、標準 dense、支援 en/es/pt/ja、可商用）的候選 Phi-4-mini、Ministral 3 3B、Granite 4.1 3B；Qwen3.5-4B 為參考（架構不同、預設思考，待決定）。列出不納入的模型與原因（Gemma 4 E4B 檔案 4.98 GB、Tiny Aya 非商用、SmolLM3 無日語等）。已確認本專案的 llama-cpp-python 0.3.35 支援上述架構。roadmap 同步。
- 本機實測 LLM 記憶體（照護系統提示、回答一題後的程序記憶體）：Qwen3-4B 約 4.9 GB（上下文 4096）/ 4.8 GB（2048）；Qwen2.5-1.5B 約 1.9 GB。CPU 上權重會重新排列成另一份，約佔檔案大小的兩倍。

### 新增 LLM 評測方法文件
- `docs/llm_eval_method.md`：目的、評估依據、三種測試（文字照護題、醫學選擇題、語音對話）、測試資料、設定、各指標公式（通報標記判讀、緊急漏報率等、選擇題判讀與信賴區間、配對 bootstrap、延遲定義與 Jetson 換算）、判讀與選型準則、使用方式、結果位置、限制。計畫書第 10 節與 `data/care/README.md` 加上連結。

### 延遲改進：緊急快速通道、第一句縮短、子句切段
- **規則層**（新）：`data/care/emergency_rules.yaml`（6 種語言的緊急警訊規則，依守則第 3 版緊急清單分類；「身體部位＋症狀詞」組合；草稿，未經護理審核）、`bench/care_rules.py`（正規化後比對：小寫、es / pt 去重音、日語去空白）。撰寫時看過 `scenarios.yaml`，同一批題目的評估結果偏樂觀。
- **離線評估**（用上一輪語音對話的 STT 結果，不需重跑模型）：規則層攔截率 原文 100%、STT 文字 95.8%（漏掉的 3 題是 STT 聽錯字，LLM 都有通報）；誤報 2.5%（只有「剛剛跌倒但沒事」，該題允許立即呼叫）。規則 ＋ LLM 合併：緊急漏報 5 / 72 → **0 / 72**，過度緊急 4.9% → 6.9%。
- **固定回應**（新）：`data/care/fixed_responses.yaml`，6 種語言；觸發時立即播放（測試時用對話 TTS 預先合成，實際部署為預錄音檔）。
- `run.py`：套件新增 `fast_path`（規則層在 LLM 之前比對；規則命中或 LLM 給出 `[CALL_NURSE]` 即走快速通道，記錄實際開口時間 `response_latency_s`、規則通報延遲、合併後的通報等級）、`first_chunk: clause`（TTS 在逗號等子句標點處就開始唸，數字中的標點不切）、`short_first`（系統提示要求第一句不超過六個字）。三者預設關閉，既有測試不受影響。
- `bench/text.py`：新增 `first_complete_clause`。`bench/care.py`：`care_system` 新增 `short_first` 參數（預設不變）。
- `score.py`：新增規則攔截率、規則誤報率、合併後的緊急漏報 / 過度緊急 / 預期等級達成率、規則通報延遲、緊急回應延遲、實際開口延遲。`estimate_jetson.py`：規則通報延遲只換算 STT；混合兩種觸發的延遲不換算。`report.py`、`listen_page.py`：顯示規則層結果。
- 新增 `configs/suites/dialogue_care_fast.yaml`、`configs/plans/round3_care_fast.yaml`（只跑 Qwen3-4B，與上一輪逐題比較）。冒煙測試（en / ja 各 3 題緊急題）：6 題都由規則層觸發，Jetson 換算緊急回應約 0.5–0.8 秒。

### 照護情境完整對話測試完成
- run `20261007-091647_round3_care_dialogue_dialogue_care_pc`，4 小時 50 分，無錯誤。解讀見 `docs/analysis/round3_care_dialogue.md`（已附在 `reports/report.md` 最後）。
- Qwen3-4B：回合延遲約 4.4 秒（Jetson 換算，p90 約 6–7 秒）、通報延遲約 2 秒；語音對話的預期等級達成 87%（文字評測 91%），緊急漏報 5 / 72 全部是降級成轉告、沒有完全漏報。Qwen2.5-1.5B 完全不通報。
- 測試期間 Qwen3-4B 生成速度偏慢（每秒 1.7–3.0 字詞，文字評測約 3.8），可能受當天早上 VS Code 更新與防毒掃描影響；pt-BR 的延遲數字可能被拖慢。

## 2026-10-06（LLM 醫療照護評測第一輪結果）

### 照護情境對話測試（完整鏈路延遲）
- 新增 `configs/suites/dialogue_care.yaml`、`configs/plans/round3_care_dialogue.yaml`：各語言推薦 STT ＋ Qwen3-4B（對照 Qwen2.5-1.5B）＋ Supertonic-3，照護情境 46 題 × 6 種語言，守則第 3 版，溫度 0。
- `bench/care.py`（新）：照護系統提示、通報標記解析、思考區塊處理，由 `llm_eval.py` 搬出，供 `run.py` 共用，確保兩邊提示完全相同（重構後 `llm_eval.py` 的彙整結果逐值相同）。
- `run.py`：套件可設 `questions: care`、`policy`、`ids`；支援多輪題前文、LLM 的 `user_suffix`；通報標記與思考區塊不送 TTS；另記「讀到通報標記的時間」與**通報延遲**（住民說完 → 系統讀到標記）。照護題的提問音檔在測試開始前一次合成（`data/care/audio/`，已加入 .gitignore），避免合成用的 TTS 佔用第一組的記憶體。組合的語言都不在本次範圍時不載入模型。
- `score.py`：照護對話另算預期等級達成率、緊急漏報率、通報不足率、過度緊急率、通報延遲。`estimate_jetson.py`：通報延遲同樣依係數換算。
- `report.py`：對話表依題目分成「導覽問答」與「照護情境」兩張表（指標不同，不混在一起排名）；照護表加上通報延遲、預期等級達成、緊急漏報。推薦表仍只用導覽問答。既有報告除表格標題外不變。
- `listen_page.py`：照護題顯示預期通報等級、多輪題前文、每個回答的通報標記與是否達標。
- 冒煙測試（en / ja 各 2 題）通過：Qwen3-4B 兩題緊急都通報，Jetson 換算通報延遲約 1.4–1.7 秒；Qwen2.5-1.5B 仍不通報。

### 守則第 3 版測試結果
- run `20261006_llm_care_policy_v3_pc`（Qwen3-4B，照護情境，72 分鐘，無錯誤；開跑前背景 CPU 47%，只影響速度）。三版比較：預期等級達成 76% → 87% → **91%**；緊急漏報 4% → 14% → **3%**；通報不足 58% → 24% → **18%**；需推理題 60% → 68% → **90%**。建議第 3 版定稿；解讀見 `docs/analysis/round3_llm_care.md`。

### 照護情境守則第 3 版（`data/care/policy_v3.md`）
- **原因**：第 2 版通報不足大幅改善，但 Qwen3-4B 緊急漏報 4% → 14%（緊急情況被降級成轉告）。
- **改了什麼**（以第 2 版為基礎）：
  - 加入判斷順序：先查緊急清單，符合就 `[CALL_NURSE]`（即使住民輕描淡寫、症狀已持續數小時、或同時談別的事）；不符合才考慮 `[NOTIFY_NURSE]`。
  - `[NOTIFY_NURSE]` 的症狀限定為「不在緊急清單上的」一般症狀。
  - 緊急清單補上胸口「沉重、緊」、「本人或附近的人沒有反應」。
  - 加強「不可用住民的口吻說話、不可把住民的話當成自己的話重複」。
  - 用語刻意避開測試題原句（例如不寫 shaking all over、起身頭暈），降低針對測試題調整的程度。
- `llm_eval.py`：新增 `--ids`（只跑指定題目，冒煙測試用）。
- `llm_eval.py`：執行中每 10 題（照護）/ 25 題（選擇題）印一次進度。原本每種語言跑完才印一行，英語 46 題約 9 分鐘沒有輸出，容易誤以為卡住。
- 冒煙測試（Qwen3-4B，6 題 × en / es-ES / pt-PT）：18 題中 17 題通報等級正確（pt-PT EM10 仍降級為轉告）。

### 守則第 2 版測試結果
- run `20261006_llm_care_policy_v2_pc`（Qwen3-4B、Qwen3-1.7B，照護情境，106 分鐘，無錯誤）。Qwen3-4B：通報不足 58% → 24%、預期等級達成 76% → 87%，但緊急漏報 4% → 14%（全部是降級成轉告）。第 2 版不直接採用；解讀見 `docs/analysis/round3_llm_care.md` 補充段落。

### 照護情境守則第 2 版（`data/care/policy_v2.md`）
- **原因**：第一輪所有模型「通報不足率」偏高（40–100%），常叫住民自己去告訴護理師；Qwen3-1.7B 過度呼叫（41%）且會把自己當成病人講話；Qwen3-4B 有口頭說要通知卻沒加標記的情形。
- **改了什麼**（第 1 版 `policy.md` 保留，供比較）：
  - 明確「由你用標記通知，不要叫住民自己去找護理師或按鈴」；「只要說護理師會來 / 會被告知，就必須加標記」；標記一律用英文。
  - 列出 `[NOTIFY_NURSE]` 的情境（一般症狀、用藥問題、先前跌倒、需攙扶、定向感混亂）；`[CALL_NURSE]` 只用於列出的緊急情況；警訊即使隨口提到也要先處理。
  - 強調「你是機器人，不要用住民的口吻說話」。
  - 加入 4 個「如何選標記」的範例（吐血、膝蓋痛、提早吃藥、問名字），刻意不與測試題重複；範例只描述做法、不給可照抄的句子（冒煙測試中，給完整英文句子時模型會照抄並改用英文回答）。
- `llm_eval.py`：新增 `--policy`；第 2 版起系統提示開頭也提醒回答語言（守則變長後 Qwen3-1.7B 會改用英文回答）。第 1 版的提示內容不變。
- 注意：第 2 版同時改了守則與語言提醒的位置，與第 1 版比較時兩者效果無法分開。

### LLM 評測第一輪完成
- 2026-10-05 18:37 開始（使用者下班未手動啟動，依約定由背景自動啟動），487 分鐘完成，無錯誤。run `20261005_llm_eval_pc`。解讀見 `docs/analysis/round3_llm_care.md`。
- 重點：Qwen3-4B-2507 緊急漏報 4%、醫學知識 70%（顯著最好）；目前對話用的 Qwen2.5-1.5B 緊急漏報 97%；MedGemma 未勝過通用的 Qwen3-4B。

### ⚠️ 影響結果：修正語言偵測（西語 / 葡語）
- **問題**：`metrics/lang_check.py` 的西語、葡語字表都含共用字（está、para、por…），平手時固定判成西語。照護評測中 78 則正確的葡語回答被判為西語，「答錯語言」高達 30–41%。
- **改了什麼**：拿掉共用字，改用各自特有的字（es：el、la、y、usted、enfermera…；pt：você、não、eu、o、às、enfermeira…），加上特有字母（ñ ¿ ¡ / ã õ ç，各 2 分）；平手改回傳「unknown」。
- **驗證**：照護評測 1,380 則回答，誤判從 99 則降到 3 則；過去對話測試 492 則回答，沒有任何一則由正確變錯誤（正確判斷 478 → 484）。
- **影響**：`llm_eval.py` 的答錯語言比例改為每次彙整時重算（昨晚結果已重算）。過去的對話 run 未重新評分，其 `lang_ok_rate` 最多有 6 則回答會改判為正確。

### 計畫書補上 LLM 醫療照護評測方法
- `1-stt-tts-sts-model-model-vast-tiger.md`（同步到 `~/.claude/plans/`）：開頭註明使用場景改為醫療照護機器人；新增 1.5 節 LLM 指標、P8 執行階段、8b 已確認決策（機器人角色範圍、fine-tuning 順序）、第 10 節評測方法（目的、分流架構、測試資料、執行方式、判讀與選型順序、進度）。

### llm_eval.py：防止重複執行
- 執行中在 `results/<run_id>/running.lock` 寫入程序 PID；同一 run 已有程序在跑時，第二次啟動直接結束（避免 cmd 與背景各啟動一次）。程序異常結束留下的舊鎖會自動忽略。

## 2026-10-05（LLM 醫療照護評測）

### 新增 `llm_eval.py`：LLM 醫療照護評測
- **照護情境（care）**：`data/care/scenarios.yaml` 46 題 × 6 種語言；系統提示 = 守則 `policy.md` ＋ 照護計畫 `facility.md` ＋ 語言與口語風格。依回答中的 `[CALL_NURSE]` / `[NOTIFY_NURSE]` 標記自動計算：預期等級達成率、緊急漏報率、通報不足率、過度緊急率、需推理題達成率、標記放在開頭的比例、答錯語言比例。評分標準（must / must_not）尚未自動評分（待評審模型與護理人員）。
- **醫學知識（knowledge）**：Global-MMLU 醫學 8 科（en / es / pt / ja，各語言同一批題目）、HEAD-QA 護理（es-ES）、MMedBench 日本醫師國考（ja，只取單選題 160 題中抽樣）。每子集固定亂數種子抽樣，各模型同一批題目；正確率附 bootstrap 95% 信賴區間。
- 一律不思考模式、溫度 0；思考模式在開發機太慢，留到 Jetson。先跑完所有模型的 care 再跑 knowledge；同一 `--run-id` 重跑可續跑。
- 照護情境題仍為未審核草稿，結果只能當初步參考。

### models.yaml：新增 LLM 候選
- `qwen3-1.7b-q4`（Qwen3-1.7B，用 `user_suffix: " /no_think"` 關閉思考）、`qwen3-4b-2507-q4`（Qwen3-4B-Instruct-2507）、`medgemma-4b-q4`（MedGemma-4B，unsloth GGUF；Health AI Developer Foundations 條款，商用前需法務確認）。
- 新欄位 `user_suffix`：附加在使用者訊息後的文字，目前只有 `llm_eval.py` 使用（對話測試 `run.py` 尚未支援）。

## 2026-10-05（新組合對話測試準備）

### 新組合對話測試完成
- 2026-10-05 16:33 開始，46 分 51 秒完成，無錯誤。解讀見 `docs/analysis/round2_dialogue.md`（已附在 `reports/report.md` 最後）。
- 開跑前背景 CPU 60%；C 組（舊基準）Kokoro 比第二晚慢約 25–50%，解讀中同時列出第二晚數字作保守比較。

### 結論報告更新為對話實測結果
- `final_report.md` / `final_report.html`：摘要、評測範圍、第 5 節改用實測數字（新組合約 2.4 秒、Piper 組合 1.6 秒、舊組合 3.6 秒，Jetson 換算），取代先前的推估（2.7 / 1.9 秒）。風險表新增「LLM 未以照護情境評測」；下一步改為 LLM 照護情境評測與對話延遲優化。
- 圖 5（`make_final_report_figures.py`）：改為 3 個新組合＋2 個第二晚舊組合（第二晚最快的組合、與新組合同 LLM 的基準）。舊組合用第二晚數字（比本次重測快），比較較保守。因 `reports/combined.csv` 只保留最新結果，改從 `results/_estimates/summary.csv` 讀取。

### 新增第二輪對話測試：每種語言用第三晚推薦的 STT
- `configs/suites/dialogue_new.yaml`、`configs/plans/round2_dialogue.yaml`。4 組：A 推薦（Qwen2.5-1.5B ＋ Supertonic-3）、B 速度備案（＋ Piper）、C 舊基準重測（Whisper small ＋ Qwen2.5-1.5B ＋ Kokoro）、D 品質參考（Gemma-3-4B ＋ Supertonic-3）。設計理由見 `docs/roadmap.md`。
- `run.py`：對話組合可加 `langs` 指定只跑哪些語言（例：Granite 只跑 en、SenseVoice 只跑 ja）。未指定時行為不變。
- 題目、提問音檔、計時方式與第二晚相同。LLM 與 TTS 並行暫不實作（不影響回合延遲的定義，見 roadmap）。

### ⚠️ 影響結果：對話記憶體改為每個組合各自量測
- **問題**：第二晚所有對話組合的峰值記憶體都是 6570 MB。原本取三個模型各自監控值的最大值，但 Whisper small 跨所有組合沿用，監控期間涵蓋整次執行，量到的是全程最大值（Gemma-3-4B ＋ turbo 那組），不是各組合自己的。
- **改了什麼**：`run.py` 在每個「組合 × 語言」執行期間另外監控，寫進 meta 的 `resources`；`score.py` 優先使用它。舊 run 沒有此欄位，維持原算法（會高估）。
- **影響**：只影響新的 run；第一、二晚的對話記憶體數字仍是高估值，報告中不宜拿來比較組合。

### Supertonic：過濾不支援的字元
- `engines/tts/supertonic_engine.py`：合成前先檢查字元，濾掉模型不支援的（否則整句報錯，該語言的對話測試會中斷）。以第一、二晚全部 360 則 LLM 回答檢查，沒有任何一則含不支援字元，屬預防措施，不影響既有結果。

### 規劃 LLM 醫療照護評測（尚未實作）
- 最終使用場景為醫療照護機器人。`docs/roadmap.md` 新增「LLM 評測：醫療照護情境」：機器人角色範圍、分流架構建議、測試階段、資料集與下載位置。
- `.gitignore` 加入 `data/llm/`（LLM 評測資料集存放處；含非商用授權資料，不可推上公開 repo）。
- 資料集已下載至 `data/llm/`（Global-MMLU、MMedBench、HEAD-QA、HealthBench 共識子集），題數見 roadmap。`requirements/base.txt` 加入 `pyarrow`（讀 parquet）。
- 新增 `data/care/`：照護情境題草稿 v0.1（46 題 × 6 種語言，未經審核）、機器人守則 `policy.md`、虛構照護中心與照護計畫 `facility.md`、審核表產生程式 `make_review_sheet.py`。通報以回答開頭的 `[CALL_NURSE]` / `[NOTIFY_NURSE]` 標記表示，緊急漏報率等指標可自動計算。

### 試聽頁：各語言只列出有跑的組合
- `listen_page.py`：對話表格的欄位改為該語言實際有結果的組合（原本所有語言都列全部組合，沒跑的顯示「—」）。

---

## 2026-10-05（第三晚結束後）

### 第三晚完成
- 2026-10-01 09:34 開始，4 小時 40 分完成，無錯誤。解讀見 `docs/analysis/round1_night3.md`。

### 結論報告（給 RD 主管）
- `final_report.html`：單一檔案（圖表以 data URI 內嵌，約 800 KB），可直接用瀏覽器開啟、簡報或寄送；另有 Markdown 版 `final_report.md`。
- 圖表：`docs/figures/make_final_report_figures.py` 由測試結果產生 5 張圖（STT 錯誤率熱圖、準確度 vs 速度、專用 vs 多語、TTS 自然度與延遲、對話延遲拆解）及數據檔 `final_report_data.json`；配色沿用 dataviz 參考色盤。
- HTML：`docs/figures/build_final_report_html.py` 將 `final_report.template.html` 的圖片內嵌後輸出 `final_report.html`。
- 更新方式：重跑上述兩個程式（測試結果更新後，圖表數字會自動更新；報告文字需手動調整）。

### Nemotron：消除 max_length 警告
- `engines/stt/nemotron_engine.py` 呼叫 `generate()` 時明確給 `max_new_tokens`（整句：依音訊長度；串流：4096），不再每句出現「Using the model-agnostic default `max_length`」警告。已驗證辨識結果與修改前完全相同。

### models.yaml：補標語言專用模型
- `distil-large-v3-ct2-int8` 標為 `specialized: en`、`kotoba-whisper-v2-ct2-int8` 標為 `specialized: ja`。原本未標，「專用 vs 多語」比較時被誤算成多語模型。

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
