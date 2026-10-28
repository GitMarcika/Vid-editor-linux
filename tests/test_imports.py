import importlib
import unittest


MODULES = [
    "src.app",
    "src.gui.main_window",
    "src.gui.tabs.raw_cutter_tab",
    "src.gui.tabs.assembly_tab",
    "src.gui.tabs.recorder_tab",
    "src.gui.widgets.assembly_preview",
    "src.gui.widgets.capture_frame",
    "src.gui.widgets.crop_video_view",
    "src.services.assembly_export",
    "src.services.ffmpeg_export",
    "src.services.media_info",
]


class ImportSmokeTests(unittest.TestCase):
    def test_linux_main_modules_import(self) -> None:
        for module_name in MODULES:
            with self.subTest(module=module_name):
                importlib.import_module(module_name)


if __name__ == "__main__":
    unittest.main()
