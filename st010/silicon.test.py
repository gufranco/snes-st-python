import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from st010 import silicon

PRESENT = silicon.available()


def an_identity(part="st010"):
    """What the processor needs to be told about an image, without an image."""
    sys.path.insert(0, str(silicon.PROCESSOR))
    from upd7725 import firmware

    return firmware.Identity(part, "upd96050", "MADE UP", 16384, 2048)


def a_program():
    """An image of zeroes, which belongs to nobody and computes nothing."""
    return bytes(16384 * 3 + 2048 * 2)


def built(**options):
    return silicon.Silicon(image=a_program(), identity=an_identity(), boot=64, **options)


class WithoutTest(unittest.TestCase):
    """What the backend says when the things it needs are not there."""

    def setUp(self):
        self.real = silicon._processor

    def tearDown(self):
        silicon._processor = self.real

    def test_with_no_processor_it_offers_nothing(self):
        silicon._processor = lambda: None

        self.assertEqual(silicon.available(), {})

    def test_and_says_the_submodule_is_the_thing_that_is_missing(self):
        silicon._processor = lambda: None

        self.assertEqual(silicon.why_not(), silicon.WHY_NOT_PROCESSOR)

    def test_and_refuses_to_build_a_part(self):
        silicon._processor = lambda: None

        with self.assertRaises(silicon.NoFirmware):
            silicon.Silicon()

    def test_with_a_processor_but_no_image_it_says_that_instead(self):
        silicon._processor = lambda: (None, None)

        self.assertEqual(silicon.why_not({}), silicon.WHY_NOT_FIRMWARE)

    def test_a_part_with_no_image_is_refused_by_name(self):
        with self.assertRaises(silicon.NoFirmware) as raised:
            silicon.Silicon("st011", images={})

        self.assertIn("st011", str(raised.exception))

    def test_an_image_with_nothing_saying_what_it_is_is_refused(self):
        with self.assertRaises(silicon.NoFirmware) as raised:
            silicon.Silicon(image=a_program())

        self.assertIn("program", str(raised.exception))

    def test_the_refusals_say_what_to_do_about_them(self):
        self.assertIn("submodule", silicon.WHY_NOT_PROCESSOR)
        self.assertIn(silicon.PROCESSOR.name, str(silicon.PROCESSOR))
        self.assertIn("firmware", silicon.WHY_NOT_FIRMWARE)


class ImportTest(unittest.TestCase):
    def test_with_the_processor_unimportable_it_offers_nothing(self):
        held = dict(sys.modules)
        sys.modules["upd7725"] = None
        try:
            self.assertIsNone(silicon._processor())
        finally:
            sys.modules.clear()
            sys.modules.update(held)


class WhereTheImagesAreTest(unittest.TestCase):
    """Finding an image when the package is checked out inside another project.

    The search belongs to the processor package, and this is here to prove this
    one reaches it rather than looking only in its own directory: a project that
    carries this as a submodule keeps its images in its own tree, and naming a
    directory has to work from here too.
    """

    def _catalogue(self, part="st010"):
        where = Path(tempfile.mkdtemp()) / "made-up.bin"
        where.write_bytes(a_program())
        return {part: (an_identity(part), where)}

    def test_an_image_that_was_found_is_read_from_its_file(self):
        chip = silicon.Silicon(images=self._catalogue(), boot=64)

        self.assertEqual(chip.part, "st010")

    def test_the_other_part_is_reached_the_same_way(self):
        chip = silicon.Silicon("st011", images=self._catalogue("st011"), boot=64)

        self.assertEqual(chip.part, "st011")

    def test_with_an_image_present_there_is_no_reason_it_cannot_run(self):
        self.assertIsNone(silicon.why_not(self._catalogue()))

    def test_the_directory_can_be_named_from_outside_the_package(self):
        sys.path.insert(0, str(silicon.PROCESSOR))
        from upd7725 import firmware

        named = Path(tempfile.mkdtemp())

        self.assertIn(named, firmware.directories({firmware.DIRECTORY_VARIABLE: str(named)}))

    def test_and_the_project_this_sits_inside_is_searched_without_being_named(self):
        sys.path.insert(0, str(silicon.PROCESSOR))
        from upd7725 import firmware

        self.assertIn(firmware.ALONGSIDE, firmware.directories({}))


