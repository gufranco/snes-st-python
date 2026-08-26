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
and runs their microcode. The ST018 is a thirty two bit ARMv3 processor clocked
at 21.47 MHz.

Putting it here would put two unrelated processors in one member. What fits the
shape this family already has is a clocked member for the ARM core, after which
this one becomes the three coprocessors Seta made rather than the two, consuming
two processor members instead of one.

Its firmware was dumped in 2012, so the rule that a part with a ROM runs its ROM
could be met. What is missing is the core, and that is a clocked part at this
family's standard rather than a wrapper.

## What is deliberately not modelled

Absent rather than unknown, and absent on purpose:

- **The processor.** It has a repository. Modelling it twice is how two models
  start disagreeing.
- **Any microcode.** Seta's programs are not carried, not linked to and not
  reconstructible from anything here. Everything published is a digest.
- **The cartridge board.** Where the part sits in the memory map is
  [snes-mapper-python](https://github.com/gufranco/snes-mapper-python).
