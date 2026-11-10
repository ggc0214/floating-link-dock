# Apple Silicon 工作场景版交接

先读 README.md。工作场景版使用 launcher_scenes.py，常用网址版使用 launcher.py。Windows 和 Mac 分别使用对应的系统集成。

- 使用独立的 arm64 Python 虚拟环境，安装 requirements-dev.txt。先检查 Tk 能在登录桌面运行，再执行 `PYTHON=.venv/bin/python bash scripts/build_macos.sh --scenes`。
- Windows 上可验证数据隔离、路径校验和打包配置。Mac 上还需验证窗口首次展开、菜单栏、重复启动、应用选择器、实际文件关联和 NAS 文件夹打开。验收请使用示例配置。
- 保留原常用网址版和 Windows 入口。只提交源码和公开示例。不要导出个人配置、账号或凭据，也不要在没有明确授权时推送、发布或使用 Apple 签名凭据。
