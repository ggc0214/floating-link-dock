from queue import SimpleQueue

from PIL import Image, ImageDraw
import pystray


class TrayIcon:
    """The tray thread sends commands; only Tk's thread touches widgets."""

    def __init__(self, commands: SimpleQueue) -> None:
        image = Image.new("RGBA", (64, 64), "#151A1F")
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((6, 6, 58, 58), radius=14, fill="#61D6C6")
        draw.line((22, 42, 42, 22), fill="#151A1F", width=5)
        draw.line((25, 22, 42, 22, 42, 39), fill="#151A1F", width=5)

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
        self.icon.run_detached()

    def stop(self) -> None:
        self.icon.stop()
