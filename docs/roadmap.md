# 待辦測試與後續工作

狀態：✅ 完成　⏳ 進行中　📋 待辦　⏸️ 暫緩。完成或變更時更新本檔；實際的程式與設定修改記錄在 `CHANGELOG.md`。

## 第一輪（P3 初篩）進度

| 狀態 | 項目 | 內容 |
|---|---|---|
| ✅ | 第一晚（2026-09-29） | TTS、對話、STT 小模型（tiny / base / small / distil-large-v3 / kotoba-whisper v2），8h54m。解讀見 `docs/analysis/round1_night1.md` |
| ✅ | 第二晚（2026-09-30） | 對話重跑、pt-PT 小模型重測、Whisper medium 與 large-v3-turbo（每語言 50 句），7h39m。解讀見 `docs/analysis/round1_night2.md` |
| ✅ | 對話延遲評分 | 2026-10-01 刻度放寬為 1–10 秒（見 CHANGELOG） |
| ❌ | 第三晚原訂 large-v3 | 已取消（2026-09-30）：超出 STT 記憶體預算，且評測以小模型為主 |
| ✅ | 第三晚（2026-10-01） | 排行榜新模型：9 個小型 STT、Nemotron 串流、Supertonic-3 TTS，4h40m。解讀見 `docs/analysis/round1_night3.md`。重點：Parakeet-v3 為西語／巴西葡語最佳；巴西葡語 Parakeet 解決 pt-PT（12.8%）；SenseVoice、Parakeet-ja 解決日語；Supertonic-3 是唯一支援全部語言的 TTS 且自然度最高 |
| ✅ | 結論報告 | 2026-10-05：`final_report.html` / `final_report.md`（給 RD 主管） |
| ✅ | 新組合對話測試 | 2026-10-05，46m51s。推薦組合（Supertonic）約 2.0–2.6 秒、Piper 組合約 1.5–1.7 秒（Jetson 換算），比舊組合快 30–55%。解讀見 `docs/analysis/round2_dialogue.md` |
| ✅ | LLM 醫療照護評測第一輪 | 2026-10-05 夜間，487 分鐘。首選 Qwen3-4B-2507（緊急漏報 4%、醫學知識 70%）；Qwen2.5-1.5B 不適合（漏報 97%）；MedGemma 無優勢。解讀見 `docs/analysis/round3_llm_care.md` |
| ✅ | LLM 系統提示改進 | 2026-10-06：守則第 2、3 版。Qwen3-4B ＋ 第 3 版：預期等級達成 91%、緊急漏報 3%、通報不足 18%。建議第 3 版定稿 |
| ✅ | 照護情境對話延遲 | 2026-10-07，4h50m。Qwen3-4B 回合延遲約 4.4 秒、通報延遲約 2 秒（Jetson 換算）；語音對話預期等級達成 87%。解讀見 `docs/analysis/round3_care_dialogue.md` |
| ✅ | 照護延遲改進 | 2026-10-08：緊急回應約 0.5–0.75 秒、規則層＋LLM 緊急漏報 0 / 72；第一段字詞數 −33%、回合延遲約 3.5 秒（Jetson 換算）；通報行為改善。解讀見 `docs/analysis/round3_care_fast.md`。下一步：一般回答先播預錄短回應、Jetson 實測 |
| 📋 | LLM 第二輪候選模型 | 2026-10-07 規劃：Phi-4-mini、Ministral 3 3B、Granite 4.1 3B（與 Qwen3-4B 同級的標準 dense 模型）；Qwen3.5-4B 待決定是否納入。條件、排除原因與測試方式見計畫書 10.7 |
| 📋 | LLM 下一步 | 規則層（緊急關鍵字攔截）；新題目驗證（避免針對考題調整，最好由護理人員撰寫）；評分標準評分（評審模型＋護理抽查）；用 Qwen3-4B 實測對話延遲；題目審核；思考版（Qwen3-4B-Thinking-2507）留到 Jetson 或夜間小規模測試 |
| ⏸️ | 暫緩（目前無法進行） | ① Jetson 實測 ② 母語者聽測（Supertonic pt-PT 口音、西語方言）③ 巴西葡語 Parakeet 量化成 int8 ④ 穩健性測試（噪音、幻覺）與自錄導覽語音 |
| ✅ | 第三晚之後 | 第二、三晚解讀；small 與大模型在相同 50 句上比較；專用 vs 多語比較；STT、TTS 推薦（見 `final_report.md`） |

