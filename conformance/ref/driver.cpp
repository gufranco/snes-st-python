#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>

typedef uint8_t uint8;
typedef uint16_t uint16;
typedef uint32_t uint32;
typedef int8_t int8;
typedef int16_t int16;
typedef int32_t int32;
typedef bool bool8;

#define TRUE true
#define FALSE false

struct SST010 {
    uint8 op_reg;
    uint8 execute;
    bool8 control_enable;
};

struct SST010 ST010;

static uint8 SRAM[0x1000];

struct FakeMemory {
    uint8 *SRAM;
    uint32 SRAMMask;
};

static struct FakeMemory Memory = {SRAM, 0x0FFF};

#define ST010_WORD(o) (Memory.SRAM[o + 1] << 8) | (Memory.SRAM[o])
#define ST010_DWORD(o)                                                                   \
    (Memory.SRAM[o + 3] << 24) | (Memory.SRAM[o + 2] << 16) | (Memory.SRAM[o + 1] << 8) | \
        (Memory.SRAM[o])

#include "st010_bodies.inc"

int main(void) {
    char line[256];
    memset(SRAM, 0x00, sizeof(SRAM));
    memset(&ST010, 0, sizeof(ST010));

    while (fgets(line, sizeof(line), stdin)) {
        char verb[16];
        long first = 0, second = 0;
        if (sscanf(line, "%15s %li %li", verb, &first, &second) < 1) continue;

        if (!strcmp(verb, "reset")) {
            memset(SRAM, 0x00, sizeof(SRAM));
            memset(&ST010, 0, sizeof(ST010));
        } else if (!strcmp(verb, "w")) {
            S9xSetST010((uint32)first, (uint8)second);
        } else if (!strcmp(verb, "r")) {
            printf("%02X\n", S9xGetST010((uint32)first));
        } else if (!strcmp(verb, "poke")) {
            SRAM[first & 0x0FFF] = (uint8)second;
        } else if (!strcmp(verb, "dump")) {
            for (int at = 0; at < 0x1000; at++) printf("%02X", SRAM[at]);
            printf("\n");
        } else if (!strcmp(verb, "state")) {
            printf("%02X %02X %d\n", ST010.op_reg, ST010.execute, (int)ST010.control_enable);
        }
    }
    return 0;
}
