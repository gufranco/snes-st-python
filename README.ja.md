# Seta ST010、ST011、ST018

SetaがSuper Nintendoのカートリッジ向けに作った3つのコプロセッサをPythonで実装したものです。それぞれ読者が用意したマイクロコードを実行し、そのマイクロコードがコマンドを待つために止まる場所に合わせて検証されています。

[English](README.md) &nbsp;|&nbsp; 日本語 &nbsp;|&nbsp; [简体中文](README.zh-Hans.md) &nbsp;|&nbsp; [繁體中文（香港）](README.zh-HK.md)

[![CI](https://github.com/gufranco/snes-st-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/snes-st-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/snes-st-python)](https://github.com/gufranco/snes-st-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**3**個のパーツ、手で記述したコマンドは**0**個、2つの待機位置はどちらも出荷時のマイクロコードで測定済み、それらの待機位置と記録との食い違いは**0**件、テストは**672**個、ステートメントとブランチの**100%**カバレッジ、依存関係なし

```python
from snesst import Chip

part = Chip("st010")

part.write(0x000000, 0x00)
for at, value in enumerate((0x00, 0x01, 0x00, 0x02)):
    part.write(0x680000 + at, value)
part.write(0x680020, 0x01)
part.write(0x680021, 0x80)

print(hex(part.read(0x680010) | part.read(0x680011) << 8))
```

```
0x9300
```

`0x000000`への書き込みは共有ウィンドウより下、プロセッサのデータポートに届き、パーツがスタートバイトに反応できるようにします。続く4バイトは点`0x0100, 0x0200`を共有メモリの先頭に置きます。コマンド`0x01`は`0x20`のレジスタバイトに、スタートビットは`0x21`のレジスタバイトに入り、ST010自身のプログラムがそのビットをクリアするまで実行されます。答えは同じメモリの`0x10`から返ります。この例にはST010のイメージが必要です。イメージがないと、`Chip("st010")`は`NoFirmware`を送出します。

## インストール

| 要件 | バージョン |
|:--|:--|
| Python | 3.12以降 |
| git | 任意。サブモジュールの取得に使います |
| ファームウェアのイメージ | 作るパーツごとに1つ。自分が所有するハードウェアからダンプしたもの |

```bash
git clone --recurse-submodules https://github.com/gufranco/snes-st-python.git
cd snes-st-python
python3 snesst/doctor.py
```

パッケージは標準ライブラリ以外を何もインポートしません。リポジトリのルートには3つのサブモジュールがあります。`nec-upd7725-96050-python`はST010とST011の内部のプロセッサ、`arm6-python`はST018の内部のプロセッサです。`snes-driver-python`はカートリッジとのやり取りを記録するツールだけが読みます。download-zipリンクから得たソースアーカイブにはサブモジュールが含まれず、その場合どのパーツも構築を拒否します。

ドクターはマシン、サブモジュール、各パーツのイメージを確認し、最後に1行を出力します。バグ報告には出力全体を貼り付けてください。チェックアウトしたばかりの状態にはイメージがないため、3つのパーツの行が失敗します。

```
  3 of 12 checks did not pass
```

リリースは[Semantic Versioning](https://semver.org/)に従い、semantic-releaseがコミット履歴から作成します。すべてのリリースにはタグが付き、[リリースページ](https://github.com/gufranco/snes-st-python/releases)に掲載されます。

## インターフェース

`snesst.Chip(model, **options)`は1つのパーツを構築します。`model`は必須で、大文字小文字、ハイフン、アンダースコアの違いを無視して照合されます。ST010とST011は`snesst.chip.Chip`として返り、NEC uPD96050を実行します。ST018は`snesst.ST018`として返り、ARM60を実行します。

| モデル | 別名 | プロセッサ | イメージのバイト数 | プログラムの役割 |
|:--|:--|:--|--:|:--|
| `st010` | `st-010`, `seta010`, `setast010` | uPD96050 | 53,248 | レースゲームのカートリッジ向けの8つのコマンド |
| `st011` | `st-011`, `seta011`, `setast011` | uPD96050 | 53,248 | 将棋を指します |
| `st018` | `st-018`, `seta018`, `setast018` | ARM60 | 163,840 | 1バイトのメールボックスを通して将棋を指します |

### カタログとエラー

| 名前 | 内容 |
|:--|:--|
| `snesst.MODELS` | 3つの`Model`レコード。正式名をキーとします |
| `snesst.Model` | `name`、`aliases`、`summary`、そして実行するイメージの名前である`image` |
| `snesst.available()` | このマシンにイメージがあるすべてのパーツの辞書。それぞれが識別情報とパスを持ちます。uPD96050のサブモジュールがない場合は空です |
| `snesst.why_not()` | uPD96050のサブモジュールかすべてのイメージがないために、ここではどのパーツも構築できない理由を述べる文。それ以外の場合は`None` |
| `snesst.ST018` | ARMパーツのクラス。直接構築する呼び出し側向けです |
| `snesst.__version__` | インストールされているバージョン |

| エラー | 送出される条件 |
|:--|:--|
| `UnknownModelError` | モデルが指定されていないか、その名前のパーツがありません。メッセージには受け付ける名前が列挙されます |
| `NoFirmware` | プロセッサのサブモジュールがチェックアウトされていない、パーツのイメージが見つからない、またはuPD96050のパーツに`identity`なしでイメージが渡されました |
| `NeverFinished` | 開始したコマンドが`patience`命令以内にスタートビットをクリアしませんでした |
| `WrongShape` | イメージの長さがそのプロセッサの受け付ける長さではありません |
| `Unrecognised` | `snesst.firmware.identify`が、マニフェストにSHA-256がないバイト列に出会いました。ディレクトリ探索では、そのようなファイルは代わりにスキップされます |
| `Corrupt` | イメージがSHA-256ではマニフェストのエントリと一致し、別のダイジェストでは食い違います |
| `UnknownPort` | ST018の読み書きが3つのポート以外のアドレスに当たりました |

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

### ST010とST011

`Chip("st011", memory=None, fill=0, patience=4000000, boot=200000, image=None, identity=None, images=None)`は、すべてのオプションとそのデフォルト値を示しています。

| オプション | 効果 |
|:--|:--|
| `memory` | ハンドシェイクの後に共有メモリへコピーされるバイト列。最大4,096バイトです |
| `fill` | 電源投入時にプロセッサのレジスタとメモリが持つ値 |
| `patience` | 開始したコマンドが`NeverFinished`になるまでに実行できる命令数 |
| `boot` | ハンドシェイクの2回の読み出しの後、パーツを返す前に実行する命令数 |
| `image` | イメージのバイト列。ディレクトリは探索されず、変数も読まれません |
| `identity` | `image`が何であるかを示す`snesst.firmware.Identity`。`image`と一緒に指定する必要があります |
| `images` | `available()`と同じ形のカタログ。このマシンのカタログの代わりに探索されます |

| 呼び出し | 効果 |
|:--|:--|
| `read(address)` | ビット`0x80000`が立っている場合は、`address & 0xFFF`にある共有メモリのバイト。それ以外はデータポート、奇数アドレスではステータスポート |
| `write(address, value)` | ビット`0x80000`が立っている場合は共有メモリのバイトを書き、パーツが有効で`0x21`のバイトのビット`0x80`が立っていればプログラムを実行します。それ以外はパーツを有効にする書き込みで、偶数アドレスではデータポートに渡されます |
| `handshake(boot=None)` | 1命令、データポートの2回の読み出し、続いて`boot`命令。パーツを返します |
| `step(count)` | `count`個のプロセッサ命令 |
| `reset()` | `enabled`をクリアします。プログラムと共有メモリはそのままです。パーツを返します |

| 属性 | 意味 |
|:--|:--|
| `model`, `part` | 正式なモデル名 |
| `processor` | `upd96050` |
| `identity` | 実行されるイメージの`Identity` |
| `core` | `nec-upd7725-96050-python`のプロセッサ |
| `console` | プロセッサのポートのホスト側 |
| `enabled` | 最後のリセット以降に共有ウィンドウより下への書き込みがあればTrue |
| `memory` | 共有メモリの4,096バイト。副作用なしで読み出されます |
| `command`, `execute` | `0x20`と`0x21`のレジスタバイト |
| `patience`, `boot` | 渡された値 |

```python
from snesst import Chip, NeverFinished
from snesst.firmware import Identity

blank = Identity("st010", "upd96050", "blank", program_words=16384, data_words=2048)
part = Chip("st010", image=bytes(53248), identity=blank, boot=0, patience=1000)

part.write(0x680005, 0x7F)
part.write(0x680020, 0x02)
print(hex(part.read(0x680005)), part.memory[5], part.command, part.enabled)

part.write(0x600000, 0x00)
try:
    part.write(0x680021, 0x80)
except NeverFinished as refused:
    print(refused)

print(part.reset().enabled, repr(part))
```

```
0x7f 127 2 False
st010 did not finish command 0x02 within 1000 instructions
False <Chip st010 on upd96050>
```

ゼロだけのプログラムにはイメージが不要なので、この例はサブモジュールのあるどのチェックアウトでも動きます。共有メモリとレジスタは、パーツが有効になる前から書き込みを受け付けます。`0x600000`への書き込みでパーツが有効になると、スタートビットがプログラムを実行します。プログラムはそのビットをクリアしないので、パーツは1,000命令の後に諦めます。

### ST018

`Chip("st018", image=None, images=None, fill=0, processor=None)`は、すべてのオプションとそのデフォルト値を示しています。`image`は163,840バイトで、プログラムが131,072バイト、データが32,768バイトです。事前の識別は行われません。`images`は識別情報とパスの組のイテラブルで、このマシンのディレクトリの代わりに探索されます。`processor`はサブモジュール以外の`arm6-python`のチェックアウトを指定します。

| 呼び出し | 効果 |
|:--|:--|
| `read(0x3800)` | ARMが送ったバイトを一度だけ返します。待機フラグをクリアし、何も待っていなければ0を返します |
| `write(0x3802, value)` | ARM宛てのバイト。送信フラグを立てます |
| `read(0x3804)` | ステータスバイト。`0x01`はコンソール宛てのバイトが待っていること、`0x08`はARM宛てのバイトが待っていること、`0x80`はパーツが起動していることを示します |
| `write(0x3804, value)` | ビット0が立っていればパーツをリセットします |
| `status()` | ステータスバイト。同じ方法で読み出します |
| `port(offset)`, `drive(offset, value)` | メールボックスのARM側。オフセット`0x10`の読み出しはコンソールのバイトを受け取り、`0x20`の読み出しはステータスを返し、`0x00`への書き込みはコンソールにバイトを送り、`0x20`への書き込みは`timer`を設定します |
| `step(count=1)` | `count`個のARM命令。パーツを返します |
| `reset()` | メールボックスを空にし、パーツを起動状態にしてARMをリセットします。パーツを返します |

| 属性 | 意味 |
|:--|:--|
| `model`, `part` | `st018` |
| `processor` | `arm60` |
| `identity` | 見つかったイメージの`Identity`。`image`が渡された場合は`None` |
| `core` | プログラムを実行する`arm6.Cpu` |
| `stores` | ARMのアドレス空間。プログラムは`0x00000000`、ポートは`0x40000000`、データは`0xA0000000`、16 KBのワークRAMは`0xE0000000`にあります |
| `incoming`, `outgoing`, `sent`, `waiting`, `up`, `timer` | ステータスバイトの背後にあるメールボックスの状態 |
| `steps` | パーツの構築以降に実行したARM命令数。リセットしても変わりません |

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

ゼロで埋めたイメージからはゼロを実行するARMが構築されるので、本物のプログラムなしでメールボックスを動かせます。コンソールのバイトはARMが受け取るまでビット`0x08`を立て、ARMのバイトはコンソールが受け取るまでビット`0x01`を立てます。

### コマンドラインツール

どれもリポジトリのルートから実行します。

| コマンド | 引数 | 終了コード |
|:--|:--|:--|
| `python3 snesst/doctor.py` | なし | すべてのチェックが通れば0、どれかが失敗すれば1 |
| `python3 -m conformance.speed` | なし | 毎秒150,000 uPD96050命令以上、またはここでどのパーツも構築できない場合は0。それを下回れば1 |
| `python3 -m conformance.against_cartridges` | パーツ。デフォルトは`st010` | 記録されたやり取りの少なくとも1つでバイトが返れば0、1つも返らなければ1、ここでどのパーツも構築できなければ2 |
| `python3 -m conformance.record` | カートリッジのディレクトリ、続いて出力ディレクトリ | 見つかったすべてのパーツが形を出せば0、1つでも出せなければ1、引数がない、ディレクトリがない、またはパーツを載せたカートリッジがない場合は2 |
| `python3 -m conformance.links` | なし | このREADMEのアドレスが404か410を返さない限り0 |
| `python3 -m conformance.package` | ビルド済みのwheel | すべてのモジュールが含まれ、テストが1つも含まれていなければ0、それ以外やファイルがない場合は1、引数がなければ2 |

`conformance.against_cartridges`は、[`conformance/st010shapes.json`](conformance/st010shapes.json)と[`conformance/st011shapes.json`](conformance/st011shapes.json)にあるやり取りをパーツに対して再生します。`conformance.record`はそれらのファイルを書き出します。`snes-driver-python`を通して各カートリッジ自身のコードを読み、すべてのやり取りの形だけを残し、カートリッジのバイトは1つも残しません。そのサブモジュールのマニフェストに名前のあるカートリッジだけを受け付け、その4つのダイジェストをすべて確認します。

## 問題

ST010とST011には独自のポートがありません。どちらもコンソールと4キロバイトのメモリを共有しています。コマンドはそのメモリの固定アドレスから引数を読み、同じメモリの別の固定アドレスに答えを書きます。

内部はどちらもNEC uPD96050で、ROMにプログラムがマスクされています。コマンドが何を計算するかは、そのプログラムそのものです。プログラムが使う表は教科書の式と1、2単位以内で一致しますが、どれとも完全には一致しません。そのため式として書き直すとすべてのエントリに誤差が残り、表を持ち込めばチップの中身を持ち込むことになります。

## 解決策

このパッケージはプログラムを実行します。何も導出せず、チップの中身はリポジトリに一切含まれていません。ST011とST018は将棋を指しますが、プログラムを実行することで、ST010の8つのコマンドと同じようにそれらにも対応できます。

イメージがなければ、パーツは構築を拒否します。パーツから得たものではない答えに頼ることはありません。

## 用意するマイクロコード

すべてのイメージは、1バイトでも実行される前に識別されます。判定はSHA-256で行います。CRC32は、それをキーにするカタログと照合するためにあります。

| パーツ | バイト数 | CRC32 | SHA-256 |
|:--|--:|:--|:--|
| `st010` | 53,248 | `8d136190` | `55c697e864562445621cdf8a7bf6e84ae91361e393d382a3704e9aa55559041e` |
| `st011` | 53,248 | `750c6012` | `651b82a1e26c4fa8dd549e91e7f923012ed2ca54c1d9fd858655ab30679c2f0e` |
| `st018` | 163,840 | `5c403cc5` | `6df209ab5d2524d1839c038be400ae5eb20dafc14a3771a3239cd9e8acd53806` |

[`snesst/artifacts.manifest.json`](snesst/artifacts.manifest.json)は、これらをMD5とSHA-1と併せて保持しています。探索は`.bin`か`.rom`で終わるファイルを次の順で読み、パーツごとに最初に見つかったイメージが採用されます。

1. `SNES_ST_FIRMWARE_DIR`で指定されたすべてのディレクトリ。区切り方はオペレーティングシステムのパスの区切り方に従います。
2. `UPD7725_FIRMWARE_DIR`で指定されたすべてのディレクトリ。
3. このリポジトリがチェックアウトされている親プロジェクトの`firmware/`。
4. このリポジトリの`firmware/`。

何もダウンロードしません。手元のコピーはmacOS、Linux、Windowsで次のように確認します。

```bash
shasum -a 256 firmware/st0010.bin
sha256sum firmware/st0010.bin
certutil -hashfile firmware\st0010.bin SHA256
```

ダイジェストがマニフェストにないファイルは、探索ではスキップされます。`snesst.firmware.identify`に渡すと拒否され、その拒否メッセージは、512バイトのヘッダを取り除く、末尾の512バイトを削る、またはバイトの組を入れ替えることで既知のイメージになるかどうかを示します。

## どこにも記載のないハンドシェイク

共有メモリより下のウィンドウはプロセッサのデータポートで、共有メモリはプロセッサ自身のデータRAMです。マイクロコードは最初の命令で注意ビットを立て、コンソールがデータポートから1ワードを取り出すのを待ちます。それが起きるまで、コマンドを監視するループには到達しません。これを行わずに話しかけたパーツは何も答えません。

`Chip`はパーツを構築する際にこのハンドシェイクを行います。1命令、データポートの2回の読み出し、続いて200,000命令です。その後、各プログラムはそれぞれ固有の場所で待機します。

| パーツ | プログラムが待機する場所 |
|:--|:--|
| ST010 | ワード3、4、5。コマンドとスタートバイトを保持するワードの最上位ビットを調べています |
| ST011 | ワード2 |

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

この例には両方のイメージが必要です。

## 正しいのか

[`conformance/hardware.json`](conformance/hardware.json)は、パッケージがインターフェースについて主張するすべての値を記録しています。どれも未検証と記され、その根拠と、決着をつける測定が添えられています。4,096バイトの共有ウィンドウ、有効化ビット`0x80000`、`0x20`と`0x21`のレジスタバイト、ハンドシェイクの2回の読み出し、2つの待機位置、そしてリセットが何をするかです。[`conformance/hardware.test.py`](conformance/hardware.test.py)は、それぞれをコード内の定数と照合します。

| 層 | 確認する内容 | イメージが必要か |
|:--|:--|:--:|
| プロセッサ | すべての命令。[nec-upd7725-96050-python](https://github.com/gufranco/nec-upd7725-96050-python)と[arm6-python](https://github.com/gufranco/arm6-python)で確認します | いいえ |
| デコード | 有効化の書き込み、2つのレジスタバイト、共有ウィンドウ。ゼロだけのプログラムで確認します | いいえ |
| ST018のメールボックス | 3つのポート、ステータスビット、拒否。テスト内に書いた短いARMプログラムで確認します | いいえ |
| 識別 | 決め手となるダイジェストで名前が決まる各イメージと、誤ったファイルが受けるすべての拒否 | いいえ |
| カタログ | 3つのパーツすべてと、それらが応じるすべての名前 | いいえ |
| パーツ | ST010とST011がそれぞれ固有の待機位置に到達して4,096命令の間そこに留まること、そしてST010がコマンドに答えること | はい |

[`snesst/microcode.test.py`](snesst/microcode.test.py)が最後の行を担当し、イメージがなければスキップとして報告します。別のCIジョブがすべてのパーツを起動し、ST010とST011に対して`conformance.against_cartridges`を実行し、パーツが実際に駆動されたかどうかを実行ページに表示します。

[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md)は、わかっていないことを、各項目を解決する測定と併せて列挙しています。[`conformance/divergences.json`](conformance/divergences.json)は、情報源の間で食い違う箇所と、このパッケージがどちらに従うかを記録しています。

## 開発に参加する

| 必要なもの | 場所 |
|:--|:--|
| すべてのゲートとその実行順 | [CONTRIBUTING.md](CONTRIBUTING.md) |
| コーディングエージェント向けの同じ内容 | [AGENTS.md](AGENTS.md) |
| このリポジトリがファミリーの他のリポジトリと共有する基準 | [FAMILY.md](FAMILY.md) |
| バグ報告 | [GitHub Issues](https://github.com/gufranco/snes-st-python/issues) |
| セキュリティ報告 | [SECURITY.md](SECURITY.md) |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 mypy==1.14.1
pnpm install --frozen-lockfile && pnpm run format:check
python3 -m coverage erase
for file in $(find snesst conformance -name '*.test.py' | sort); do python3 -m coverage run -a "$file"; done
python3 -m coverage report
python3 -m conformance.speed
```

各モジュールの隣には、その名前を付けたテストファイルがあり、`python3 snesst/chip.test.py`のようにそれぞれ単独で実行できます。カバレッジはステートメントとブランチで100%の厳格なゲートで、[pyproject.toml](pyproject.toml)で設定されています。スループットの下限はカバレッジのステップとは別に実行します。

## 参考資料

- Setaはこれらのパーツについて何も公開していません。[`conformance/hardware.json`](conformance/hardware.json)の権威の序列の最上段は空で、記録にもそう書かれています。
- 読者が用意するマイクロコード。パッケージが返すすべての答えの源です。実行前にダイジェストで確認され、このリポジトリには含まれていません。
- [nec-upd7725-96050-python](https://github.com/gufranco/nec-upd7725-96050-python)。uPD96050と、NECがそれについて印刷したすべての事実のために。
- [arm6-python](https://github.com/gufranco/arm6-python)。ST018の内部のARM60のために。
- [snes-driver-python](https://github.com/gufranco/snes-driver-python)。カートリッジ自身のコードを読み、コプロセッサに何を伝えているかを調べるために。
- エミュレータの動作モデル。インターフェースの定数、つまり共有メモリの位置とどのアドレスがレジスタかのために。

## 引用

[CITATION.cff](CITATION.cff)は、パッケージのバージョンを刻むスクリプトによってリリースごとに更新されます。

## ライセンス

MIT。[LICENSE](LICENSE)を参照してください。
