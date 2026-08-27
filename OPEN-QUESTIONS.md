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

### What either part does with a command number outside the eight.

**The document says.** Nothing.

**What this project follows.** The microcode, for every command number, including
the ones no cartridge issues.

**Why.** The program is run rather than described, so an unasked command is
answered by the same mechanism as an asked one. What is absent is confirmation
rather than an answer.

**What would settle or reopen it.** Nothing published would. A capture of a real
part answering one would.

## Where the question is a scope boundary, not an unknown

### Anything about timing.

**What this project does.** Models neither how long a command takes nor whether a
console polling for an answer can outrun it.

**Why it is not a gap in the model.** The cycles are spent inside the processor,
and that member is the one that reports them. A second claim about timing here
would be a second source of truth for something a member already answers.

**What would settle or reopen it.** A measurement of a real cartridge, which
would belong in this repository because it is a property of the board rather than
of the processor.

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

## The third chip Seta made, and why it is not here

**The ST018 is not modelled and does not belong in this member as it stands.**
The name says otherwise, which is the trap: it shares a vendor and a prefix with
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

Putting it here would put two unrelated processors in one member. What fits the
shape this family already has is a clocked member for the ARM core, after which
this one becomes the three coprocessors Seta made rather than the two, consuming
two processor members instead of one.

Its firmware was dumped in 2012, so the rule that a part with a ROM runs its ROM
could be met. What is missing is the core, and that is a clocked part at this
family's standard rather than a wrapper.

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
that, the member would publish cycle counts in the manufacturer's own S, N, I and
C terms and refuse to convert them to ticks, the way this family already refuses
to convert between the console and the audio unit.

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

| Address | What the firmware does with it |
|:--|:--|
| `0x00000000` | The program it is executing |
| `0x40000000` | Registers, written at offsets `0x20` through `0x2D`, and `0x20` read once |
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

| Address | What the cartridge does with it |
|:--|:--|
| `$3800` | Read only. One byte in from the part |
| `$3802` | Written only. One byte out to the part |
| `$3804` | Read for status, and written to drive the part's reset |

Five routines in bank `$00` are the whole of the console side, and every other
site calls one of them:

| Routine | File offset | What it does |
|:--|:--|:--|
| `$E717` | `0x006717` | Writes `0`, then `1`, then `0` to `$3804`, with a full index-register countdown between each. A reset pulse |
| `$E862` | `0x006862` | Writes `0` to `$3804`, counts down, then polls `$3804` until bit 7 sets |
| `$E873` | `0x006873` | Sends: checks the guard, and writes the accumulator to `$3802` only if it passes |
| `$E87E` | `0x00687E` | Receives: checks the guard, polls `$3804` until bit 0 sets, then reads `$3800` |
| `$E892` | `0x006892` | The guard: reads `$3804` and returns carry set when bit 4 is set, which is what both transfer routines abandon on |

That gives four bits of `$3804` a role the cartridge can be seen to rely on:

| Bit | How the cartridge reads it |
|:--|:--|
| 0 | Polled before every read of `$3800`. A byte is waiting |
| 4 | Polled before every transfer in either direction. Set means the transfer is abandoned |
| 6 | Read once beside bit 7, in the routine at `$EFBD` that decides between two paths |
| 7 | Polled after the reset pulse until it sets |

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

That leaves one arrangement, because each side has exactly one port it writes and
one it reads:

| Direction | Console | Part | What gates it |
|:--|:--|:--|:--|
| Console to part | writes `$3802` | reads `0x40000010` | part waits for bit 3 of `0x40000020` to set |
| Part to console | reads `$3800` | writes `0x40000000` | part waits for bit 0 of `0x40000020` to clear |
| Abandon | `$3804` bit 4 | `0x40000020` bit 5 | both give up on it |

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

| Derived here | ares |
|:--|:--|
| Console writes `$3802`, part reads `0x40000010` | `cputoarm` buffer, ready flag cleared on the read |
| Part writes `0x40000000`, console reads `$3800` | `armtocpu` buffer, ready flag cleared on the read |
| `$3804` read is status, written to drive reset | the same, with bit 0 of the written byte driving it |
| `0x40000020` bit 3 set means a byte is waiting for the part | `cputoarm.ready` |
| `0x40000020` bit 0 clear means the last outgoing byte was collected | `armtocpu.ready` |
| `$3804` bit 7 is what the console waits for after reset | `ready` |

**And it explains the write this record could not pair.** The firmware writes
`0x40000020`, `0x40000024` and `0x40000028` and then `0x4000002C`, which was
recorded here as a shape with no meaning attached. ares reads those four as a
24-bit timer being loaded a byte at a time and then committed, which fits the
order exactly. That reading is ares's rather than this project's: what the
artifact establishes is the four writes and their order, and nothing here
observes a timer counting.

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

## What is deliberately not modelled

Absent rather than unknown, and absent on purpose:

- **The processor.** It has a repository. Modelling it twice is how two models
  start disagreeing.
- **Any microcode.** Seta's programs are not carried, not linked to and not
  reconstructible from anything here. Everything published is a digest.
- **The cartridge board.** Where the part sits in the memory map is
  [snes-mapper-python](https://github.com/gufranco/snes-mapper-python).
