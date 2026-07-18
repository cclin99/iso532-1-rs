# 架構評估：三種交付方案與 repo 切分（2026-07-18）

> 評估問題:同時提供三種方案給使用者，目前架構是否可行？分 3 個 repo 還是 2 個？
>
> 1. 靜態計算 + C-ABI + Python 對接
> 2. 動態引擎 + C-ABI + Python 接口
> 3. 動態引擎 + 顯示面板（GUI / VST）

## 結論

**目前架構可行，不需為了同時出三種方案而重構。分 2 個 repo**：現有 D:\ISO532 作為「引擎 repo」同時承載方案 1+2；顯示面板另開「應用 repo」。分 3 個是錯誤方向。

## 現況盤點

`iso532-ffi` 與 `iso532-py` 皆以 `path = "../iso532"` 直接依賴同一核心 crate；核心內靜態（zwst）與動態（zwtv batch + `ZwtvStream`）共用同一套 filterbank/loudness kernel。

| 交付面 | 靜態（方案1） | 動態（方案2） |
|---|---|---|
| Rust core | ✅ | ✅ |
| C-ABI（iso532.h） | ✅ | ✅ `iso532_stream_*`（v1 已凍結） |
| Python | ✅ `loudness_zwst` | ⚠️ 僅 batch `loudness_zwtv`；`ZwtvStream` 尚未綁 pyclass（純加法補齊，非結構問題） |

## 為何方案 1、2 不拆開（反對 3 repo）

- 兩者共用同一核心 crate 的 kernel，拆開等於複製 DSP 或引入脆弱的跨 repo 核心依賴。
- **v1 凍結的 header 是單一 artifact，同時涵蓋靜態與串流函式**——拆 repo 會把一個凍結面切成兩半各自演化。
- hash gate 12/12、parity 18/18 等 CI 關卡是共用的，拆開必須複製整套關卡，零收益。

## 為何面板獨立成第二個 repo

方案 3 本質是**應用程式**，不是程式庫：

- **依賴重量**：GUI 框架（egui/iced，VST 路線則 JUCE/nih-plug）會拖大量依賴進 lockfile，污染引擎的確定性建置環境，CI 時間翻倍。
- **發版節奏**：引擎走「凍結 + 逐位確定性」紀律，改動慢、每次過 hash gate；面板是 UI 迭代，改動快、不需逐位關卡。混在一起互相拖累。
- **消費方式乾淨**：面板透過已凍結 C-ABI（或 git tag 依賴 Rust crate）消費引擎，正好是 v1 凍結面的第一個真實用戶，反向驗證 ABI 設計。
- **授權隔離**：VST 路線若用 JUCE（GPL/商業雙授權），獨立 repo 避免污染引擎授權。

## 最終形態

```
repo A（現有 D:\ISO532）— 引擎
  iso532        core（靜態+動態 kernel）
  iso532-ffi    C-ABI → iso532.h + dll/lib（方案1+2 的 C 出口）
  iso532-py     wheel（方案1+2 的 Python 出口）

repo B（新開）— 面板/VST
  依賴 repo A 的 tagged release（C-ABI binary 或 crates.io/git dep）
```

repo A 一次 CI 產出全部函式庫 artifact（crate、header+dll、wheel），三種方案使用者各取所需。

## 待辦（不急）

- repo A 三個 crate 為兄弟目錄、無 root workspace `Cargo.toml`——開面板前補一個，統一 `cargo test --workspace`。
- 方案 2 的 py 串流接口（`ZwtvStream` 綁 pyclass）為純加法，可排入下一輪 Codex 工作。