---

## ✅ 第二輪：新組合對話測試（2026-10-05）

目的：第三晚選出更快、更準的 STT 與 TTS 後，實測整條對話鏈路的延遲，驗證結論報告的推估（Supertonic 約 2.7 秒、Piper 約 1.9 秒，Jetson 換算）。

- 計畫：`configs/plans/round2_dialogue.yaml`；套件：`configs/suites/dialogue_new.yaml`
- 每種語言用第三晚推薦的 STT：en → Granite-470M；es-ES / es-419 / pt-BR → Parakeet-v3；pt-PT → 巴西葡語微調 Parakeet；ja → SenseVoice
- 題目、提問音檔、計時方式與第二晚完全相同，可直接比較

| 組 | LLM | TTS | 用途 |
|---|---|---|---|
| A | Qwen2.5-1.5B | Supertonic-3 | 推薦組合（6 種語言） |
| B | Qwen2.5-1.5B | Piper | 速度備案（無日語） |
| C | Qwen2.5-1.5B（STT 為 Whisper small） | Kokoro | 舊基準，同一次執行重測，排除不同天電腦狀態的差異 |
| D | Gemma-3-4B | Supertonic-3 | 品質參考：換較準的 LLM 要多付多少延遲 |

- **LLM 與 TTS 並行暫不實作**：回合延遲只算到「第一段聲音出現」，現行做法已是 LLM 寫完第一句就送 TTS，與並行系統相同；並行只影響後續句子之間的停頓。開發機只有 2 核心，真的並行反而互搶 CPU、數字失真。留到 Jetson 實作。
- 看什麼：A / B 的回合延遲比 C 少多少（各元件拆解）；A 與 D 的事實正確率、延遲差距；各組合的記憶體（本次起每個組合×語言各自量測）
- 注意：題目是博物館導覽，只用來量延遲；事實正確率不能代表醫療照護情境的能力（見下一節）

---

## 📋 LLM 評測：醫療照護情境（2026-10-05 規劃）

最終使用場景是**醫療照護機器人**。博物館題目只是測試情境，LLM 需要另外評測。

### 機器人的角色（評測的前提，需與醫護團隊確認）

機器人是**陪伴與通報者，不是醫護人員**：

| 可以做 | 不可以做 |
|---|---|
| 日常聊天、情緒陪伴 | 診斷（「你可能是 OO 病」） |
| 院方已核定的資訊：作息、探病時間、醫護交代的服藥提醒（照原樣轉述） | 治療或用藥建議、改劑量（「可以多吃一顆」） |
| 一般衛教常識（不針對個人狀況），並建議詢問醫護 | 叫病人「不用擔心、不必找醫生」 |
| **偵測警訊並通報醫護**（胸痛、呼吸困難、跌倒、說話不清、意識改變），寧可多報不可漏報 | 自行判斷「沒事」而不通報 |

- 「判斷緊急狀況」的實際意思是**偵測警訊、交給人**，最後的判斷由醫護人員做。
- LLM 需要的「思考」主要用於：聽懂模糊描述（「我怪怪的」）、適時追問、守住上述規則；不是做醫學推理。
- 法規：若機器人提供診斷或治療建議，可能被視為醫療器材軟體（SaMD），需依當地法規認證。範圍請醫護與法務確認。

### 架構建議：分流，不要每句都讓 LLM 思考