class ShapeTest(unittest.TestCase):
    """That the backend is the same shape as the model, so a caller can swap."""

    def test_it_carries_the_part_it_was_asked_for(self):
        self.assertEqual(built().part, "st010")

    def test_and_the_same_name_field_the_model_carries(self):
        self.assertEqual(built().model, "st010")

    def test_it_names_the_processor_the_image_says_it_runs_on(self):
        self.assertEqual(built().processor, "upd96050")

    def test_it_prints_as_the_part_and_how_it_is_run(self):
        self.assertIn("silicon", repr(built()))

    def test_the_shared_memory_is_the_size_the_model_shares(self):
        self.assertEqual(len(built().memory), silicon.MEMORY_BYTES)

    def test_memory_can_be_handed_over_at_the_start(self):
        chip = built(memory=bytes([0x5A]) * silicon.MEMORY_BYTES)

        self.assertEqual(chip.memory[0], 0x5A)

    def test_memory_longer_than_the_shared_memory_is_taken_up_to_it(self):
        chip = built(memory=bytes([0x11]) * (silicon.MEMORY_BYTES * 2))

        self.assertEqual(len(chip.memory), silicon.MEMORY_BYTES)


class HandshakeTest(unittest.TestCase):
    """The exchange a console performs before the part will take a command.

    The microcode raises its attention bit on its first instruction and waits for
    the console to read a word back. Until that happens it never reaches the loop
    that watches for a command, so a part that is spoken to without it answers
    nothing and looks broken. A console does this at power-on without being told.
    """

    def test_a_freshly_built_part_is_past_the_boot_exchange(self):
        chip = built()

        self.assertFalse(chip.chip.registers.sr.rqm)

    def test_the_exchange_can_be_asked_for_again_without_reloading(self):
        chip = built()

        chip.handshake()

        self.assertFalse(chip.chip.registers.sr.rqm)


@unittest.skipUnless(PRESENT, silicon.WHY_NOT_FIRMWARE)
class RealMicrocodeTest(unittest.TestCase):
    """The part itself, which only a machine holding its microcode can run."""

    def test_the_handshake_leaves_it_waiting_for_a_command(self):
        chip = silicon.Silicon()

        self.assertIn(chip.chip.registers.pc, silicon.COMMAND_LOOP["st010"])

    def test_and_it_stays_there_until_one_is_started(self):
        chip = silicon.Silicon()

        for _ in range(4096):
            chip.chip.step()

        self.assertIn(chip.chip.registers.pc, silicon.COMMAND_LOOP["st010"])

    def test_the_other_part_waits_in_its_own_place(self):
        chip = silicon.Silicon("st011")

        for _ in range(4096):
            chip.chip.step()

        self.assertIn(chip.chip.registers.pc, silicon.COMMAND_LOOP["st011"])

    def test_every_part_the_package_covers_reaches_a_wait_of_its_own(self):
        from st010 import models

        for name in models.MODELS:
            chip = silicon.Silicon(name)

            self.assertIn(chip.chip.registers.pc, silicon.COMMAND_LOOP[name], name)

    def test_a_command_runs_and_answers(self):
        chip = silicon.Silicon()
        chip.write(0x000000, 0x00)
        for at, value in enumerate((0x00, 0x01, 0x00, 0x02)):
            chip.write(0x680000 + at, value)
        chip.write(0x680000 + silicon.COMMAND_REGISTER, 0x01)

        chip.write(0x680000 + silicon.START_REGISTER, silicon.START)

        self.assertEqual(chip.read(0x680010) | (chip.read(0x680011) << 8), 0x9300)

    def test_and_the_start_byte_is_clear_once_it_has(self):
        chip = silicon.Silicon()
        chip.write(0x000000, 0x00)
        for at, value in enumerate((0x00, 0x01, 0x00, 0x02)):
            chip.write(0x680000 + at, value)
        chip.write(0x680000 + silicon.COMMAND_REGISTER, 0x01)
        chip.write(0x680000 + silicon.START_REGISTER, silicon.START)

        self.assertFalse(chip.execute & silicon.START)


