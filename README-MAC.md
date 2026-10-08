# 在 Mac 上继续这个项目

这是最新源码交接目录。本机已生成Mac验收应用，详见 `docs/macos/交付状态.md`。当前安装包最低要求macOS 26，尚未完成全部人工与第二台Mac验收。

1. 把整个 ZIP 传到 M 系列 Mac，双击解压。
2. 在 Mac 的 Codex 中打开解压后的 `xuanfu-mac` 文件夹（不是 ZIP，也不是里面的 src 文件夹）。
3. 新建聊天，发送下面这句话：

> 请先阅读根目录 AGENTS.md 和 docs/macos/交付状态.md，继续已批准的 Mac 版本实施。在本机完成测试、构建 .app 和 ZIP，并验证原生交互。保留 Windows 功能，不擅自推送或发布；需要我手动验收的地方告诉我。

根目录 AGENTS.md 已包含交接边界，Codex 不必依赖之前 Windows 的聊天记录。完整方案、计划、审查修复记录和使用说明都在 docs 中。

目标 macOS 13 或以上、Apple Silicon，实际最低版本需实测。构建需要 arm64 Python 3.11 或以上和 Tk；请让 Codex先检查环境，在项目虚拟环境中安装依赖。

本机构建输出 `dist/macos-arm64/FloatingLinkDock.app` 和 `FloatingLinkDock-macos-arm64.zip`，采用本地临时签名，未做Apple公证。源码ZIP仍不能直接作为应用运行。