| 情況 | 做法 | 理由 |
|---|---|---|
| 日常回話 | LLM 不思考模式 | 延遲；思考數百字詞在 Jetson 上粗估多等 15–30 秒（依第二晚實測 Qwen2.5-1.5B 6.4、Gemma-3-4B 3.2 字詞/秒 × 換算係數 3） |
| 緊急警訊 | 規則或關鍵字分類器先攔截，固定回應並通報 | 快、可預測、可逐條驗證；不依賴 LLM |
| 需要判斷的問題 | 才開思考模式，先說「請稍等，我確認一下」；或轉給醫護 | 延遲可接受、行為較穩 |

### 測試內容

| 階段 | 測什麼 | 資料 | 指標 |
|---|---|---|---|
| 0 | 定義角色範圍（上表） | 與醫護團隊討論 | — |
| 1 | 醫學知識（初篩） | Global-MMLU 醫學科目、MMedBench、HEAD-QA 護理 | 選擇題正確率＋95% 信賴區間；思考 / 不思考各測一次 |
| 2 | **照護情境行為（主要）** | 自建照護情境題（6 種語言，醫護審核）；HealthBench 共識子集當公開參考 | **緊急情況漏報率（目標 0）**、過度通報率、守規率（不診斷、不給劑量）、評分標準通過率、語言正確率 |
| 3 | 速度與資源 | 沿用對話測試框架 | 第一句延遲、思考字數、記憶體 |
| 4 | 決定是否需要改進 | — | 依序：調整系統提示 → RAG（院內照護手冊、衛教資料）→ 仍不足才 fine-tuning（LoRA） |

- 評分方式：選擇題自動評分；情境題由大模型依評分標準逐項評分，護理人員抽查。題目為自建、不含病人資料，可用雲端模型評分；**真實病人資料不可送出**。
- 自建情境題：**草稿 v0.1 已完成（2026-10-05）**，`data/care/`：46 題 × 6 種語言（緊急 12、症狀 8、超出範圍 7、衛教 4、院內資訊 5、陪伴 5、認知 2、安全隱私 3），附機器人守則、虛構照護計畫與審核表 `review_sheet.csv`。用 `[CALL_NURSE]` / `[NOTIFY_NURSE]` 標記讓通報可自動判斷。**待護理人員與母語者審核**，詳見 `data/care/README.md`。
- 候選 LLM（測試前再查最新排行榜）：可切換思考 / 不思考的通用模型（如 Qwen3 系列）、醫療專用小模型（如 MedGemma-4B），比照 STT 做「專用 vs 通用」比較。

### 資料集（都不需登入；存放於 `data/llm/`，已列入 .gitignore，不可推上 GitHub）

| 資料集 | 語言 | 內容 | 授權 | 下載位置 |
|---|---|---|---|---|
| Global-MMLU（醫學科目：解剖、臨床知識、大學醫學、醫學遺傳、專業醫學、營養等） | en、es、pt、ja | MMLU 多語版，各語言題目相同，可直接比較語言差異 | Apache-2.0 | huggingface.co/datasets/CohereLabs/Global-MMLU（`<語言>/test-00000-of-00001.parquet`，各約 4 MB） |
| MMedBench | en、es、ja（另有 zh、fr、ru） | 各國醫學考試：美國醫師執照、西班牙 HEAD-QA、日本醫師國考 | **CC-BY-NC-4.0（非商用）** | huggingface.co/datasets/Henrychur/MMedBench（`MMedBench.zip`，22 MB） |
| HEAD-QA | es-ES（附英譯） | 西班牙醫療專科考試，取**護理（enfermería）**科目 | MIT | huggingface.co/datasets/dvilares/head_qa（`data/head-qa-es-en-pdfs.zip`，79 MB） |
| HealthBench（共識子集） | 多語 | 醫師撰寫評分標準的健康對話，含緊急轉介、追問情境 | MIT | openaipublic.blob.core.windows.net/simple-evals/healthbench/consensus_2025-05-09-20-00-46.jsonl（37 MB） |