class DecodeTest(unittest.TestCase):
    """The register decode, which is the cartridge's rather than the chip's."""

    def test_the_window_with_the_bit_clear_is_the_port_rather_than_a_refusal(self):
        chip = built()

        self.assertEqual(chip.read(0x000001), chip.console.read(1))

    def test_the_write_with_the_bit_clear_wakes_it_and_does_nothing_else(self):
        chip = built()

        chip.write(0x000000, 0x00)

        self.assertTrue(chip.enabled)

    def test_a_woken_part_reads_its_shared_memory(self):
        chip = built()
        chip.write(0x000000, 0x00)

        chip.write(0x680100, 0x37)

        self.assertEqual(chip.read(0x680100), 0x37)

    def test_the_command_address_holds_a_copy_of_the_command(self):
        chip = built()
        chip.write(0x000000, 0x00)

        chip.write(0x680000 + silicon.COMMAND_REGISTER, 0x04)

        self.assertEqual(chip.command, 0x04)

    def test_the_start_address_holds_what_was_written_to_it(self):
        chip = built()
        chip.write(0x000000, 0x00)

        chip.write(0x680000 + silicon.START_REGISTER, 0x01)

        self.assertEqual(chip.execute, 0x01)

    def test_a_sleeping_part_takes_no_command(self):
        chip = built()

        chip.write(0x680000 + silicon.COMMAND_REGISTER, 0x04)

        self.assertFalse(chip.enabled)

    def test_forgetting_it_was_woken_does_not_reload_the_part(self):
        chip = built()
        chip.write(0x000000, 0x00)
        chip.write(0x680100, 0x42)

        chip.reset()

        self.assertFalse(chip.enabled)
        self.assertEqual(chip.memory[0x100], 0x42)


class RunningTest(unittest.TestCase):
    """Starting a command, with a program that will never answer one."""

    def test_a_program_that_never_clears_the_start_byte_is_given_up_on(self):
        chip = built(patience=64)
        chip.write(0x000000, 0x00)

        with self.assertRaises(silicon.NeverFinished):
            chip.write(0x680000 + silicon.START_REGISTER, silicon.START)

    def test_and_says_which_command_it_was_and_how_long_it_waited(self):
        chip = built(patience=64)
        chip.write(0x000000, 0x00)
        chip.write(0x680000 + silicon.COMMAND_REGISTER, 0x03)

        with self.assertRaises(silicon.NeverFinished) as raised:
            chip.write(0x680000 + silicon.START_REGISTER, silicon.START)

        self.assertIn("0x03", str(raised.exception))
        self.assertIn("64", str(raised.exception))

    def test_a_write_without_the_start_bit_starts_nothing(self):
        chip = built(patience=64)
        chip.write(0x000000, 0x00)

        chip.write(0x680000 + silicon.START_REGISTER, 0x01)

        self.assertEqual(chip.execute, 0x01)

    def test_a_command_whose_start_byte_is_already_clear_ends_at_once(self):
        chip = built(patience=64)
        chip.write(0x000000, 0x00)
        chip.chip.stores.write_byte(silicon.START_REGISTER, 0x00)

        chip._run()

        self.assertEqual(chip.execute, 0x00)

    def test_the_odd_address_in_the_port_window_is_the_status_side(self):
        chip = built()
        before = chip.chip.registers.pc

        chip.write(0x000001, 0x00)

        self.assertTrue(chip.enabled)
        self.assertEqual(chip.chip.registers.pc, before)

    def test_a_program_that_clears_it_is_taken_at_its_word(self):
        chip = built(patience=64)
        chip.write(0x000000, 0x00)
        chip.chip.stores.write_byte(silicon.START_REGISTER, 0x00)

        chip.write(0x680100, 0x01)

        self.assertEqual(chip.read(0x680100), 0x01)


if __name__ == "__main__":
    unittest.main()
