# Is NCU Down ?

中央大學的網站太容易當機了，平均一星期炸一次。

這是一個嘲諷 NCU 的 Discord 機器人：每分鐘檢查一次學校網站，炸了就在頻道裡公告，復活了再告訴大家這次炸了多久。

## 功能

### 被動偵測

- 每 1 分鐘先 ping 一次 `google.com`，確認是自己的網路沒問題；連 Google 都連不上就略過這一輪
- 接著檢查 `web_list.json` 中所有網站，**連續 2 次**沒回應才算連接失敗
- 網站炸**超過 5 分鐘**才會發 embed 到所有已註冊的頻道，短暫抽風不會洗版：
  - :boom: **網站炸了**（附上原因，例如逾時、HTTP 503）
  - :sparkles: **網站復活了**，這次炸了 `<時間>`（只有發過「炸了」的網站才會發）
- 每次當機（包含不到 5 分鐘的）都會記錄在 `data/outages.json`

### 更新公告

- 機器人啟動時若發現版本和上次不同，會在通知頻道公告更新內容

### 主動偵測

- `/is_ncu_alive`：立刻 ping 所有網站，回傳每個網站的延遲與狀態
- 整個機器人共用 10 秒冷卻

### 頻道註冊

- `/notify_channel_register`：讓目前頻道開始 / 停止接收通知（再執行一次就是取消）
- 僅限伺服器管理員使用

## 判斷標準

| 情況 | 結果 |
| --- | --- |
| 有回應，且狀態碼 < 500 | 正常 |
| 逾時（10 秒）、連不上、HTTP 5xx | 連接失敗 |

不驗證 SSL 憑證，避免學校憑證出包時被誤判成炸了。

## 安裝與執行

需要 Python 3.10 以上。

```bash
git clone git@github.com:Gamed1er/IsNcuAlive.git
cd IsNcuAlive

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # 填入你的 Bot Token
python3 main.py
```

機器人上線後，到要接收通知的頻道執行 `/notify_channel_register`。

### Discord Bot 設定

到 [Discord Developer Portal](https://discord.com/developers/applications) 建立 Bot，邀請時需要的權限：

- Scopes：`bot`、`applications.commands`
- Bot Permissions：`Send Messages`、`Embed Links`

不需要開啟任何 Privileged Intents。

## 設定檔

### `.env`

```env
DISCORD_TOKEN=你的機器人Token
```

### `web_list.json`

要監測的網站，每一項代表一個網站：

```json
[
    {
        "name" : "中央大學首頁",
        "url"  : "https://www.ncu.edu.tw"
    },
    {
        "name" : "Portal 入口網站",
        "url"  : "https://portal.ncu.edu.tw"
    }
]
```

修改後需要重新啟動機器人。

### `data/notify_channels.json`

已註冊的通知頻道 ID，由 `/notify_channel_register` 自動管理，不需要手動編輯。

### `data/outages.json`

當機紀錄，每 1 分鐘判斷一次，自動產生：

```json
{
    "name": "ee-class",
    "url": "https://ncueeclass.ncu.edu.tw",
    "start": "2026-11-26T12:02:03",
    "end": "2026-11-26T12:10:03",
    "duration_seconds": 480,
    "reason": "逾時",
    "notified": true
}
```

`end` 為 `null` 代表還在炸；`notified` 代表是否有發出通知。

### `data/version.json`

上次啟動時的版本，用來判斷是否要公告更新。

## 發布新版本

1. 修改 `core/version.py` 的 `VERSION`
2. 在 `CHANGELOG` 最上面新增這次的更新內容
3. 重新啟動機器人，就會自動公告

## 專案結構

```
.
├── main.py                 # 機器人主程式，自動載入 cogs/、廣播到通知頻道
├── cogs/
│   ├── monitor.py          # 被動偵測、/is_ncu_alive、/notify_channel_register
│   └── updater.py          # 版本更新公告
├── core/
│   ├── site_checker.py     # 發送請求、計算延遲（獨立於 Discord）
│   ├── channel_store.py    # 通知頻道的讀寫
│   ├── outage_log.py       # 當機紀錄的讀寫
│   └── version.py          # 版本號與更新內容
├── web_list.json           # 監測的網站清單
├── .env.example
└── requirements.txt
```

## 注意事項

- 重新啟動時會從 `data/outages.json` 還原還沒結束的當機，不會重複通知
- 停機時間從第一次偵測到失敗開始計算，誤差約 1 分鐘
