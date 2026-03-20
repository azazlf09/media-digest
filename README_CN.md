# MediaDigest v3.0 中文说明

> 🌐 [English README](README.md)

<p align="center">
  <strong>通用视频内容摘要工具</strong><br>
  下载 • 转写 • 总结<br>
  <em>YouTube • B站 • X/Twitter</em>
</p>

---

## 这是什么？

MediaDigest 可以从 YouTube、B站、X/Twitter 下载视频音频，用 Whisper 在本地转写为文字（不花钱！），然后生成结构化摘要。

还支持频道监控——自动检查 YouTube 和 B站的频道是否有新内容。

### 核心特性

- 🌍 **多平台** — YouTube、B站、X/Twitter 一个工具搞定
- 💰 **零 API 费用** — 本地 Whisper 转写，不用云服务
- 🍪 **智能 Cookie 重试** — 自动检测登录要求，本地用户自动从浏览器读取 Cookie
- 📺 **频道监控** — 添加 YouTube/B站频道，自动检查新视频
- 🐳 **Docker 就绪** — 支持 Cookie 文件挂载和专用安装脚本
- 🔄 **V2 平滑迁移** — 从 channel-monitor v2.0 无缝升级

---

## 快速开始

### 方式一：本地用户（Windows / Mac / Linux）

```bash
# 1. 克隆项目
git clone https://github.com/azazlf09/media-digest.git
cd media-digest

# 2. 安装依赖
bash setup.sh          # Mac/Linux
setup.bat              # Windows

# 3. 处理一个视频
python3 media_digest.py now "https://www.youtube.com/watch?v=xxxxxx"
```

**需要：** Python 3.11+、yt-dlp、ffmpeg、faster-whisper（安装脚本会自动处理）

### 方式二：Docker 用户

```bash
# 1. 克隆项目
git clone https://github.com/azazlf09/media-digest.git

# 2. 导出浏览器的 Cookie（用于需要登录的视频）
#    推荐使用 Chrome 扩展："Get cookies.txt LOCALLY"
#    按平台保存到对应目录：
#    data/cookies/youtube/cookies.txt
#    data/cookies/bilibili/cookies.txt
#    data/cookies/twitter/cookies.txt

# 3. 运行安装脚本
bash setup-docker.sh

# 4. 处理视频
python3 media_digest.py now "https://www.youtube.com/watch?v=xxxxxx"
```

### 方式三：OpenClaw 用户

```bash
# 将整个 media-digest/ 文件夹放到 skills/ 目录下
# AI 会自动识别，你只需要发送视频链接即可

# 也可以设置频道监控
python3 skills/media-digest/media_digest.py add "https://youtube.com/@频道名" "我的频道"
python3 skills/media-digest/media_digest.py check 5
```

---

## 使用方法

### 处理单个视频

```bash
python3 media_digest.py now "https://www.youtube.com/watch?v=xxxxxx"
python3 media_digest.py now "https://www.bilibili.com/video/BVxxxxxx"
python3 media_digest.py now "https://x.com/用户名/status/推文ID"
```

### 频道管理

```bash
# 添加频道
python3 media_digest.py add "https://youtube.com/@频道名" "频道别名"
python3 media_digest.py add "https://space.bilibili.com/12345" "UP主名"

# 查看已添加的频道
python3 media_digest.py list

# 检查频道最新视频（最新5个）
python3 media_digest.py check 5

# 移除频道
python3 media_digest.py remove "频道别名"
```

### 查看历史

```bash
# 查看最近的摘要
python3 media_digest.py latest 10

# 生成文字报告
python3 media_digest.py report
```

### 工具命令

```bash
# 检查依赖是否安装
python3 media_digest.py deps

# 从 v2.0 迁移数据
python3 media_digest.py migrate "/旧版本/channel-monitor路径"
```

---

## 支持的平台

| 平台 | 单视频处理 | 频道监控 | 备注 |
|------|-----------|---------|------|
| YouTube | ✅ | ✅ | 优先使用字幕，比Whisper更快更准 |
| B站 | ✅ | ✅ | 大部分视频无需登录 |
| X/Twitter | ✅ | ❌ | 仅支持单链接，需Cookie |

> X/Twitter 不支持自动监控频道，因为 X API 限制。你可以手动发送推文链接来处理。

---

## Cookie 说明

**什么时候需要 Cookie？**

- YouTube：大多数视频**不需要**
- B站：公开视频**不需要**，会员视频需要
- X/Twitter：**必须需要** Cookie

**本地用户（Windows/Mac/Linux）：**
不需要手动操作！遇到需要登录的视频，工具会自动从你的 Chrome/Edge/Firefox 浏览器读取 Cookie。你只需要在浏览器里登录过对应网站就行。

**Docker 用户：**
需要手动导出 Cookie 文件：
1. 安装 Chrome 扩展：[Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
2. 在浏览器中打开对应网站并登录
3. 点击扩展图标，导出 Netscape 格式
4. 保存到 `data/cookies/{平台}/cookies.txt`（平台名：youtube、bilibili、twitter）

---

## 首次运行提示

⚠️ **首次运行 Whisper 转写时会自动下载模型文件：**
- `base` 模型：约 140MB（中文识别一般，速度快）
- `large-v3` 模型：约 3GB（中文识别优秀，速度慢）

模型只需下载一次，之后会自动缓存。

---

## 项目结构

```
media-digest/
├── media_digest.py          # 主程序入口
├── setup.sh                 # Linux/Mac 安装脚本
├── setup.bat                # Windows 安装脚本
├── setup-docker.sh          # Docker 安装脚本
├── core/
│   ├── downloader.py        # 统一下载（自动Cookie重试）
│   ├── platform.py          # 平台识别（URL判断）
│   ├── transcriber.py       # Whisper 转写 + 字幕提取
│   ├── monitor.py           # 频道监控 + 全流程管道
│   ├── deps.py              # 依赖检查
│   └── config.py            # 配置管理
├── data/
│   ├── channels.json        # 关注的频道列表
│   ├── processed.json       # 已处理视频记录
│   ├── summaries/           # 摘要输出目录
│   └── cookies/             # Cookie 文件目录
├── tools/
│   ├── cookie_helper.py     # Cookie 导出辅助工具
│   └── cookie_helper.bat    # Windows Cookie 辅助
├── SKILL.md                 # OpenClaw Skill 定义
├── README.md                # 英文说明
├── README_CN.md             # 中文说明（本文件）
└── LICENSE                  # MIT 开源协议
```

---

## 常见问题

**Q: 视频下载失败怎么办？**
A: 先运行 `python3 media_digest.py deps` 检查依赖。如果是登录限制，本地用户确保浏览器已登录对应网站，Docker 用户检查 Cookie 文件是否正确。

**Q: 转写结果不准确怎么办？**
A: 默认使用 `base` 模型。如需更高精度，修改 `core/transcriber.py` 中的模型名称为 `large-v3`。

**Q: 支持哪些语言？**
A: Whisper 支持 99 种语言，包括中文、英文、日文、韩文等，会自动检测。

**Q: 数据存在哪里？**
A: 所有数据存在 `data/` 目录下，包括频道列表、已处理记录和摘要文件。

---

## 开源协议

[MIT License](LICENSE) — 随便用，随便改，开心就好 😊

---

## 作者

🦐 **鼠鼠虾** & **鼠哥**

由 OpenClaw 驱动，AI 辅助开发。
