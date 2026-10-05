# 待辦測試與後續工作

狀態：✅ 完成　⏳ 進行中　📋 待辦。完成或變更時更新本檔；實際的程式與設定修改記錄在 `CHANGELOG.md`。

## 第一輪（P3 初篩）進度

| 狀態 | 項目 | 內容 |
|---|---|---|
| ✅ | 第一晚（2026-09-29） | TTS、對話、STT 小模型（tiny / base / small / distil-large-v3 / kotoba-whisper v2），8h54m。解讀見 `docs/analysis/round1_night1.md` |
| ✅ | 第二晚（2026-09-30） | 對話重跑、pt-PT 小模型重測、Whisper medium 與 large-v3-turbo（每語言 50 句），7h39m。解讀見 `docs/analysis/round1_night2.md` |
| 📋 | 待決定 | 對話延遲分數全為 0 的評分問題：新增延遲門檻或放寬刻度（見第二晚解讀「已知問題」） |
| ❌ | 第三晚原訂 large-v3 | 已取消（2026-09-30）：超出 STT 記憶體預算，且評測以小模型為主 |
| ✅ | 第三晚（2026-10-01） | 排行榜新模型：9 個小型 STT、Nemotron 串流、Supertonic-3 TTS，4h40m。解讀見 `docs/analysis/round1_night3.md`。重點：Parakeet-v3 為西語／巴西葡語最佳；巴西葡語 Parakeet 解決 pt-PT（12.8%）；SenseVoice、Parakeet-ja 解決日語；Supertonic-3 是唯一支援全部語言的 TTS 且自然度最高 |
| 📋 | 下一步 | ① 人工聽測（Supertonic pt-PT 口音、西語方言）② 巴西葡語 Parakeet 量化成 int8 ③ 用新的最佳組合重跑對話測試 ④ Jetson 實測 |
| 📋 | 第三晚之後 | 撰寫第二、三晚解讀；small 與大模型在相同 50 句上比較；專用 vs 多語比較；選出 STT、TTS、LLM 短名單 |

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
