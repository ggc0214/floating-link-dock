import traceback
from datetime import datetime

from .storage import StoragePaths
from .platform_integration import show_startup_error


def report_error(exc: BaseException, parent=None, *, root=None) -> None:
    log = (root if root is not None else StoragePaths.for_user().root) / "errors.log"
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
        if log.exists() and log.stat().st_size > 1_000_000:
            log.replace(log.with_suffix(".previous.log"))
        with log.open("a", encoding="utf-8") as stream:
            stream.write(f"\n{datetime.now().isoformat()}\n")
            traceback.print_exception(type(exc), exc, exc.__traceback__, file=stream)
        message = f"程序遇到错误：{exc}\n\n错误记录：{log}"
    except OSError:
        message = f"程序遇到错误：{exc}\n无法写入错误记录，请检查磁盘或目录权限。"
    if parent is not None:
        from tkinter import messagebox
        messagebox.showerror("常用网址 · 错误", message, parent=parent)
    else:
        show_startup_error(message)