- pt-PT、es-419 沒有專屬的公開醫學資料集：知識用 pt / es 版本，口音與用語在自建情境題補。
- MMedBench 為非商用授權：內部評估作參考可以，用於商用產品決策前請法務確認。
- MMedBench 的西語部分來自 HEAD-QA，整理時需去除重複。

**已下載（2026-10-05，大小與來源一致、壓縮檔完整）**：

| 資料集 | 檔案 | 可用題數（測試集） |
|---|---|---|
| Global-MMLU | `data/llm/global_mmlu/{en,es,pt,ja}_test.parquet` | 醫學 8 科每語言 1,561 題（營養 306、專業醫學 272、臨床知識 265、大學醫學 173、病毒學 166、大學生物 144、解剖 135、醫學遺傳 100），4 種語言題目相同 |
| MMedBench | `data/llm/mmedbench/MMedBench.zip` | en 1,273（4 選 1）、es 2,742（4 選 1）、ja 199（5 選 1） |
| HEAD-QA | `data/llm/head_qa/head_qa.zip` | 護理 455、醫學 463、藥學 457（另有生物、心理、化學） |
| HealthBench 共識子集 | `data/llm/healthbench/consensus.jsonl` | 3,671 段對話，其中緊急轉介 453；以英語為主（粗估：西語約 110、葡語約 80、日語 0） |

- HealthBench 幾乎只有英語：非英語的照護行為要靠自建情境題（或翻譯部分 HealthBench 題目）。
- 實際測試會抽樣（例：每語言 200 題），在開發機上全部跑完太久。

---

## 📋 第三晚：排行榜新模型（小型多語、語言專用 STT 與小型 TTS）

- **目的**：評測以小模型為主（使用者 2026-09-30 決定）。從 Hugging Face 熱門榜與 Open ASR Leaderboard 找出適合 Jetson 規格的新模型，並比較「語言專用模型」是否明顯優於「多語模型」。
- **篩選條件**：參數量約 1B 以下、單一模型記憶體 ≤ 2 GB、授權 PoC 可用、這台 Windows CPU 可跑（先測準確度）且 Jetson 有 GPU 推論路徑。挑選方法見 `docs/model_selection_guide.md`。
- **資料**：與第一輪相同，每語言前 100 句（FLEURS / Common Voice），所有模型在同一批句子上比較；TTS 用同一份導覽文本。
- **調查來源**（2026-09-30）：Hugging Face 熱門榜（ASR / TTS / text-to-audio，各前 60 名）、Open ASR Leaderboard、各模型卡。text-to-audio 榜幾乎都是音樂、音效生成模型，與本專案無關。

