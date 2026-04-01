# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案簡介

台灣高鐵（THSR）自動訂票助理，支援 CLI 互動模式與 Web API 模式。透過 CNN 模型自動解 CAPTCHA，完成三步驟訂票流程。

## 常用指令

### 安裝依賴

```bash
uv sync           # 推薦（使用 uv）
pip install -r requirements.txt  # 備用
```

### 執行

```bash
python thsr_ticket/server.py     # Web 模式，http://localhost:8000
python thsr_ticket/main.py       # CLI 互動模式
docker-compose up                # Docker 模式
python scripts/batch_book.py     # 批次非同步訂票
```

### 測試與檢查

```bash
make test         # pytest ./thsr_ticket/unittest
make check        # mypy + flake8 + pylint
make check-mypy   # 只做型別檢查
make check-flake  # 只做風格檢查
make all          # check + test（預設目標）
```

單一測試：

```bash
pytest thsr_ticket/unittest/test_http_request.py
pytest thsr_ticket/unittest/model/test_booking_form.py
```

## 架構說明

### 三步驟訂票流程

`thsr_ticket/controller/booking_flow.py` 編排整個流程：

1. **First Page** (`first_page_flow.py`) — 送出訂票表單並解 CAPTCHA（最多重試 1 次）
2. **Confirm Train** (`confirm_train_flow.py`) — 從可用班次中自動選取（支援 preferred trains）
3. **Confirm Ticket** (`confirm_ticket_flow.py`) — 確認乘客資訊，完成訂票

### Web 模式 vs CLI 模式

- Web 模式使用 `NonInteractiveFirstPageFlow`（無互動提示），由 `server.py` 的 FastAPI 應用呼叫
- CLI 模式使用 `BookingSystem`（`booking_system.py`），包含互動提示

### 層次結構

- `controller/` — 業務流程編排（使用 `remote/` 發送 HTTP、`view_model/` 解析回應）
- `model/` — Pydantic 資料模型與 TinyDB 持久化（`model/db.py`，存於 `.db/history.json`）
- `view_model/` — HTML 解析（繼承 `AbstractViewModel`，用 BeautifulSoup4）
- `remote/` — HTTP session 管理（維護 JSESSIONID cookie）
- `ml/` — CaptchaSolver 單例（CNN 模型，權重在 `ml/checkpoints/`）
- `configs/web/` — 車站 enum、時刻表對應、HTTP endpoint 設定

### API Endpoints（Web 模式）

| Method | Path | 說明 |
|--------|------|------|
| GET | `/api/stations` | 取得所有車站列表 |
| GET | `/api/history` | 取得歷史訂票紀錄 |
| POST | `/api/book` | 執行訂票，回傳 `{ status, message, data }` |

### 時間格式

前端送 24 小時制（如 `"1900"`），後端轉換為 THSR 格式（如 `"700P"`）。特殊值：`"1200N"` = 中午，`"1200M"` = 午夜。詳見 `configs/common.py`。

### 車票類型格式

格式為 `"數量代碼"`，例如 `"2F"` = 2 張全票。代碼：`F` 全票、`H` 孩童、`W` 身障、`E` 敬老、`P` 大學生。

### 已知錯誤處理

系統會靜默吞掉以下已知錯誤（不記錄 stack trace）：`"Preferred trains"`、`"Sold out"`、`"System busy"`、`"Too late"`、`"Max retries exceeded"`。相關邏輯在 `server.py` 與 `first_page_flow.py`。

## 重要設定

- HTTP timeout：10 秒（`configs/web/http_config.py`）
- HTTP adapter max_retries：0（fail-fast 策略）
- Python 版本：3.13（`pyproject.toml`）
- THSR base URL：`https://irs.thsrc.com.tw`
