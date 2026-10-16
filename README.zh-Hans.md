[English](README.md) | [日本語](README.ja.md) | 简体中文 | [繁體中文（香港）](README.zh-HK.md)

# Seta ST010、ST011 和 ST018

Seta 为 Super Nintendo 卡带制造的三款协处理器的 Python 实现，每款都运行读者自行提供的微码，并严格对准该微码停下来等待命令的位置。

[![CI](https://github.com/gufranco/snes-st-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/snes-st-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/snes-st-python)](https://github.com/gufranco/snes-st-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**3** 个部件，**0** 条手工描述的命令，两处等待位置均在出厂微码上测得，这些等待位置与记录之间 **0** 处不一致，**672** 个测试，**100%** 语句和分支覆盖率，无依赖

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

对 `0x000000` 的写入落在共享窗口下方，即处理器的数据端口上，使部件能够响应启动字节。接下来的四个字节把点 `0x0100, 0x0200` 放在共享内存的底部。命令 `0x01` 写入 `0x20` 处的寄存器字节，启动位写入 `0x21` 处的寄存器字节，随后 ST010 自身的程序一直运行，直到清除该位。答案从同一块内存的 `0x10` 处读回。此示例需要 ST010 镜像；没有镜像时，`Chip("st010")` 会抛出 `NoFirmware`。

## 安装

| 要求 | 版本 |
|:--|:--|
| Python | 3.12 或更高 |
| git | 任意版本，用于获取子模块 |
| 固件镜像 | 每个要构建的部件一个，从你拥有的硬件中转储 |

```bash
git clone --recurse-submodules https://github.com/gufranco/snes-st-python.git
cd snes-st-python
python3 snesst/doctor.py
```

本包只导入标准库中的内容。仓库根目录下有三个子模块：`nec-upd7725-96050-python` 是 ST010 和 ST011 内部的处理器，`arm6-python` 是 ST018 内部的处理器，`snes-driver-python` 只由记录卡带交互的工具读取。通过下载 zip 链接得到的源码归档不含子模块，此时每个部件都会拒绝构建。

诊断脚本检查本机、子模块和每个部件的镜像，最后输出一行结论。提交任何缺陷报告时请粘贴其完整输出。全新检出的仓库不含镜像，因此三个部件对应的行会失败：

```
  3 of 12 checks did not pass
```

版本遵循[语义化版本](https://semver.org/)，由 semantic-release 根据提交历史发布。每个版本都打了标签，并列在[发布页面](https://github.com/gufranco/snes-st-python/releases)上。

## 接口

`snesst.Chip(model, **options)` 构建一个部件。`model` 为必填项，匹配时不区分大小写、连字符和下划线。ST010 和 ST011 返回 `snesst.chip.Chip`，运行一颗 NEC uPD96050。ST018 返回 `snesst.ST018`，运行一颗 ARM60。

| 型号 | 别名 | 处理器 | 镜像字节数 | 程序的功能 |
|:--|:--|:--|--:|:--|
| `st010` | `st-010`, `seta010`, `setast010` | uPD96050 | 53,248 | 为一款赛车卡带提供八条命令 |
| `st011` | `st-011`, `seta011`, `setast011` | uPD96050 | 53,248 | 下将棋 |
| `st018` | `st-018`, `seta018`, `setast018` | ARM60 | 163,840 | 通过单字节邮箱下将棋 |

### 目录与错误

| 名称 | 内容 |
|:--|:--|
| `snesst.MODELS` | 三条 `Model` 记录，以规范名称为键 |
| `snesst.Model` | `name`、`aliases`、`summary` 和 `image`，即其运行的镜像的名称 |
| `snesst.available()` | 一个字典，包含镜像存在于本机的每个部件，每项为一个标识和一个路径。缺少 uPD96050 子模块时为空 |
| `snesst.why_not()` | 说明此处为何无法构建任何部件的句子，原因是缺少 uPD96050 子模块或缺少全部镜像。否则为 `None` |
| `snesst.ST018` | ARM 部件的类，供直接构建它的调用者使用 |
| `snesst.__version__` | 已安装的版本 |

| 错误 | 抛出时机 |
|:--|:--|
| `UnknownModelError` | 缺少型号，或没有部件使用该名称。消息中列出可接受的名称 |
| `NoFirmware` | 某个处理器子模块未检出，找不到该部件的镜像，或向 uPD96050 部件传入镜像时未提供 `identity` |
| `NeverFinished` | 已启动的命令在 `patience` 条指令内未清除启动位 |
| `WrongShape` | 镜像长度不是其处理器所需的长度 |
| `Unrecognised` | `snesst.firmware.identify` 遇到 SHA-256 不在清单中的字节。目录搜索则会跳过此类文件 |
| `Corrupt` | 镜像的 SHA-256 与某个清单条目一致，但另一个摘要与之不符 |
| `UnknownPort` | 对 ST018 的读或写落在其三个端口以外的地址上 |

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

### ST010 和 ST011

`Chip("st011", memory=None, fill=0, patience=4000000, boot=200000, image=None, identity=None, images=None)` 列出了每个选项及其默认值。

| 选项 | 作用 |
|:--|:--|
| `memory` | 握手后复制到共享内存中的字节，最多 4,096 个 |
| `fill` | 上电时处理器寄存器和存储器中的值 |
| `patience` | 已启动的命令在抛出 `NeverFinished` 之前可运行的指令数 |
| `boot` | 握手的两次读取之后、部件交还之前运行的指令数 |
| `image` | 镜像字节。不搜索任何目录，也不读取任何变量 |
| `identity` | `image` 是什么，以 `snesst.firmware.Identity` 表示。与 `image` 一起使用时必填 |
| `images` | 形如 `available()` 的目录，代替本机的目录进行搜索 |

| 调用 | 作用 |
|:--|:--|
| `read(address)` | 设置了 `0x80000` 位时，返回 `address & 0xFFF` 处的共享内存字节。否则读取数据端口，奇数地址则读取状态端口 |
| `write(address, value)` | 设置了 `0x80000` 位时，写入一个共享内存字节；若部件已启用且 `0x21` 处的字节含 `0x80` 位，则随后运行程序。否则为一次启用部件的写入，偶数地址时传给数据端口 |
| `handshake(boot=None)` | 一条指令，两次读取数据端口，然后运行 `boot` 条指令。返回部件 |
| `step(count)` | 运行 `count` 条处理器指令 |
| `reset()` | 清除 `enabled`。程序和共享内存保持不变。返回部件 |

| 属性 | 含义 |
|:--|:--|
| `model`, `part` | 规范型号名称 |
| `processor` | `upd96050` |
| `identity` | 所运行镜像的 `Identity` |
| `core` | 来自 `nec-upd7725-96050-python` 的处理器 |
| `console` | 处理器端口的主机一侧 |
| `enabled` | 自上次复位以来收到过一次共享窗口下方的写入后为 True |
| `memory` | 共享内存的 4,096 个字节，读取时无副作用 |
| `command`, `execute` | `0x20` 和 `0x21` 处的寄存器字节 |
| `patience`, `boot` | 传入的值 |

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

全零的程序不需要镜像，因此在任何带有子模块的检出上都能运行。部件启用之前，共享内存和寄存器就能接受写入。对 `0x600000` 的写入启用部件后，启动位使程序运行，而程序永远不会清除该位，于是部件在 1,000 条指令后放弃。

### ST018

`Chip("st018", image=None, images=None, fill=0, processor=None)` 列出了每个选项及其默认值。`image` 为 163,840 字节，其中程序 131,072 字节、数据 32,768 字节，且不会先经过识别。`images` 是由标识和路径组成的二元组的可迭代对象，代替本机的目录进行搜索。`processor` 指定子模块以外的另一个 `arm6-python` 检出。

| 调用 | 作用 |
|:--|:--|
| `read(0x3800)` | ARM 发送的字节，只能读取一次。清除等待标志，没有等待中的字节时读出 0 |
| `write(0x3802, value)` | 发给 ARM 的一个字节。设置已发送标志 |
| `read(0x3804)` | 状态字节：`0x01` 表示有字节等待主机读取，`0x08` 表示有字节等待 ARM 读取，`0x80` 表示部件已就绪 |
| `write(0x3804, value)` | 设置第 0 位时复位部件 |
| `status()` | 状态字节，读取方式相同 |
| `port(offset)`, `drive(offset, value)` | 邮箱的 ARM 一侧：读取偏移 `0x10` 取走主机的字节，读取 `0x20` 给出状态，驱动 `0x00` 向主机发送一个字节，驱动 `0x20` 设置 `timer` |
| `step(count=1)` | 运行 `count` 条 ARM 指令。返回部件 |
| `reset()` | 清空邮箱，将部件置为就绪并复位 ARM。返回部件 |

| 属性 | 含义 |
|:--|:--|
| `model`, `part` | `st018` |
| `processor` | `arm60` |
| `identity` | 所找到镜像的 `Identity`，传入 `image` 时为 `None` |
| `core` | 运行程序的 `arm6.Cpu` |
| `stores` | ARM 的地址空间：程序位于 `0x00000000`，端口位于 `0x40000000`，数据位于 `0xA0000000`，16 KB 工作 RAM 位于 `0xE0000000` |
| `incoming`, `outgoing`, `sent`, `waiting`, `up`, `timer` | 状态字节背后的邮箱状态 |
| `steps` | 自部件构建以来运行的 ARM 指令数。复位不影响它 |

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

全零的镜像构建出一个运行零指令的 ARM，因此无需真实程序即可驱动邮箱。主机的字节会置起 `0x08` 位，直到 ARM 取走它；ARM 的字节会置起 `0x01` 位，直到主机取走它。

### 命令行工具

每个工具都从仓库根目录运行。

| 命令 | 参数 | 退出码 |
|:--|:--|:--|
| `python3 snesst/doctor.py` | 无 | 所有检查通过时为 0，任一失败时为 1 |
| `python3 -m conformance.speed` | 无 | 达到或超过每秒 150,000 条 uPD96050 指令，或此处无法构建任何部件时为 0。低于该值时为 1 |
| `python3 -m conformance.against_cartridges` | 一个部件，默认为 `st010` | 至少一次记录的交互得到返回字节时为 0，没有任何一次得到时为 1，此处无法构建任何部件时为 2 |
| `python3 -m conformance.record` | 一个卡带目录，然后是一个输出目录 | 找到的每个部件都产生形态时为 0，有一个未产生时为 1，缺少参数、缺少目录或没有卡带带有部件时为 2 |
| `python3 -m conformance.links` | 无 | 为 0，除非本 README 中的某个地址返回 404 或 410 |
| `python3 -m conformance.package` | 一个构建好的 wheel | 每个模块都在其中且不含任何测试时为 0，否则或文件不存在时为 1，没有参数时为 2 |

`conformance.against_cartridges` 将 [`conformance/st010shapes.json`](conformance/st010shapes.json) 和 [`conformance/st011shapes.json`](conformance/st011shapes.json) 中的交互回放给部件。`conformance.record` 生成这些文件：它通过 `snes-driver-python` 读取每个卡带自身的代码，保留每次交互的形态，从不保留卡带的任何字节。它只接受该子模块清单中列出的卡带，并检查它们全部四个摘要。

## 问题

ST010 和 ST011 没有自己的端口。每款都与主机共享 4 KB 内存。命令从该内存中的固定地址读取参数，并把答案写到其中的另一些固定地址。

两者内部都是一颗 NEC uPD96050，程序掩膜在其 ROM 中。命令计算什么，取决于这段程序。程序所用的表与教科书公式的误差在一两个单位以内，但没有一个完全吻合，因此把它们重述为公式会使每个条目都带有误差，而携带这些表就意味着携带芯片的内容。

## 解决方案

本包直接运行程序。没有任何推导，仓库中也不含芯片的任何内容。ST011 和 ST018 下将棋，运行程序对它们的覆盖方式与覆盖 ST010 的八条命令相同。

没有镜像时部件拒绝构建。它从不退回到不是来自部件的答案。

## 你提供的微码

每个镜像在其任何字节运行之前都会被识别。以 SHA-256 为准。CRC32 用于与以其为键的目录交叉核对。

| 部件 | 字节数 | CRC32 | SHA-256 |
|:--|--:|:--|:--|
| `st010` | 53,248 | `8d136190` | `55c697e864562445621cdf8a7bf6e84ae91361e393d382a3704e9aa55559041e` |
| `st011` | 53,248 | `750c6012` | `651b82a1e26c4fa8dd549e91e7f923012ed2ca54c1d9fd858655ab30679c2f0e` |
| `st018` | 163,840 | `5c403cc5` | `6df209ab5d2524d1839c038be400ae5eb20dafc14a3771a3239cd9e8acd53806` |

[`snesst/artifacts.manifest.json`](snesst/artifacts.manifest.json) 保存了这些值，并附有 MD5 和 SHA-1。搜索读取以 `.bin` 或 `.rom` 结尾的文件，按以下顺序进行，部件找到的第一个镜像生效：

1. `SNES_ST_FIRMWARE_DIR` 指定的每个目录，分隔方式与操作系统分隔路径的方式相同。
2. `UPD7725_FIRMWARE_DIR` 指定的每个目录。
3. 本项目被检出于其中的那个项目里的 `firmware/`。
4. 本仓库中的 `firmware/`。

不会下载任何内容。在 macOS、Linux 或 Windows 上确认你持有的副本：

```bash
shasum -a 256 firmware/st0010.bin
sha256sum firmware/st0010.bin
certutil -hashfile firmware\st0010.bin SHA256
```

摘要不在清单中的文件会被搜索跳过。传给 `snesst.firmware.identify` 时它会被拒绝，拒绝信息会说明去掉 512 字节文件头、丢弃最后 512 字节或交换字节对之后，它是否会变成已知镜像。

## 没有任何文档记载的握手

共享内存下方的窗口是处理器的数据端口，共享内存则是处理器自己的数据 RAM。微码在第一条指令上置起其请求位，并等待主机从数据端口取走一个字。在此之前，它永远不会进入监视命令的循环，未经握手就与之通信的部件不会有任何应答。

`Chip` 在构建部件时执行该握手：一条指令，两次读取数据端口，然后运行 200,000 条指令。之后每段程序都在各自的位置等待。

| 部件 | 程序的等待位置 |
|:--|:--|
| ST010 | 第 3、4、5 字，测试保存命令和启动字节的字的最高位 |
| ST011 | 第 2 字 |

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

此示例需要两个镜像。

## 它是否正确

[`conformance/hardware.json`](conformance/hardware.json) 记录了本包对接口断言的每个值，每项都标记为未验证，并附有证据和能够定论的测量：4,096 字节的共享窗口、启用位 `0x80000`、`0x20` 和 `0x21` 处的寄存器字节、握手的两次读取、两处等待位置，以及复位的作用。[`conformance/hardware.test.py`](conformance/hardware.test.py) 将每一项与代码中的常量对照。

| 层 | 检查内容 | 需要镜像 |
|:--|:--|:--:|
| 处理器 | 每条指令，见 [nec-upd7725-96050-python](https://github.com/gufranco/nec-upd7725-96050-python) 和 [arm6-python](https://github.com/gufranco/arm6-python) | 否 |
| 解码 | 启用写入、两个寄存器字节、共享窗口，在全零程序上检查 | 否 |
| ST018 邮箱 | 三个端口、状态位和拒绝情况，在测试中编写的简短 ARM 程序上检查 | 否 |
| 识别 | 每个镜像由决定性摘要命名，以及错误文件得到的每种拒绝 | 否 |
| 目录 | 全部三个部件及其响应的每个名称 | 否 |
| 部件 | ST010 和 ST011 各自到达自己的等待位置并在那里停留 4,096 条指令，且 ST010 应答一条命令 | 是 |

[`snesst/microcode.test.py`](snesst/microcode.test.py) 负责最后一行，没有镜像时报告为跳过。一个单独的 CI 作业启动每个部件，为 ST010 和 ST011 运行 `conformance.against_cartridges`，并在运行页面上说明是否真正驱动了某个部件。

[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) 列出尚未知晓的内容，以及能解决每一项的测量。[`conformance/divergences.json`](conformance/divergences.json) 记录各来源的分歧之处，以及本包采用哪一个。

## 参与开发

| 需求 | 位置 |
|:--|:--|
| 每项门禁检查及其运行顺序 | [CONTRIBUTING.md](CONTRIBUTING.md) |
| 面向编程智能体的同一份材料 | [AGENTS.md](AGENTS.md) |
| 本仓库与该系列其他仓库共享的标准 | [FAMILY.md](FAMILY.md) |
| 缺陷报告 | [GitHub Issues](https://github.com/gufranco/snes-st-python/issues) |
| 安全报告 | [SECURITY.md](SECURITY.md) |

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

每个模块旁边都有一个以其命名的测试文件，每个都可以单独运行，例如 `python3 snesst/chip.test.py`。覆盖率是一项硬性门禁检查，要求 100% 语句和分支覆盖，在 [pyproject.toml](pyproject.toml) 中设置。吞吐量下限在覆盖率步骤之外运行。

## 参考资料

- Seta 没有公开过关于这些部件的任何资料。[`conformance/hardware.json`](conformance/hardware.json) 中权威等级的最高一级为空，记录中也如此说明。
- 读者提供的微码，用于本包给出的每个答案。它在运行前经摘要确认，且不在本仓库中。
- [nec-upd7725-96050-python](https://github.com/gufranco/nec-upd7725-96050-python)，用于 uPD96050 以及 NEC 印发的关于它的每项事实。
- [arm6-python](https://github.com/gufranco/arm6-python)，用于 ST018 内部的 ARM60。
- [snes-driver-python](https://github.com/gufranco/snes-driver-python)，用于读取卡带自身的代码，以找出它对其协处理器说了什么。
- 模拟器中的行为模型，用于接口常量：共享内存位于何处，以及哪些地址是寄存器。

## 引用

[CITATION.cff](CITATION.cff) 在每次发布时由标记包版本的脚本更新。

## 许可证

MIT。见 [LICENSE](LICENSE)。
