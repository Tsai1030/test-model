### 第一輪・第三晚結果解讀（2026-10-01 執行，2026-10-05 撰寫）

#### 執行概況

| 項目 | 內容 |
|---|---|
| 測試範圍 | 排行榜新模型：多語 STT（Qwen3-ASR-0.6B、Nemotron-3.5-ASR-Streaming、Parakeet-TDT-0.6B-v3、SenseVoice-Small）、語言專用 STT（Parakeet-ja、Moonshine-tiny-ja、Parakeet-v2、Granite-Speech-5.0-470M、Parakeet-v3 巴西葡語微調版）、Nemotron 串流模式、Supertonic-3 TTS |
| 耗時 | 4 小時 40 分（多語 STT 3h05m、專用 STT 20m、串流 40m、TTS 33m），無執行錯誤 |
| 資料 | 與第一、二晚相同（每語言前 100 句），所有模型在**相同句子**上比較；評分已統一數字寫法 |

#### STT：各語言最佳模型（相同句子上的錯誤率；日語為 CER）

turbo、medium 只測了前 50 句，其餘為 100 句；「相對 small」為配對 bootstrap 差距，括號內為 95% 信賴區間。速度為 Jetson 理論換算（本機 ÷ 係數），僅供排序。

| 語言 | 第一名 | 第二名 | 其他重點 | whisper-small |
|---|---|---|---|---|
| en | Qwen3-ASR 4.9% | Granite-470M（英語專用）5.4% | Parakeet-v2（英語專用）6.0%；turbo 5.9%（50 句） | 6.9% |
| es-ES | **Parakeet-v3 4.1%**（−5.6%，顯著） | turbo 5.6%（50 句） | Nemotron 6.2%、Qwen3 6.4% | 9.8% |
| es-419 | turbo 2.5%（50 句） | **Parakeet-v3 3.5%**（−2.0%，顯著） | Qwen3 3.7%、Nemotron 4.5% | 5.6% |
| pt-BR | **Parakeet-v3 4.6%**＝巴西葡語 Parakeet 4.6% | turbo 5.0%（50 句） | Nemotron 6.0%、Qwen3 6.8% | 7.0% |
| **pt-PT** | **巴西葡語 Parakeet 12.8%**（−23.4%，顯著） | turbo 16.3%（50 句） | Qwen3 23.7%、Parakeet-v3 27.9%、Nemotron 30.4% | 36.2% |
| ja | turbo 6.4%（50 句） | **SenseVoice 6.8%** ≈ Parakeet-ja 6.9% | Qwen3 7.8%、kotoba 8.1%、Moonshine-tiny-ja 12.9%、Nemotron 12.8% | 11.0% |

- **Parakeet-v3 是西語、巴西葡語的最佳選擇**：比 small 顯著更準，Jetson 換算延遲約 0.3–0.8 秒（small 約 1.3–1.5 秒），記憶體約 1.3 GB。但它不接受語言參數（自動判斷語言），英語只有 8.3%，比 small 差。
- **pt-PT 終於有快速的解法**：巴西葡語微調的 Parakeet 在 pt-PT 上 12.8%，比 turbo（16.3%）還準，速度快很多（Jetson 換算約 0.35 秒）。推測是 podcast 語料微調提升了葡語整體的穩健性。缺點是只有 fp32 版本（本機約 3.1 GB），**需要自行量化成 int8**（預估約 1 GB）才符合預算。
- **日語**：SenseVoice（6.8%）和 Parakeet-ja（6.9%）都比 small（11.0%）顯著更準，而且非常快；**SenseVoice 記憶體只要約 0.3 GB**，Jetson 換算延遲約 0.45 秒。
- **Nemotron 的準確度令人失望**：西語、巴西葡語還不錯，但英語（9.7%）、日語（12.8%）比 small 差，pt-PT（30.4%）不合格。
- **Qwen3-ASR** 是唯一在 6 種語言都還不錯的小型多語模型（pt-PT 23.7% 偏高），但它是 LLM 式模型，延遲較長（Jetson 換算約 0.9–3.1 秒）。
- **Moonshine-tiny-ja**（2,700 萬參數）比 small 略差，但小非常多，可當極低資源情境的備案。

#### 專用 vs 多語（相同 100 句，配對 bootstrap）

| 語言 | 最佳專用 | 最佳多語 | 差距（95% CI） | 結論 |
|---|---|---|---|---|
| en | Granite-470M 5.4% | Qwen3-ASR 4.9% | +0.6%（−0.3%～+1.5%） | 不顯著 → 多語即可 |
| pt-BR | 巴西葡語 Parakeet 4.6% | Parakeet-v3 4.6% | +0.0%（−0.9%～+1.0%） | 不顯著 → 多語即可 |
| **pt-PT** | **巴西葡語 Parakeet 12.8%** | Qwen3-ASR 23.7% | **−11.0%（−15.2%～−6.9%）** | **專用顯著較好** |
| ja | Parakeet-ja 6.9% | SenseVoice 6.8% | +0.1%（−1.8%～+2.4%） | 不顯著 → 多語即可 |
| es-ES / es-419 | — | — | — | 沒有專用候選 |