### 第三晚在本機測試的候選（官方數字僅供參考，以實測為準）
| # | 類別 | 模型 | 大小 | 本專案語言 | 授權 | 本機執行方式 | 官方公布的準確度 |
|---|---|---|---|---|---|---|---|
| 1 | 多語 STT | Qwen3-ASR-0.6B（2026/1） | 0.6B | en、es、pt、ja | Apache-2.0 | transformers | FLEURS WER：en 4.39、es 3.89、pt 4.55、ja 7.77 |
| 2 | 多語 STT（串流） | NVIDIA Nemotron-3.5-ASR-Streaming-0.6B（2026/5） | 0.6B | en、es、pt（BR/PT）、ja | OpenMDW-1.1（可商用） | transformers | 1.12 秒區塊：en 7.91、es 4.11、pt 5.48、ja CER 11.48 |
| 3 | 多語 STT | NVIDIA Parakeet-TDT-0.6B-v3 | 0.6B | en、es、pt | CC-BY-4.0 | onnx-asr（int8） | FLEURS 25 語平均 11.62 |
| ~~4~~ | 多語 STT | ~~Moondream Parakeet-Redux（2026/9，1.58-bit）~~ **→ 移到 Jetson 階段**（Windows 版缺 AVX2 核心） | 178 MB | en、es、pt | CC-BY-4.0 | moondream（Photon） | FLEURS 25 語平均 10.56 |
| 5 | 多語 STT | SenseVoice-Small | 約 0.23B | en、ja | 模型自有授權 | sherpa-onnx（int8） | — |
| 6 | 日語專用 STT | NVIDIA Parakeet-TDT_CTC-0.6B-ja | 0.6B | ja | CC-BY-4.0 | sherpa-onnx（int8） | JSUT CER 6.4 |
| 7 | 日語專用 STT | Moonshine-tiny-ja | 27M | ja | 自有授權 | transformers | FLEURS CER 17.87 |
| 8 | 葡語專用 STT | Parakeet-v3 ptBR（TAGARELA 微調） | 0.6B | pt-BR | CC-BY-4.0 | onnx-asr | — |
| 9 | 英語專用 STT | NVIDIA Parakeet-TDT-0.6B-v2 | 0.6B | en | CC-BY-4.0 | onnx-asr（int8） | — |
| 10 | 英語專用 STT | IBM Granite-Speech-5.0-470M-TurboCTC（2026/8） | 0.47B | en | Apache-2.0 | transformers | — |
| 11 | 多語 TTS | Supertonic-3 | 99M | en、es、pt、ja（共 31 語） | OpenRAIL-M | supertonic（ONNX） | 10 種預設聲音 |

- 已測過的基準：whisper-small（多語）、kotoba-whisper v2（日語）、distil-large-v3（英語）、Kokoro、Piper（TTS）。

### 串流能力（2026-09-30 查證）
| 類型 | STT | TTS |
|---|---|---|
| ✅ 原生串流 | **Nemotron-3.5-ASR-Streaming**（區塊 80 ms–1.12 s；唯一支援 4 種語言的小型串流 STT） | Qwen3-TTS（首段約 97 ms）、CosyVoice3（約 150 ms，無葡語）——皆需 GPU |
| ⚠️ 有條件串流 | Parakeet-TDT-0.6B-v3（分段模擬，每段約 2 秒，延遲較高）；Qwen3-ASR（僅 vLLM／GPU） | — |
| ❌ 整句處理 / 逐句輸出 | Whisper 全系列、SenseVoice、Parakeet-ja、Parakeet-Redux、Moonshine、Granite、Parakeet ptBR、Parakeet-v2 | Kokoro、Piper、Supertonic-3（逐句合成，第一句完成即可播放） |

- 第三晚：Nemotron 同時測**整句**與**串流**（區塊 160 / 320 / 560 ms）兩種模式，量化串流能省多少時間（首個部分結果延遲、說完話到最終結果的時間）。
- 建議加測：`nvidia/nemotron-speech-streaming-en-0.6b`（英語串流專用），與多語串流模型比較。
- 報告與 `configs/models.yaml` 加入「串流能力」欄位（原生 / 有條件 / 整句）。
- 整句模型不一定不能用：導覽提問多為 3–5 秒短句，若 Jetson 上處理只需 0.1–0.2 秒，體感差異小；需以延遲數據量化比較。
- 未找到公開的小型**歐洲葡語（pt-PT）專用** ASR。pt-PT 的希望在 Nemotron-3.5（官方明列 pt-PT）、Qwen3-ASR、Parakeet 系列（訓練資料含歐洲議會演講）。
- 以 Common Voice 微調的葡語 Whisper 有資料重疊風險（我們的 pt-PT 測試資料也來自 Common Voice），不列入。
- 預估時間：約 5 小時（多數為非自回歸模型，CPU 上速度快；實際以冒煙測試量到的速度為準）。
- 安裝：新套件（onnx-asr、sherpa-onnx、moondream、supertonic）在第二晚結束後才安裝，避免影響執行中的測試；若與 `.venv-core` 衝突，改用獨立環境。

