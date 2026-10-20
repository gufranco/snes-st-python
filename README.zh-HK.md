# Seta ST010、ST011 與 ST018

Seta 為 Super Nintendo 卡帶製造的三款協處理器的 Python 實現。每款都執行讀者自行提供的微碼，並以該微碼停下等待命令的位置作為檢驗基準。

[English](README.md) | [日本語](README.ja.md) | [简体中文](README.zh-Hans.md) | 繁體中文（香港）

[![CI](https://github.com/gufranco/snes-st-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/snes-st-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/snes-st-python)](https://github.com/gufranco/snes-st-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**3** 款晶片，**0** 個人手描述的命令，兩處等待位置均在出貨的微碼上量度，這些等待位置與記錄之間 **0** 處分歧，**793** 個測試，**100%** 語句與分支覆蓋率，無任何依賴

```python
from snesst import Chip

part = Chip("st010")

part.write(0x000000, 0x00)
for at, value in enumerate((0x00, 0x01, 0x00, 0x02)):
    part.write(0x680000 + at, value)
part.write(0x680020, 0x01)
part.write(0x680021, 0x80)
print(hex(part.read(0x680021)))

print(part.finish(), hex(part.read(0x680021)))
print(hex(part.read(0x680010) | part.read(0x680011) << 8))
```

```
0x80
106 0x0
0x9300
```

寫入 `0x000000` 落在共享窗口之下，即處理器的數據埠，使晶片能對啟動位元組作出反應。接下來四個位元組把點 `0x0100, 0x0200` 放在共享記憶體的底部。命令 `0x01` 寫入 `0x20` 的暫存器位元組，啟動位寫入 `0x21` 的暫存器位元組。這次寫入只保存該位，所以緊接著輪詢 `0x21` 的主機讀到 `0x80`，即晶片仍在忙。`finish()` 執行 ST010 自身的程式直至它清除該位，並返回所用的指令數，此命令為 106。答案從同一記憶體的 `0x10` 讀回。此例子需要 ST010 映像檔；沒有映像檔時，`Chip("st010")` 會拋出 `NoFirmware`。

## 安裝

| 需求       | 版本                                       |
| :--------- | :----------------------------------------- |
| Python     | 3.12 或更新版本                            |
| git        | 任何版本，用於取得子模組                   |
| 韌體映像檔 | 每款要建構的晶片一個，從你擁有的硬件上傾印 |

```bash
git clone --recurse-submodules https://github.com/gufranco/snes-st-python.git
cd snes-st-python
python3 snesst/doctor.py
```

套件不匯入標準程式庫以外的任何東西。儲存庫根目錄下有三個子模組：`nec-upd7725-96050-python` 是 ST010 與 ST011 內部的處理器，`arm6-python` 是 ST018 內部的處理器，`snes-driver-python` 只由記錄卡帶交換的工具讀取。從下載 zip 連結取得的原始碼封存檔不含子模組，此時每款晶片都會拒絕建構。

診斷腳本檢查機器、子模組及每款晶片的映像檔，最後輸出一行結果。提交錯誤報告時，請貼上其完整輸出。全新簽出的儲存庫不含映像檔，因此三行晶片檢查都不會通過：

```
  3 of 12 checks did not pass
```

版本發佈遵循 [Semantic Versioning](https://semver.org/)，由 semantic-release 根據提交歷史產生。每個版本都會加上標籤，並列於[版本發佈頁面](https://github.com/gufranco/snes-st-python/releases)。

## 介面

`snesst.Chip(model, **options)` 建構一款晶片。`model` 為必填，比對時不區分大小寫、連字號或底線。ST010 與 ST011 以 `snesst.chip.Chip` 返回，執行 NEC uPD96050。ST018 以 `snesst.ST018` 返回，執行 ARM60。

| 型號    | 別名                             | 處理器   | 映像檔位元組數 | 程式的功能                   |
| :------ | :------------------------------- | :------- | -------------: | :--------------------------- |
| `st010` | `st-010`, `seta010`, `setast010` | uPD96050 |         53,248 | 為一款賽車卡帶提供八個命令   |
| `st011` | `st-011`, `seta011`, `setast011` | uPD96050 |         53,248 | 下將棋                       |
| `st018` | `st-018`, `seta018`, `setast018` | ARM60    |        163,840 | 下將棋，經由一個單位元組信箱 |

### 目錄與錯誤

| 名稱                 | 內容                                                                                           |
| :------------------- | :--------------------------------------------------------------------------------------------- |
| `snesst.MODELS`      | 三個 `Model` 記錄，以標準名稱為鍵                                                              |
| `snesst.Model`       | `name`、`aliases`、`summary` 及 `image`，即其執行的映像檔名稱                                  |
| `snesst.available()` | 一個 dict，包含映像檔存在於本機的每款晶片，每項為一個身份及一個路徑。uPD96050 子模組缺失時為空 |
| `snesst.why_not()`   | 說明為何此處無法建構任何晶片的句子，原因是 uPD96050 子模組或所有映像檔缺失。否則為 `None`      |
| `snesst.ST018`       | ARM 晶片的類別，供直接建構它的呼叫者使用                                                       |
| `snesst.__version__` | 已安裝的版本                                                                                   |

| 錯誤                | 拋出時機                                                                                  |
| :------------------ | :---------------------------------------------------------------------------------------- |
| `UnknownModelError` | 未提供型號，或沒有晶片使用該名稱。訊息會列出可接受的名稱                                  |
| `NoFirmware`        | 處理器子模組未簽出、找不到該晶片的映像檔，或傳入 uPD96050 晶片的映像檔沒有附帶 `identity` |
| `NeverFinished`     | `finish()` 已執行 `patience` 條指令，啟動位仍然設定                                       |
| `WrongShape`        | 映像檔長度與其處理器所需不符                                                              |
| `Unrecognised`      | `snesst.firmware.identify` 遇到 SHA-256 不在清單中的位元組。目錄搜尋則會略過此類檔案      |
| `Corrupt`           | 映像檔的 SHA-256 與清單項目相符，但另一個摘要不符                                         |
| `UnknownPort`       | ST018 的讀寫落在其三個埠以外的位址                                                        |

```python
import snesst
from snesst import Chip, UnknownModelError

for name, model in snesst.MODELS.items():
    print(name, model.aliases)

print(repr(snesst.MODELS["st018"]))

for asked in ("st012", None):
    try:
        Chip(asked)
    except UnknownModelError as refused:
        print(refused)
```

```
st010 ('st-010', 'seta010', 'setast010')
st011 ('st-011', 'seta011', 'setast011')
st018 ('st-018', 'seta018', 'setast018')
<Model st018, running the st018 image>
st012 is not a model this package covers; it has st010, st011, st018
no model was named, and this package will not choose one for you. Name one of: st010, st011, st018
```

### ST010 與 ST011

`Chip("st011", memory=None, fill=0, patience=4000000, boot=200000, image=None, identity=None, images=None)` 列出每個選項及其預設值。

| 選項       | 作用                                                                            |
| :--------- | :------------------------------------------------------------------------------ |
| `memory`   | 握手後複製到共享記憶體的位元組，最多 4,096 個                                   |
| `fill`     | 處理器的暫存器與記憶體在開機時的值                                              |
| `patience` | `finish()` 在 `NeverFinished` 之前可執行的指令數                                |
| `boot`     | 握手的兩次讀取之後、交回晶片之前執行的指令數                                    |
| `image`    | 映像檔位元組。不搜尋任何目錄，也不讀取任何變數                                  |
| `identity` | `image` 是甚麼，以 `snesst.firmware.Identity` 表示。與 `image` 一併使用時為必填 |
| `images`   | 形如 `available()` 的目錄，用於取代本機目錄進行搜尋                             |

| 呼叫                    | 作用                                                                                                                                                    |
| :---------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `read(address)`         | 設定了位 `0x80000` 時，讀取 `address & 0xFFF` 處的共享記憶體位元組。否則讀取數據埠，奇數位址則讀取狀態埠                                                |
| `write(address, value)` | 設定了位 `0x80000` 時，寫入一個共享記憶體位元組，不執行任何程式。否則為一次啟用晶片的寫入，偶數位址時會傳至數據埠                                       |
| `handshake(boot=None)`  | 一條指令、兩次讀取數據埠，然後執行 `boot` 條指令。返回晶片                                                                                              |
| `step(count)`           | 執行 `count` 條處理器指令。這是晶片的時鐘：已啟動的命令只在它執行時推進                                                                                 |
| `finish()`              | 在已啟用的晶片上，若 `0x21` 的位元組設有位 `0x80`，便執行指令直至程式清除該位。返回執行的指令數，無需執行時為 0。超過 `patience` 後拋出 `NeverFinished` |
| `reset()`               | 清除 `enabled`。程式與共享記憶體不受影響。返回晶片                                                                                                      |

| 屬性                 | 含義                                            |
| :------------------- | :---------------------------------------------- |
| `model`, `part`      | 標準型號名稱                                    |
| `processor`          | `upd96050`                                      |
| `identity`           | 所執行映像檔的 `Identity`                       |
| `core`               | 來自 `nec-upd7725-96050-python` 的處理器        |
| `console`            | 處理器各埠的主機一側                            |
| `enabled`            | 自上次重設以來，有寫入落在共享窗口之下時為 True |
| `memory`             | 共享記憶體的 4,096 個位元組，讀取時無副作用     |
| `command`, `execute` | `0x20` 與 `0x21` 的暫存器位元組                 |
| `patience`, `boot`   | 傳入的值                                        |

```python
from snesst import Chip, NeverFinished
from snesst.firmware import Identity

blank = Identity("st010", "upd96050", "blank", program_words=16384, data_words=2048)
part = Chip("st010", image=bytes(53248), identity=blank, boot=0, patience=1000)

part.write(0x680005, 0x7F)
part.write(0x680020, 0x02)
print(hex(part.read(0x680005)), part.memory[5], part.command, part.enabled)

part.write(0x600000, 0x00)
part.write(0x680021, 0x80)
try:
    part.finish()
except NeverFinished as refused:
    print(refused)

print(part.reset().enabled, repr(part))
```

```
0x7f 127 2 False
st010 did not finish command 0x02 within 1000 instructions
False <Chip st010 on upd96050>
```

全零的程式不需要映像檔，因此只要簽出了子模組，任何簽出都能執行此例子。晶片啟用之前，共享記憶體與暫存器已可接受寫入。寫入 `0x600000` 啟用晶片後，`finish()` 執行程式，而程式永不清除啟動位，於是在 1,000 條指令後放棄。

### ST018

`Chip("st018", image=None, images=None, fill=0, processor=None)` 列出每個選項及其預設值。`image` 為 163,840 個位元組，其中程式 131,072 個、數據 32,768 個，且不會先經識別。`images` 是一個由身份與路徑配對組成的可迭代物件，用於取代本機目錄進行搜尋。`processor` 指定子模組以外的另一份 `arm6-python` 簽出。

| 呼叫                                   | 作用                                                                                                                                                                                                                            |
| :------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `read(0x3800)`                         | ARM 送出的位元組，只能讀取一次。清除等待旗標，沒有位元組等待時讀到 0                                                                                                                                                            |
| `write(0x3802, value)`                 | 給 ARM 的一個位元組。設定已送出旗標                                                                                                                                                                                             |
| `read(0x3802)`                         | 讀到 0 並清除訊號旗標，即卡帶輪詢位元 2 之後所做的讀取                                                                                                                                                                          |
| `read(0x3804)`                         | 狀態位元組：`0x01` 表示有位元組等待主機，`0x04` 表示 ARM 已發出訊號，`0x08` 表示有位元組等待 ARM，`0x80` 表示晶片已啟動                                                                                                         |
| `write(0x3804, value)`                 | 設定了位 0 時重設晶片                                                                                                                                                                                                           |
| `status()`                             | 狀態位元組，讀取方式相同                                                                                                                                                                                                        |
| `port(offset)`, `drive(offset, value)` | 信箱的 ARM 一側：讀取偏移 `0x10` 取得主機的位元組，讀取 `0x20` 取得狀態，驅動 `0x00` 向主機送出一個位元組，驅動 `0x10` 發出訊號，驅動 `0x20`、`0x24` 及 `0x28` 設定 `latch` 的三個位元組，驅動 `0x2C` 把 `latch` 複製到 `timer` |
| `step(count=1)`                        | 執行 `count` 條 ARM 指令。返回晶片                                                                                                                                                                                              |
| `run_for(cycles)`                      | 執行完整的 ARM 指令，直至最少經過 `cycles` 個匯流排週期。返回實際花費的週期數，可能超出                                                                                                                                         |
| `reset()`                              | 清空信箱及計時器、將晶片設為已啟動並重設 ARM。返回晶片                                                                                                                                                                          |

| 屬性                                                      | 含義                                                                                                                |
| :-------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------ |
| `model`, `part`                                           | `st018`                                                                                                             |
| `processor`                                               | `arm60`                                                                                                             |
| `identity`                                                | 找到的映像檔的 `Identity`；傳入 `image` 時為 `None`                                                                 |
| `core`                                                    | 執行程式的 `arm6.Cpu`                                                                                               |
| `stores`                                                  | ARM 的位址空間：程式位於 `0x00000000`，埠位於 `0x40000000`，數據位於 `0xA0000000`，16 KB 工作 RAM 位於 `0xE0000000` |
| `incoming`, `outgoing`, `sent`, `signal`, `waiting`, `up` | 狀態位元組背後的信箱狀態                                                                                            |
| `latch`, `timer`                                          | 24 位元計時器：正在載入的值，以及每個 ARM 週期減一、到 0 停止的計數                                                 |
| `steps`                                                   | 自晶片建構以來執行的 ARM 指令數。重設不會改變它                                                                     |
| `cycles`                                                  | 自晶片建構以來 ARM 花費的匯流排週期數。重設會加上其所花費的週期                                                     |
| `tally`                                                   | 以 ARM60 數據表自身的分類表示的同一批週期：順序、非順序、內部及協處理器                                             |

```python
from snesst import Chip, UnknownPort

part = Chip("setast018", image=bytes(163840))
print(type(part).__name__, part.model, part.processor, hex(part.status()))

part.write(0x3802, 0x2A)
print(hex(part.read(0x3804)), hex(part.port(0x10)), hex(part.read(0x3804)))

part.drive(0x00, 0x99)
print(hex(part.read(0x3804)), hex(part.read(0x3800)), hex(part.read(0x3804)))
print(part.step(100).steps)

try:
    part.read(0x3806)
except UnknownPort as refused:
    print(str(refused).split(".")[0])
```

```
ST018 st018 arm60 0x80
0x88 0x2a 0x80
0x81 0x99 0x80
100
nothing establishes what a read of $3806 does
```

全零的映像檔會建構出一個執行零的 ARM，因此無需真正的程式也能驅動信箱。主機的位元組會令位 `0x08` 升起，直到 ARM 取走為止；ARM 的位元組會令位 `0x01` 升起，直到主機取走為止。

### 命令列工具

每個工具都從儲存庫根目錄執行。

| 命令                                        | 參數                                           | 結束碼                                                                                             |
| :------------------------------------------ | :--------------------------------------------- | :------------------------------------------------------------------------------------------------- |
| `python3 snesst/doctor.py`                  | 無                                             | 所有檢查通過時為 0，任何一項失敗時為 1                                                             |
| `python3 -m conformance.speed`              | 無                                             | 每秒 150,000 條 uPD96050 指令或以上，或此處無法建構任何晶片時為 0。低於該值時為 1                  |
| `python3 -m conformance.against_cartridges` | 一款晶片，預設為 `st010`                       | 至少一次記錄的交換取回一個位元組時為 0，全部都沒有時為 1，此處無法建構任何晶片時為 2               |
| `python3 -m conformance.record`             | 一個卡帶目錄，然後一個輸出目錄                 | 找到的每款晶片都產生形態時為 0，有一款沒有產生時為 1，缺少參數、缺少目錄或沒有卡帶帶有晶片時為 2   |
| `python3 -m conformance.links`              | 無                                             | 為 0，除非本 README 中有位址回應 404 或 410                                                        |
| `python3 -m conformance.package`            | 一個已建構的 wheel                             | 每個模組都在其中且不含任何測試時為 0，否則或檔案不存在時為 1，沒有參數時為 2                       |
| `python3 -m conformance.testroms`           | 程式傾印所在的資料夾，加 `--record` 則重寫判定 | 找到的每個傾印都與記錄的判定一致時為 0，有一個不一致時為 1，沒有資料夾或其中沒有記錄過的傾印時為 2 |

`conformance.against_cartridges` 把 [`conformance/st010shapes.json`](conformance/st010shapes.json) 與 [`conformance/st011shapes.json`](conformance/st011shapes.json) 中的交換向晶片重播。`conformance.record` 負責寫出這些檔案：它經由 `snes-driver-python` 讀取每張卡帶自身的程式碼，保留每次交換的形態，但從不保留卡帶的任何位元組。它只接受該子模組清單中列名的卡帶，並檢查其全部四個摘要。

這些檔案中的每個寬度都帶有標籤。像 `write2` 這樣不帶標記的寬度，是卡帶程式碼在存取之前設定的寬度；`*` 表示映像檔的一次執行所用的寬度，`~` 表示無介面 MAME 追蹤在該指令處看到匯流排搬運的寬度，`?` 表示沒有任何東西確定的寬度。`?` 按一個位元組播放，執行會說明所播放的存取中有多少依賴這個假設。[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) 按晶片統計了它們。

## 問題

ST010 與 ST011 沒有自己的埠。每款都與主機共享四 KB 記憶體。命令從該記憶體的固定位址讀取參數，並把答案寫到其中其他固定位址。

兩款內部都是一顆 NEC uPD96050，程式以遮罩方式寫入其 ROM。命令計算的內容就是該程式。程式所用的表格與教科書公式相差在一兩個單位以內，卻沒有一個完全吻合，因此把它們改寫成公式會在每個項目中留下誤差，而攜帶這些表格就等於攜帶晶片的內容。

## 解決方法

套件執行該程式。沒有任何東西是推導出來的，晶片的內容也一概不在儲存庫中。ST011 與 ST018 下將棋，執行程式涵蓋它們的方式，與涵蓋 ST010 的八個命令相同。

沒有映像檔時，晶片拒絕建構。它從不退而使用並非來自晶片的答案。

## 你提供的微碼

每個映像檔在執行任何一個位元組之前都會先經識別。由 SHA-256 決定。CRC32 用於與以它為鍵的目錄交叉核對。

| 晶片    | 位元組數 | CRC32      | SHA-256                                                            |
| :------ | -------: | :--------- | :----------------------------------------------------------------- |
| `st010` |   53,248 | `8d136190` | `55c697e864562445621cdf8a7bf6e84ae91361e393d382a3704e9aa55559041e` |
| `st011` |   53,248 | `750c6012` | `651b82a1e26c4fa8dd549e91e7f923012ed2ca54c1d9fd858655ab30679c2f0e` |
| `st018` |  163,840 | `5c403cc5` | `6df209ab5d2524d1839c038be400ae5eb20dafc14a3771a3239cd9e8acd53806` |

[`snesst/artifacts.manifest.json`](snesst/artifacts.manifest.json) 載有這些數值，並附有 MD5 與 SHA-1。搜尋讀取以 `.bin` 或 `.rom` 結尾的檔案，按以下次序進行，每款晶片以最先找到的映像檔為準：

1. `SNES_ST_FIRMWARE_DIR` 指定的每個目錄，以作業系統分隔路徑的方式分隔。
2. `UPD7725_FIRMWARE_DIR` 指定的每個目錄。
3. 本專案所簽出於其中的專案內的 `firmware/`。
4. 本儲存庫中的 `firmware/`。

不會下載任何東西。在 macOS、Linux 或 Windows 上確認你持有的副本：

```bash
shasum -a 256 firmware/st0010.bin
sha256sum firmware/st0010.bin
certutil -hashfile firmware\st0010.bin SHA256
```

摘要不在清單中的檔案會被搜尋略過。傳給 `snesst.firmware.identify` 時，它會被拒絕，拒絕訊息會說明移除 512 位元組標頭、刪去最後 512 個位元組或交換位元組對，能否把它變成已知映像檔。

把每個程式字和每個表字以低位元組在前儲存的傾印亦會被接受，這是流傳較廣的 ST010 和 ST011 檔案的排列方式。把這兩個檔案中每個 3 位元組程式字和每個 2 位元組表字的位元組反轉，得到的正好是上表中的摘要，因此搜尋以這種反轉識別這樣的檔案，在其 `Identity` 上標記 `low_byte_first`，晶片執行的是反轉後的位元組。診斷腳本報告它執行的位元組的摘要，並說明檔案是以另一種次序儲存的。ST018 檔案沒有需要反轉的字，按原樣即可配對。

## 沒有文件記載的握手

共享記憶體之下的窗口是處理器的數據埠，而共享記憶體就是處理器自身的數據 RAM。微碼在第一條指令就升起其注意位，並等待主機從數據埠取走一個字。在此之前，它永遠不會到達監察命令的迴圈，未經握手便與之通訊的晶片不會作出任何回應。

`Chip` 在建構晶片時執行此握手：一條指令、兩次讀取數據埠，然後 200,000 條指令。之後每個程式各自在不同位置等待。

| 晶片  | 其程式等待的位置                                   |
| :---- | :------------------------------------------------- |
| ST010 | 字 3、4 與 5，測試存放命令與啟動位元組的字的最高位 |
| ST011 | 字 2                                               |

```python
from snesst import Chip

for name in ("st010", "st011"):
    part = Chip(name)
    print(part.model, part.processor, part.core.registers.pc)
```

```
st010 upd96050 3
st011 upd96050 2
```

此例子需要兩個映像檔。

## 它是否正確

[`conformance/hardware.json`](conformance/hardware.json) 記錄套件就介面所斷言的每個值，每個都標記為未驗證，並附有其證據及可以確定它的量度：4,096 位元組的共享窗口、啟用位 `0x80000`、`0x20` 與 `0x21` 的暫存器位元組、握手的兩次讀取、兩處等待位置，以及重設的作用。[`conformance/hardware.test.py`](conformance/hardware.test.py) 驅動一款以全零程式建立的晶片，核對窗口、啟用位、暫存器及握手；兩處等待位置由 [`snesst/microcode.test.py`](snesst/microcode.test.py) 在真實映像上核對。

| 層次       | 檢查內容                                                                                                                                                | 需要映像檔 |
| :--------- | :------------------------------------------------------------------------------------------------------------------------------------------------------ | :--------: |
| 處理器     | 每條指令，見 [nec-upd7725-96050-python](https://github.com/gufranco/nec-upd7725-96050-python) 與 [arm6-python](https://github.com/gufranco/arm6-python) |     否     |
| 解碼       | 啟用寫入、兩個暫存器位元組、共享窗口，在全零的程式上                                                                                                    |     否     |
| ST018 信箱 | 其三個埠、狀態位及拒絕情況，在測試中編寫的簡短 ARM 程式上                                                                                               |     否     |
| 身份       | 每個映像檔以決定性摘要命名，以及錯誤檔案所得到的每種拒絕                                                                                                |     否     |
| 目錄       | 全部三款晶片及其接受的每個名稱                                                                                                                          |     否     |
| 晶片       | ST010 與 ST011 各自到達自己的等待位置並在該處停留 4,096 條指令，且 ST010 回應一個命令                                                                   |     是     |

[`snesst/microcode.test.py`](snesst/microcode.test.py) 負責最後一行，沒有映像檔時報告為已略過。另一個獨立的 CI 作業會啟動每款晶片，為 ST010 與 ST011 執行 `conformance.against_cartridges`，並在執行頁面上說明是否有晶片真正被驅動。

[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) 列出未知的事項，以及可以解決每一項的量度。[`conformance/divergences.json`](conformance/divergences.json) 記錄各來源之間的分歧，以及本套件採用哪一個。

## 參與開發

| 需要                                 | 位置                                                               |
| :----------------------------------- | :----------------------------------------------------------------- |
| 每項關卡檢查及其執行次序             | [CONTRIBUTING.md](CONTRIBUTING.md)                                 |
| 供編程代理使用的相同資料             | [AGENTS.md](AGENTS.md)                                             |
| 本儲存庫與同系列其他儲存庫共用的標準 | [FAMILY.md](FAMILY.md)                                             |
| 錯誤報告                             | [GitHub Issues](https://github.com/gufranco/snes-st-python/issues) |
| 安全報告                             | [SECURITY.md](SECURITY.md)                                         |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 --with types-setuptools==84.0.0.20260812 mypy==1.14.1
pnpm install --frozen-lockfile && pnpm run format:check
cov=(uvx --python 3.12 --from coverage==7.6.10 --with setuptools==84.0.0 coverage)
"${cov[@]}" erase
for file in $(find snesst conformance -name '*.test.py' | sort); do "${cov[@]}" run -a "$file"; done
"${cov[@]}" report
python3 -m conformance.speed
```

每個模組旁邊都有一個以其命名的測試檔案，每個都可單獨執行，例如 `python3 snesst/chip.test.py`。覆蓋率是一項硬性關卡檢查，要求 100% 語句與分支覆蓋，設定於 [pyproject.toml](pyproject.toml)。吞吐量下限在覆蓋率步驟之外執行。

## 參考資料

- Seta 從未公佈任何有關這些晶片的資料。[`conformance/hardware.json`](conformance/hardware.json) 中權威等級的最高一級是空的，記錄中亦如此註明。
- 讀者提供的微碼，用於套件給出的每個答案。它在執行前經摘要確認，並不在本儲存庫中。
- [nec-upd7725-96050-python](https://github.com/gufranco/nec-upd7725-96050-python)，用於 uPD96050 及 NEC 就其印行的每項事實。
- [arm6-python](https://github.com/gufranco/arm6-python)，用於 ST018 內部的 ARM60。
- [snes-driver-python](https://github.com/gufranco/snes-driver-python)，用於讀取卡帶自身的程式碼，以找出它向協處理器發出甚麼。
- 模擬器中的行為模型，用於介面常數：共享記憶體位於何處，以及哪些位址是暫存器。

## 引用本專案

[CITATION.cff](CITATION.cff) 在每次版本發佈時，由寫入套件版本的腳本更新。

## 授權

MIT。見 [LICENSE](LICENSE)。
