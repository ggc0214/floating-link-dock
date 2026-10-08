from queue import SimpleQueue
import sys

from PIL import Image, ImageDraw
import pystray
from . import theme


def _set_macos_accessory_policy():
    from AppKit import NSApplication, NSApplicationActivationPolicyAccessory
    NSApplication.sharedApplication().setActivationPolicy_(NSApplicationActivationPolicyAccessory)


class TrayIcon:
    """The tray thread sends commands; only Tk's thread touches widgets."""

    def __init__(self, commands: SimpleQueue) -> None:
        self._started = False
        image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((4, 4, 60, 60), radius=18, fill=theme.ACCENT,
                               outline=theme.BORDER, width=3)
        draw.ellipse((20, 22, 25, 28), fill=theme.TEXT)
        draw.ellipse((39, 22, 44, 28), fill=theme.TEXT)
        draw.arc((18, 24, 46, 46), 10, 170, fill=theme.TEXT, width=3)

        def command(name):
            return lambda icon, item: commands.put(name)

        self.icon = pystray.Icon(
            "FloatingLinkDock", image, "常用网址 · 单击显示",
            pystray.Menu(
                pystray.MenuItem("显示网址", command("show"), default=True),
                pystray.MenuItem("重置位置", command("reset")),
                pystray.MenuItem("退出", command("quit")),
            ),
        )

    def start(self) -> None:
        if self._started:
            return
        if sys.platform == 'darwin':
            # Tk promotes even LSUIElement bundles to regular applications.
            # Restore menu-bar-only mode after Tk has initialized NSApplication.
            _set_macos_accessory_policy()
            # pystray's default setup shows the icon from a worker thread.
            # Cocoa must instead be updated on Tk's main thread.
            self.icon.run_detached(setup=lambda icon: None)
            self.icon.visible = True
        else:
            self.icon.run_detached()
        self._started = True

    def stop(self) -> None:
        if self._started:
            self.icon.visible = False
            self.icon.stop()
            self._started = False