### 需要 GPU，留到 Colab 或 Jetson 階段
| 模型 | 類別 | 原因 |
|---|---|---|
| Moondream Parakeet-Ultra | 多語 STT | 只支援 GPU；官方 FLEURS 25 語平均 9.55，是 Parakeet 系列最準的 |
| Moondream Parakeet-Redux | 多語 STT | 轉接器已寫好（`engines/stt/photon_engine.py`），但 Windows 版 kestrel 沒有 AVX2 核心，本機無法執行；Linux x86 或 Jetson（NEON dotprod）可跑 |
| Fun-ASR-Nano（0.8B） | STT（en、ja） | 較大，CPU 慢 |
| Qwen3-TTS-0.6B-Base | 多語 TTS（en、es、pt、ja） | 需參考錄音複製聲音；需 GPU |
| Fun-CosyVoice3-0.5B | TTS | 無葡語；需 GPU |
| Irodori-TTS-v4.1-Small（0.8B） | 日語專用 TTS | 需 GPU |
| Chatterbox Multilingual、OmniVoice | TTS | 需 GPU；OmniVoice 為 CC-BY-NC。OmniVoice 可指定口音或複製聲音，是 pt-PT 的潛在候選；2026-10-01 使用者決定暫不測 |

### 排除（超過規格或不適用）
- 超過 1B：Qwen3-ASR-1.7B、Cohere Transcribe（2B）、Granite Speech 4.1（2B）、Voxtral Mini（4B）、VibeVoice-ASR（8.7B）、Confucius4（2B）、Audio8-ASR（4B）；TTS：VoxCPM2（2.3B）、Higgs（4.6B）、Breeze-TTS-2（3.5B）、Irodori Large（3.3B）、Fish S2 Pro（4.6B）
- 只支援英語的 TTS：VibeVoice-Realtime、NeuTTS Air
- 禁止商用且有替代方案者：F5-TTS、Fish S1 mini

### 量化比較方式
- 指標：WER / CER（含 95% 信賴區間）、RTF p50 / p90、延遲 p50、峰值記憶體、模型檔案大小、載入時間
- 專用 vs 多語：每種語言取「最佳專用模型」與「最佳多語模型」，在**相同句子**上以配對 bootstrap 計算錯誤率差距的 95% 信賴區間；區間不含 0 才算顯著
- 部署成本：專用方案需同時部署多個模型，計入 Jetson 上的總記憶體與維護成本

---

## 📋 STT 穩健性測試：噪音錯誤率、幻覺率

- **時機**：第一輪結束、選出 STT 短名單之後（計畫書原則：`stt_full` 只跑短名單）。
- **目的**：報告中的「噪音錯誤率」「幻覺率」目前都是「–」，STT 總分的「穩健性（15%）」也因沒有資料而未計入。測完後 STT 排名可能改變。

### 指標
| 指標 | 做法 |
|---|---|
| 噪音錯誤率 | 乾淨錄音混入環境噪音（SNR 10 dB）後重測錯誤率。報告的穩健性分數取 `configs/scoring.yaml` 的 `robustness_condition: snr10` |
| 幻覺率 | 輸入純靜音 / 純噪音片段，STT 仍輸出文字的比例（Whisper 常見問題，例如沒人說話時冒出「謝謝收看」） |