依決策規則（顯著且差距 ≥ 2 個百分點才採用專用模型），**只有 pt-PT 應該用專用（葡語）模型**，其他語言多語模型就夠了。

#### 串流（Nemotron，區塊 560 ms，每語言 20 句）

- **串流不損失準確度**：串流與整句的錯誤率幾乎相同（只有 pt-BR 差 0.8 個百分點）。
- **這台 CPU 跟不上即時速度**：首段文字 2.6–4.5 秒才出現，說完話後還要 2.5–7.0 秒，延遲數據無法代表 Jetson。串流的實際效益要在 Jetson GPU 上量。
- 由於 Nemotron 本身的準確度在英語、日語、pt-PT 上不理想，串流目前不足以讓它勝出。

#### TTS：Supertonic-3 表現亮眼

| 語言 | Supertonic-3 | Kokoro | Piper |
|---|---|---|---|
| en | UTMOS 4.49 / 回測 1.3% | **4.50** / 0.0% | 4.39 / 1.3% |
| es-ES | **3.97** / 4.3% | 3.58 / 0.7% | 2.52 / 0.7% |
| es-419 | **3.94** / 5.1% | 3.48 / 0.6% | 3.08 / 3.9% |
| pt-BR | **4.18** / 2.8% | 3.70 / 0.0% | 3.50 / 3.5% |
| pt-PT | **4.15** / 4.8% | 不支援 | 2.76 / 12.4% |
| ja | **4.23** / 2.8% | 3.81 / 2.1% | 不支援 |
| 首段延遲（Jetson 換算） | 約 0.9–1.1 秒 | 約 1.0–1.7 秒 | **約 0.2–0.3 秒** |
| 記憶體 | **約 0.5 GB** | 約 1.5 GB | 約 0.8 GB |

- **Supertonic-3 是唯一支援全部 6 種語言的 TTS**，自然度（UTMOS）在 5 種語言第一、英語與 Kokoro 並列，記憶體最小。**有機會成為單一通用 TTS**。
- 回測錯誤率（2.8–5.1%）略高於 Kokoro，西語約 4–5%，需人工確認是否有唸錯。
- **口音未確認**：Supertonic 不區分 pt-PT / pt-BR、es-ES / es-419，需母語者確認 pt-PT 聽起來是否像葡萄牙口音。
- 首段延遲比 Piper 慢，但比 Kokoro 快。

#### 更新後的推薦（暫定）

| 語言 | STT | TTS |
|---|---|---|
| en | whisper-small 或 Parakeet-v2（英語專用，較快） | Supertonic-3（或 Piper：速度優先） |
| es-ES | **Parakeet-v3** | **Supertonic-3** |
| es-419 | **Parakeet-v3** | **Supertonic-3** |
| pt-BR | **Parakeet-v3** | **Supertonic-3** |
| pt-PT | **巴西葡語 Parakeet**（需量化成 int8） | **Supertonic-3**（口音待確認） |
| ja | **SenseVoice** 或 Parakeet-ja | **Supertonic-3** |

- **STT 最精簡的部署**：Parakeet-v3（en / es / pt-BR）＋巴西葡語 Parakeet（pt-PT）＋SenseVoice（ja）三個模型；或以 Qwen3-ASR 單一模型涵蓋全部語言（pt-PT 較弱、延遲較長）。
- **TTS**：Supertonic-3 單一模型涵蓋全部語言，前提是口音與唸錯情形通過人工聽測。

#### 注意事項

- **記憶體**：torch 模型（Qwen3-ASR、Nemotron、Granite）在 CPU 上以 fp32 執行，本機量到約 2–3 GB；Jetson GPU 上以 fp16 執行約減半。報告的記憶體門檻判定（`FAIL:memory`）因此對它們偏嚴。
- **速度**：全部是理論換算，Jetson 實測可能差很多。
- **Parakeet-v3 不接受語言參數**：在多語環境中若誤判語言（例如把葡語判成西語），錯誤率會上升；本次測試結果已包含這個影響。
- **自然度**：UTMOS 以英語資料訓練，非英語只能比較相對高低。

#### 下一步

1. **人工聽測**：特別是 Supertonic-3 的 pt-PT 口音、西語兩種方言，以及回測錯誤率較高的句子。
2. **巴西葡語 Parakeet 量化成 int8**，確認準確度不變、記憶體符合預算。
3. **用新的最佳組合重跑對話測試**（例如 Parakeet-v3 / SenseVoice + Qwen2.5-1.5B + Supertonic-3），量化端到端延遲的改善。
4. **Jetson 實測**：Parakeet、SenseVoice、Supertonic 的實際速度，以及 Nemotron 串流的真實延遲。
