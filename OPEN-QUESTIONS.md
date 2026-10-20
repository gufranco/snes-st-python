# Open questions

What this project does not know for certain, and what it would take to find out.

Seta published nothing about either part. There is no data sheet, no application
note and no register map, so the top rung of the authority ladder is empty here
and [`conformance/hardware.json`](conformance/hardware.json) says so rather than
promoting the rung below it.

What that leaves is a sharp split. What each command computes is settled by
running the microcode a reader supplies, which removes the whole class of error a
description introduces. The interface around the microcode is not settled at all:
where the shared memory sits, which addresses are registers and what wakes the
part are inferences from a cartridge's own code and from a reference
implementation.

The processor underneath both parts is a NEC uPD96050 and it is not modelled
here. It is
[nec-upd7725-96050-python](https://github.com/gufranco/nec-upd7725-96050-python),
which carries its own record and its own open questions.

Every entry is also in
[`conformance/divergences.json`](conformance/divergences.json) with its status
and severity, so a program can read what a person reads here.

## Why running the microcode closes most of it

A derived model covers the commands somebody thought to look at, and the corners
nobody characterised are exactly where it is silently wrong. Running the program
removes that.

It removed something concrete here. The model this replaced treated one write as
a switch that made the part start listening, and the part has no switch: the
window below the shared memory is the processor's own data port, and the
microcode raises its attention bit on its first instruction and waits for the
console to take a word off it. That is recorded as a closed divergence rather
than deleted, because it is the clearest evidence in this repository that running
a program beats describing one.

## What would settle almost all of them

A capture of the cartridge bus while a real cartridge runs, or a Seta document.
Neither is available here.

## Where the interface is inferred rather than documented

### Where the shared memory sits and which addresses are registers.

**The document says.** Nothing. There is no document.

**What this project follows.** A four kilobyte window shared with the console,
with two registers just past the end of it, taken from a reference implementation
and from what a cartridge's own code does.

**Why.** It is the only source there is, and it is a rung below everything else
here. The map is not derived from the microcode, because the microcode cannot say
where a console addressed it from.

**What would settle or reopen it.** A bus capture, or a board schematic.

### Whether the two registers past the shared memory are the only two.

**The document says.** Nothing.

**What this project follows.** Two.

**Why.** Two is what the one cartridge per part touches. Nothing establishes that
a third does not exist; it establishes that no shipped program uses one.

**What would settle or reopen it.** A cartridge that addresses a third, or a
schematic.

### Whether the ST011 ever writes the byte that starts a command.

**The document says.** Nothing.

**What running the ST010 cartridge showed.** The static readings never found a
write to `$680021`, the byte that starts a command running, so on 2026-10-19 the
cartridge was run instead. The image was Exhaust Heat II - F1 Driver e no Michi
(Japan), 1,048,576 bytes, SHA-256
`1c78d8208a05cbfe88ee019edbc3a0c9cdabfd2b62089ca119215bbc7e581611`, with the ST010
microcode appended, in MAME 0.289 headless with a write tap on `$680000` to
`$6FFFFF` and the `$E80000` mirror. With the controls untouched, at frame 992 of
the attract run, one instruction at `$80:8D69` wrote `$06` to `$680020` and `$80`
to `$680021`.

The cartridge's own bytes say why the readings missed it. At file offset
`0x0D66` they are `A9 06 80 8F 20 00 68`: a load of `$8006` with a sixteen bit
accumulator, then a long store to `$680020`. That is one word-wide write carrying
the command in its low byte and the start bit in its high byte. It is followed by
`AF 20 00 68 30 FA`, a word read of the same pair that loops while bit 15 is set,
which is the console polling the start bit. The image holds nine long stores to
`$680020` and every one is preceded by `A9 nn 80`, for commands 1, 2, 3, 4, 6, 7
and 8.

So the earlier statement here, that every write to the pair is one byte wide, was
wrong. The reader in
[snes-driver-python](https://github.com/gufranco/snes-driver-python) lost the
accumulator width at these sites and recorded `write1@0x680020` where the
cartridge writes two bytes. Re-recorded on 2026-10-19 from that reader at
`adc1b8c`, the shapes in
[`conformance/st010shapes.json`](conformance/st010shapes.json) now carry
`write2~@0x680020` wherever its MAME trace saw the word store, and `write?` where
nothing settled the width.

**What is still open.** The ST011. Its cartridge, Hayazashi Nidan Morita Shougi
(Japan), 524,288 bytes, SHA-256
`85825a75ef662b28d0111c0462ec3c34234da1d78d10472b8022fcba3b9eaed5`, run the same
way for 600 seconds with Start, A, B and Right pressed in turn, never wrote
anywhere in `$680000` to `$68017F`. All 13 of its writes to the part went to the
data port at `$600000`, from code in bank `$84`, and the image holds no long
store to `$680020` or `$680021`. Whether its engine is ever started through the
start byte is unknown.

**What this costs.** No command sweep for either part yet. The ST010's start is
now known to be a word write of `$80nn`, and its recorded shapes say so where a
trace reached the routine and say `?` where none did.

**What would settle or reopen it.** For the ST011, a run that reaches the shogi
engine's own moves while watching `$680021` and `$600000`, or a capture of a real
console driving it.

### Which recorded shapes rest on an assumed width.

**The document says.** Nothing. How wide an access is depends on the
accumulator's width when the cartridge's routine runs, and that is set by
whoever called the routine.

**What this project follows.** Every shape the reader gives, with every width
labelled. A bare width, such as `write2`, is one the code sets on the way to the
access. `*` marks one a run of the image used, `~` one that snes-driver-python's
headless MAME trace saw the bus move at that instruction, and `?` one nothing
settled. A `?` is replayed as one byte, as every width was before the label
existed, and `conformance.against_cartridges` prints how many of the accesses it
played rest on that assumption.

**What that leaves, measured on 2026-10-20.** Re-recorded from the reader at
`62d619b`, which walks both arms of every forward conditional branch: 21 of the
42 ST010 shapes carry a `?`, 92 of the 232 accesses they make counting each
shape as often as it was seen, while 19 shapes and 92 accesses are traced and 2
shapes are known throughout. 10 of the 16 ST011 shapes carry a `?`, 30 of 76
accesses, as before. All 1,543 ST018 shapes are known, against 7 from the
reader at `adc1b8c`, which took only the arm a branch falls through to; the
routine at `$E796` that reads `$3802` is still one the sweep from the reset
vector does not reach. Before the labels, all 339 accesses across the three
files read as one byte with nothing saying that was assumed.

**What would settle or reopen it.** A trace that reaches the routine an assumed
width sits in, which for these cartridges means input that gets the game past
its attract run, or a jump table the reader's walk can follow to the routine's
callers.

### What either part does with a command number outside the eight.

**The document says.** Nothing.

**What this project follows.** The microcode, for every command number, including
the ones no cartridge issues.

**Why.** The program is run rather than described, so an unasked command is
answered by the same mechanism as an asked one. What is absent is confirmation
rather than an answer.

**What would settle or reopen it.** Nothing published would. A capture of a real
part answering one would.

### How long one instruction takes on each board.

**What this project does.** Runs a started command on the processor's clock. The
write that sets the start bit only stores it, a console polling the start byte
reads the part busy, and the program advances only when the host steps it.
`finish()` returns the instructions a command took: 106 for the ST010's command 1
on the point the README uses. That is a count of instructions, not of time.

**What the boards carry.** Martin Korth's fullsnes,
`https://problemkaputt.de/fullsnes.htm`, fetched on 2026-10-19 with SHA-256
`3853b65a7331bf12eea431ff494a2948a1c78ef22f7e819db4b139fd5a79f6c6`, lists the
oscillators found in cartridges by their markings: the ST010 board carries a
22.000 MHz plastic oscillator marked `[M]22000C`, and the ST011 board a 15.000 MHz
ceramic one marked `15.00X`. That is a third-party board reading, the same kind of
source as the ST018 component list below, and it settles which oscillator each
board carries.

**What is still not known.** How many oscillator periods one uPD96050 instruction
costs. The uPD77C25 executes one instruction per external clock, no document for
the uPD96050 exists, and fullsnes's notes that the ST010 runs internally at
11.000 MHz and the ST011 without a divider come with no measurement behind them.
So nothing here converts an instruction count into time.

**What would settle it.** A uPD96050 data sheet, or a cartridge timed on a
console: start a command, count console cycles until the start bit clears, and
divide by the instruction count `finish()` reports for the same command.

## Where the question is a scope boundary, not an unknown

### What a reset does.

**The document says.** Nothing.

**What this project does.** Forgets that the console ever performed the
handshake, and does not reload the program.

**Why.** The program is masked into the ROM, so nothing a reset does can reach
it. What is left is the one piece of state the interface makes observable, and
the record marks the claim as unverified rather than presenting it as documented.

**What would settle or reopen it.** A capture across a console reset.

## What is not in question

So the boundary is visible rather than implied:

- **What each command computes.** The program decides, and the program is run.
  Nothing here describes a command.
- **Where each part's program waits.** Measured on both, on a copy confirmed by
  digest before a byte of it ran, rather than assumed to be the same place.
- **Which image each part runs.** Recorded with a deciding digest, so a supplied
  file is confirmed rather than trusted.
- **Everything about the processor.** Settled in the member that models it,
  against NEC's own data sheet.

## The third chip Seta made, and how it got here

**The ST018 is modelled, as `snesst.ST018`, and it is a separate class rather
than a third model behind `Chip`.** The name is the trap: it shares a vendor and a prefix with
the two parts here and shares no silicon with them. The ST010 and ST011 are NEC
uPD96050 digital signal processors, which is why this member consumes
[nec-upd7725-96050-python](https://github.com/gufranco/nec-upd7725-96050-python)
and runs their microcode. The ST018 is a thirty two bit ARM processor on the
cartridge's own oscillator.

**It is not clocked at 21.47 MHz.** That figure is the console's master clock and
it circulates widely as the ST018's. The board carries its own crystal: the
component list for PCB SHVC-1DE3B-01 reads `X1 3pin [M]21440C 21.44MHz (plastic
oscillator)`, beside a 160 pin Seta ST018 marked (C)1994-5. So the part is
independently clocked, exactly as the S-SMP is, and no figure here converts one
clock to the other. Whether anything divides or multiplies that oscillator before
it reaches the core is not known.

**The architecture is inferred, not read.** Every source calls it ARMv3, and the
basis is what the firmware happens to use rather than a die reading or a part
marking: the program uses a 32 bit program counter and the CPSR, and never uses
BX, LDRH, System mode or Thumb. That is good evidence for ARMv3 and it is not the
same as knowing which ARM6 family core is inside. Nobody has published one.

Putting it behind `Chip` would put two unrelated processors behind one interface
that describes neither, so the class is its own and the factory decides which a
name means. This member now consumes two processor members rather than one:
[nec-upd7725-96050-python](https://github.com/gufranco/nec-upd7725-96050-python)
for the two signal processors and
[arm6-python](https://github.com/gufranco/arm6-python) for the ARM.

What is modelled is what the two artifacts establish. Bit 7 of `$3804` is the one
thing the model answers that neither states, and it is recorded in
[conformance/divergences.json](conformance/divergences.json) under
`nothing-sets-the-bit-the-console-waits-on` rather than left to look derived.

**What that member could and could not reach.** ARM published a datasheet for the
ARM60 whose chapter 10 gives, per instruction and per cycle, the address driven
and the state of Nbw, Nrw, seq, Nmreq and Nopc. That is the resolution the clocked
members of this family are held to, and it comes from the manufacturer. What no
document gives is how many of this cartridge's oscillator ticks one of those
cycles costs. The ARM60 datasheet puts that on a pin, `Nwait`, and says the clock
may be stretched without limit. ARM's own reference design for the family runs the
memory clock at half the processor clock. The ST018's answer is unknown, the 32 KB
data ROM sits on an eight bit databus so a word read from it cannot be one access
whatever the answer, and the part's ROM is on the die so there is no bus to probe.

**How to settle it.** Decapping and probing, which is out of reach here. Short of
that, `ST018.cycles` and `ST018.tally` publish the cycles
[arm6-python](https://github.com/gufranco/arm6-python) spends on the ARM's bus,
in the manufacturer's own S, N, I and C terms, and `run_for` takes a budget in
them. Nothing here converts them to oscillator ticks, the way this family already
refuses to convert between the console and the audio unit.

**What running the firmware already shows.** On 2026-08-27 the dumped firmware
was driven against [arm6-python](https://github.com/gufranco/arm6-python), which
is the clocked member this needs. It is 163,840 bytes and opens with an ARM
exception vector table, eight consecutive branches beginning `EA00002A`. The
model executes the boot sequence without a special case: the reset vector
branches to `0x0000B0`, which sets a register to `0x4000002C` and stores 2 there,
loads `0xD3` and writes it to the whole CPSR, which is supervisor mode with both
interrupt disables set, loads the stack pointer PC-relative from a literal at
`0x0008A4`, and calls `0x000100`, which opens by pushing with `STMDB SP!`.

That gives three regions, read off the part's own program rather than from any
implementation of it:

| Address      | What the firmware does with it                                                                                                             |
| :----------- | :----------------------------------------------------------------------------------------------------------------------------------------- |
| `0x00000000` | The program it is executing                                                                                                                |
| `0x40000000` | Registers, written at offsets `0x20` through `0x2D`, and `0x20` read once                                                                  |
| `0xE0000000` | Work RAM. The stack pointer is loaded with `0xE0004000`, so sixteen kilobytes, and the repeated reads at `0xE0003FE0` upward are its stack |

What this does not show is what any of those registers answer, because the model
has none: it runs 1,271 instructions across 35 addresses and then spins in the
routine at `0x000100`, reading zeros where the part would read a port. The map is
what the firmware asks for, not what the silicon replies, and the difference is
the whole of what a member would still have to establish.

**What the cartridge's own code shows.** On 2026-08-27 the other half of that
interface was read off the cartridge, which is the same tier of authority as the
firmware: the artifact itself. The copy read is 524,288 bytes, sha256
`40cec32f4c1b5a2564b8bb2e825ca1314d2171edb8e934956a74827e14bc9972`, crc32
`dd852671`. Its header reports LoROM, chipset `0xF5`, 512 KB of program and 8 KB
of save RAM, titled `NIDAN MORITASHOGI2`. The method was a reachability walk from
the reset vector, following calls, branches and jumps and tracking the accumulator
and index widths through `SEP` and `REP`, so every address below is one that
reached execution rather than one that matched a pattern in the file. Blind
scanning was tried first and discarded: it answers without instruction boundaries,
so it reports operand bytes as addresses.

Three console-side addresses answer, and no others in `$2000` through `$5FFF`
outside the console's own registers:

| Address | What the cartridge does with it                                    |
| :------ | :----------------------------------------------------------------- |
| `$3800` | Read only. One byte in from the part                               |
| `$3802` | Written for one byte out to the part, and read once to clear bit 2 |
| `$3804` | Read for status, and written to drive the part's reset             |

Five routines in bank `$00` are the whole of the console side, and every other
site calls one of them:

| Routine | File offset | What it does                                                                                                      |
| :------ | :---------- | :---------------------------------------------------------------------------------------------------------------- |
| `$E717` | `0x006717`  | Writes `0`, then `1`, then `0` to `$3804`, with a full index-register countdown between each. A reset pulse       |
| `$E862` | `0x006862`  | Writes `0` to `$3804`, counts down, then polls `$3804` until bit 7 sets                                           |
| `$E873` | `0x006873`  | Sends: checks the guard, and writes the accumulator to `$3802` only if it passes                                  |
| `$E87E` | `0x00687E`  | Receives: checks the guard, polls `$3804` until bit 0 sets, then reads `$3800`                                    |
| `$E892` | `0x006892`  | The guard: reads `$3804` and returns carry set when bit 4 is set, which is what both transfer routines abandon on |

That gives four bits of `$3804` a role the cartridge can be seen to rely on:

| Bit | How the cartridge reads it                                                            |
| :-- | :------------------------------------------------------------------------------------ |
| 0   | Polled before every read of `$3800`. A byte is waiting                                |
| 2   | Polled at `$E7E3` and `$E806`, then cleared by reading `$3802` at `$E812`             |
| 4   | Polled before every transfer in either direction. Set means the transfer is abandoned |
| 6   | Read once beside bit 7, in the routine at `$EFBD` that decides between two paths      |
| 7   | Polled after the reset pulse until it sets                                            |

**The read of `$3802`, corrected on 2026-10-20.** This record said `$3802` is
only written. The walk from the reset vector never reaches the routine at
`$E796`, and that routine reads it. Decoded from the cartridge's own bytes at
file offset `0x006806`: `AD 04 38 29 04 F0 F9` polls `$3804` until bit 2 sets,
`A9 00 8D C0 07` clears a flag in work RAM, then `AD 02 38` at `$E812` reads
`$3802` and `A9 AD` at `$E815` loads `$AD` over the byte read, which is then
sent as the next command. The value read is never used; the read is the point.
The firmware has the other half: after a call into `0x001000`, it loads
`0x40000000` into R11 at `0x00046C` and stores a byte at `0x40000010` at
`0x000470`, `E5CB0010`, the only immediate-offset store to that offset in the
program. That is the address it reads the console's byte from, and no console port is
seen returning what is stored there. ares at
`9408cb43d4948fc3ea6e152a307a34348df3fe04`, `sfc/coprocessor/armdsp/memory.cpp`
and `io.cpp`, reads the pair as a signal: the store sets its `signal`, shown
as bit 2 of `$3804`, and a console read of `$3802` clears it and answers 0. The
model now does both, which is the rung of that implementation for the value 0
and the artifacts' own rung for the two accesses.

**What this still does not settle.** The names above are the cartridge's usage,
never the part's documentation, and no document for this part exists. Nothing here
says which ARM-side address each console-side address appears at, and pairing the
two halves is the next thing a member would have to do rather than something these
two artifacts state. Bit 4 is the sharpest case: the cartridge abandons a transfer
on it and never sets it, so whether it means busy, faulted or absent cannot be read
off the console side at all. The remaining bits of `$3804` are never examined, which
is documented silence rather than a claim that they are unused.

**The two halves pair, and the pairing was derived before it was tested.** The
first attempt at this stopped and recorded a ceiling, on the grounds that feeding
the firmware invented port answers until the handshake completed would produce
whichever mapping made the run proceed. That reasoning was right about searching
and wrong about the situation: the mapping did not have to be searched for,
because the firmware states it. Reading it needed a disassembler the ARM member
did not have, and once
[arm6-python](https://github.com/gufranco/arm6-python) had one the two routines
that matter read straight off.

At `0x000300` the part sends a byte: it waits until bit 0 of `0x40000020` is
clear, stores the byte at `0x40000000`, and settles. At `0x00031C` it receives
one: it waits until bit 3 of `0x40000020` is set, reads the byte from
`0x40000010`, and settles. Both wait through a common helper at `0x0002C0` that
polls `0x40000020` under a mask, and both bracket the transfer with a
sixty-four iteration delay at `0x0002B0`. The guard at `0x00011C` tests bit 5 of
the same register and is the counterpart of the console's guard at `$E892`.

That leaves one arrangement for the bytes, because each side has exactly one port
it writes a byte to and one it reads a byte from:

| Direction       | Console        | Part                | What gates it                                 |
| :-------------- | :------------- | :------------------ | :-------------------------------------------- |
| Console to part | writes `$3802` | reads `0x40000010`  | part waits for bit 3 of `0x40000020` to set   |
| Part to console | reads `$3800`  | writes `0x40000000` | part waits for bit 0 of `0x40000020` to clear |
| Abandon         | `$3804` bit 4  | `0x40000020` bit 5  | both give up on it                            |
| Part signals    | reads `$3802`  | writes `0x40000010` | console waits for bit 2 of `$3804` to set     |

**Tested as a prediction rather than searched for.** Driven with a memory
implementing exactly that mapping and nothing else, the firmware reads the
offered byte, reaches 75 distinct addresses instead of the 34 it reaches with
nothing offered, and writes bytes back through `0x40000000`. Offered a byte that
is not a command it knows, it answers `0xEE`, which is the value its own
unknown-command path loads at `0x0001E8`.

**The part has twenty-eight commands.** They are a table at `0x00023C`, four
bytes per entry, terminated by `0xFF`: `0xF1` through `0xF6`, then `0xA0`
through `0xA5`, `0xA8` through `0xAF`, and `0xB0` through `0xB7`. Each entry
carries the command byte, a second byte, and a handler address. Two of them are
confirmed by the other artifact: the cartridge sends `0xF1` at `$F030` and `0xF2`
at `$F089`, which is two independent sources agreeing on the same values.

**What the independent implementations say.** Checked on 2026-08-27, after the
derivation above rather than before it, because an independent implementation is
the bottom rung of this family's ladder and cannot be the thing a mapping is
taken from.

No FPGA implementation of this part exists in the open. sd2snes carries CX4,
GSU, OBC1, SA-1, S-DD1, SGB and a uPD77C25 whose program counter is eleven bits
wide, so 2,048 words, which covers DSP1 through DSP4 and no Seta part at all.
The MiSTer SNES core carries BSX, CX4, DSP, GSU, MSU1, SA-1, S-DD1, SPC7110,
Sufami, RTC4513 and SRTC, and its DSP microcode image packs dsp1, dsp1b, dsp2,
dsp3, dsp4 and st010 by name. So the ST010 has one FPGA implementation, the
ST011 has none, and neither does this part.

The one independent implementation is software: ares carries it as `armdsp`. It
agrees with the mapping above on every point, having been written by somebody
else from the same artifacts:

| Derived here                                                        | ares                                                |
| :------------------------------------------------------------------ | :-------------------------------------------------- |
| Console writes `$3802`, part reads `0x40000010`                     | `cputoarm` buffer, ready flag cleared on the read   |
| Part writes `0x40000000`, console reads `$3800`                     | `armtocpu` buffer, ready flag cleared on the read   |
| `$3804` read is status, written to drive reset                      | the same, with bit 0 of the written byte driving it |
| `0x40000020` bit 3 set means a byte is waiting for the part         | `cputoarm.ready`                                    |
| `0x40000020` bit 0 clear means the last outgoing byte was collected | `armtocpu.ready`                                    |
| `$3804` bit 7 is what the console waits for after reset             | `ready`                                             |

**And it explains the write this record could not pair.** The firmware writes
`0x40000020`, `0x40000024` and `0x40000028` and then `0x4000002C`, which was
recorded here as a shape with no meaning attached. ares reads those four as a
24-bit timer being loaded a byte at a time and then committed, which fits the
order exactly. That reading is ares's rather than this project's: what the
artifact establishes is the four writes and their order.

**The timer counts, at the rung of that implementation.** The model now does
what ares at commit `9408cb43d4948fc3ea6e152a307a34348df3fe04` does in
`sfc/coprocessor/armdsp/memory.cpp` and `armdsp.cpp`: the writes to `0x20`,
`0x24` and `0x28` set the low, middle and high bytes of a latch, the write to
`0x2C` copies the latch into the count, the count falls by one for every cycle
the ARM spends until it reaches zero, and a reset empties both. Nothing reads
the count back, in ares or in any instruction this record has seen the firmware
execute, so no observation here can tell a counting timer from a stored byte.
What would settle it is the firmware reading the count, or an interrupt line
the count drives, seen on a part; until then it is recorded as
`the-timer-is-an-implementation-s-reading`.

**Two regions the artifact names for itself.** The image is 163,840 bytes, which
is 128 KiB then 32 KiB. The first region ends in zero padding from `0x01FFE0`,
and the second is dense data rather than code. At `0x0010E4` the firmware loads
the literal `0xA0000000`, adds an index and reads a byte, so the second region is
a data ROM at `0xA0000000` and the split is the part's own. ares maps it the same
way. A member has to load the image as two regions rather than one flat block.

**What is still not paired.** The console waits on bit 7 of `$3804` after the
reset pulse and nothing the firmware executes sets it, so it is the interface
hardware answering rather than the program. ares models it exactly that way, as a
flag its bridge owns and neither side writes, which is consistent and is not
evidence: an implementation is free to invent a flag that satisfies the firmware
it was tested against. What would settle it is the package opened and probed, and
that is a permanent ceiling here.

The guard bits are the same shape. The console's routine at `$E892` abandons a
transfer when bit 4 of `$3804` is set, and the firmware's at `0x00011C` abandons
when bit 5 of `0x40000020` is set. Neither implementation ever sets either, so
both are read by code that has never seen them set, and what they mean is
unestablished on both sides. The remaining bits of both registers are never read
at all, which is documented silence rather than a claim that they are unused.

**What replaying the cartridge's exchanges shows.** `conformance.against_cartridges
st018` plays the five recorded shapes that move a byte at the part built from the dump in
`snes-roms/5 Tools & Service Test Carts/CPU/`, SHA-256
`6df209ab5d2524d1839c038be400ae5eb20dafc14a3771a3239cd9e8acd53806`. Until
2026-10-20 the replay never ran the ARM between two console accesses, so a byte
written to `$3802` sat unread and the one read of `$3800` found nothing. Nothing
gives the number of ARM cycles one console access allows, so the replay now does
what the cartridge does instead of claiming a time: the ARM runs 100 instructions
before every access, and a poll that comes right before a read of `$3800` keeps
polling `$3804`, the ARM running 100 instructions between looks, until bit 0
sets or 400 looks have passed. That is the loop at `$E886`, file offset
`0x006886`, `AD 04 38 29 01 F0 F9`, followed by `AD 00 38` at `$E88D`. The 100
and the 400 are the pacing the program dump run already uses, not a measurement.

Run on 2026-10-20 against the seven shapes the reader at `adc1b8c` gave, the ARM
took the first byte the longest shape sends, the status falling from `$88` to
`$80`, and nothing came back: no shape that sent also read `$3800`, because that
reader took only the arm a branch falls through to, and the receive at `$E87E`
falls through `BCC $E886` to an `RTS`.

**What it shows now.** Re-recorded the same day from the reader at `62d619b`,
which walks both arms of every forward branch, the cartridge gives 1,543 shapes,
1,541 of which move a byte. `conformance.against_cartridges st018` plays the 64
with the fewest accesses, in 23 seconds on the machine that recorded this: 28 of
them read `$3800`, and 12 of those got a byte back, so the run exits 0. Playing
every one, with `--every`, took more than eighteen minutes of processor time:
1,032 of the 1,541 got a byte back and 449 that read got nothing, and the run
exits 0. That is a local run rather than a CI step; CI plays the same 64
whenever an image is present.

## What is deliberately not modelled

Absent rather than unknown, and absent on purpose:

- **The processor.** It has a repository. Modelling it twice is how two models
  start disagreeing.
- **Any microcode.** Seta's programs are not carried, not linked to and not
  reconstructible from anything here. Everything published is a digest.
- **The cartridge board.** Where the part sits in the memory map is
  [snes-mapper-python](https://github.com/gufranco/snes-mapper-python).