### 步驟
1. **準備噪音來源**（建議）：將環境噪音 wav 放入 `data\noise\`。
   - DEMAND：含餐廳、咖啡廳、廣場等公共空間噪音，最接近博物館人潮
   - MUSAN：較大的噪音資料庫
   - 不提供時，程式以同資料集其他語句混成「人聲嘈雜」噪音代替（較不真實）
2. **產生噪音版資料**（每個語言 × 資料集各一次，共 6 次）：
   ```cmd
   .venv-core\Scripts\python.exe -m bench.augment noisy --lang ja --dataset fleurs --snr 20 10 5 --noise-dir data\noise
   ```
   en、es-419、pt-BR、ja 用 `fleurs`；es-ES、pt-PT 用 `commonvoice`。SNR 20 / 5 可一併產生，之後若要畫「噪音衰減曲線」（計畫書的報告項目）再測。
3. **產生靜音 / 噪音片段**（一次，21 段 × 5 秒：近乎靜音、粉紅噪音、環境噪音）：
   ```cmd
   .venv-core\Scripts\python.exe -m bench.augment silence --n 21 --noise-dir data\noise
   ```
4. **新增縮小版套件與執行計畫**：原本的 `configs/suites/stt_full.yaml`（每語言 300 句 × 4 種條件 × 速度重複測）在本機要跑數十小時，改為：
   - 條件只測 `snr10`（乾淨條件第一輪已測），資料集加入 `silence`
   - 只測短名單 2–3 個模型（預期如 whisper-small、large-v3-turbo，日語加 kotoba-whisper v2）
   - 每語言 100 句（大模型 50 句）
   - 新增 `configs/suites/stt_robust.yaml` 與對應的 plan 步驟，以 `run_all.py` 執行
5. **預估時間**：small 約 1 小時、turbo 約 4–7.5 小時，約一個晚上。

---

## 📋 其他待辦（大致依優先順序）

| # | 項目 | 說明 |
|---|---|---|
| 1 | **人工聽測與評分** | `listening_test.csv`（TTS，1–5 分）、`rating_sheet.csv`（對話相關度、自然度、方言）。可用各 run 的 `listen.html` 試聽。優先確認：① **es-ES**：請西班牙人比較 Kokoro 與 Piper 的自然度與口音；② **es-419**：Kokoro 西語用 espeak-ng 的「es」（西班牙本土）發音規則，拉美西語也套用同一規則，請拉美人確認是否聽起來像西班牙腔（若是，es-419 可能改用 Piper 墨西哥聲音或 Supertonic）；③ Piper pt-PT 是否堪用 |
| 2 | **Jetson 實測與校準** | 以錨點模型（`configs/anchors.yaml`）校準速度換算係數。Kokoro 在 Jetson GPU 上的實測速度將決定 TTS 選 Kokoro 或 Piper；medium / turbo 的 RTF 門檻也要重新判定 |
| 3 | **自建導覽語料** | 計畫書中最重要的測試資料：每語言 50–100 句導覽腳本，含專有名詞、數字、年份，由母語者錄音（`data/prepare_custom.py`、`data/recordings/`）。特別是 pt-PT |
| 4 | **pt-PT STT（若大模型仍不合格）** | NVIDIA Parakeet-TDT-0.6B-v3 / Canary-1B-v2（需 WSL2 或 Colab）；以 faster-whisper 的提示詞功能提示場館名稱等專有名詞 |
| 5 | **pt-PT TTS 替代方案（若 Piper 不堪用）** | Chatterbox、XTTS-v2（需 GPU，可用 Colab）；Piper high 品質聲音；最後手段為錄製葡萄牙人語音微調 |
| 6 | **對話測試改進** | 擴充題目（目前每語言 6 題過少）；加入 Llama-3.2-3B；加入「FAQ 比對」組合（不用 LLM，預寫答案）與 LLM 比較；研究降低延遲的做法（LLM 與 TTS 並行、預錄常見回答） |
| 7 | **自動語言辨識** | `configs/suites/stt_lid.yaml`：測 Whisper 自動判斷語言的準確率 |
| 8 | **語言切換 / 中文支援** | 產品決策待定：是否允許遊客要求改用其他語言回答（需調整 LLM 提示、依回答語言選 TTS 聲音、加入中文聲音與測試） |
| 9 | **其他 TTS** | MeloTTS（需另建環境，無葡語） |
| 10 | **串流式 STT** | 如 sherpa-onnx：可量「首個部分結果延遲」，對降低對話延遲可能有幫助 |
