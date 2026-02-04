# <a id="top"></a>📺 直播源 & 台标 & EPG 网络采集工具

一个免费、轻量、全自动化的直播源、台标 Logo 与 EPG 电子节目指南网络采集同步工具。自动拉取并整合互联网公开资源，格式化输出，适配 IPTV、电视盒子、手机直播 APP 等主流使用场景。

---

## 📁 资源直链（直接调用）

>使用不了直链的搜下GitHub代理加速

### 直播源 (Live Channels)
支持 TXT 和 M3U 两种格式，提供完整版、精简版、直播平台轮博及其他未收入频道版本。

| 格式 | 完整版（含地方台等） | 精简版（不含地方台等） | 直播平台（虎牙、斗鱼、B站、YY） | 其他未收入频道 |
| :--- | :--- | :--- | :--- | :--- |
| **TXT** | [live.txt](https://raw.githubusercontent.com/CCSH/IPTV/refs/heads/main/live.txt) | [live_lite.txt](https://raw.githubusercontent.com/CCSH/IPTV/refs/heads/main/live_lite.txt) | — | [others.txt](https://raw.githubusercontent.com/CCSH/IPTV/refs/heads/main/others.txt) |
| **M3U** | [live.m3u](https://raw.githubusercontent.com/CCSH/IPTV/refs/heads/main/live.m3u) | [live_lite.m3u](https://raw.githubusercontent.com/CCSH/IPTV/refs/heads/main/live_lite.m3u) | [live_platforms.m3u](https://raw.githubusercontent.com/CCSH/IPTV/refs/heads/main/live_platforms.m3u) | — |

### EPG 电子节目指南
提供原始 XML 和压缩 GZ 双版本，压缩版体积更小，适合网络调用。

| 格式 | 直链地址 | 核心特点 |
| :--- | :--- | :--- |
| **XML** | [e.xml](https://raw.githubusercontent.com/CCSH/IPTV/refs/heads/main/e.xml) | 原始格式，兼容性最佳，适配所有播放器 |
| **GZ** | [e.xml.gz](https://raw.githubusercontent.com/CCSH/IPTV/refs/heads/main/e.xml.gz) | 压缩格式，体积大幅减小，传输更快 |

### 台标 LOGO
采用标准化命名规则，与直播源频道名一一对应，可直接在播放器中自动加载显示。

**调用格式：**
```
https://raw.githubusercontent.com/CCSH/IPTV/refs/heads/main/logo/{频道名}.png
```

**调用示例：**
- 央视一套 → `https://raw.githubusercontent.com/CCSH/IPTV/refs/heads/main/logo/CCTV1.png`
- 湖南卫视 → `https://raw.githubusercontent.com/CCSH/IPTV/refs/heads/main/logo/湖南卫视.png`

**覆盖范围：** 央视全频道、省级卫视、主流地方频道、数字付费频道、特色网络频道等。

---

## 🔄 自动更新说明（北京时间）
所有资源均由 GitHub Actions 全自动更新，无需手动干预。

| 文件类型 | 更新频率 | 更新说明 |
| :--- | :--- | :--- |
| **直播源** | 每日 04:00 更新一次 ✅ | 同步最新可用直播链路， 整理收集合并|
| **黑白名单** | 每周五 00:00 更新一次 ✅ | 测速现有直播源，自动检测并剔除失效源 |
| **EPG 节目单** | 每日 00:30 开始，每 4 小时更新一次 ✅ | 高频更新，确保节目信息准确及时 |
| **台标 LOGO** | 每周五 08:00 更新一次 ✅ | 同步新增频道台标，修复失效链接，补充高清图标 |
| **直播平台** | 每日 00:15 开始，每 2 小时更新一次 ✅ | 直播平台（虎牙、斗鱼、B站、YY）轮播整理收集合并 |

---

## ✨ 核心功能
- 🤖 **全自动化运维**：基于 GitHub Actions 实现定时采集、校验、更新与发布，零部署成本，无需人工干预。
- 🎯 **多源容错机制**：主数据源失效时自动切换备用源，显著提升资源整体可用性。
- 📦 **数据优化处理**：自动格式化直播源、压缩 EPG 文件，减少存储与传输开销。
- 📱 **多端无缝适配**：输出格式兼容 IPTV 电视盒子（如 TiviMate）、手机直播 APP、电脑播放器及投屏工具。
- 🧹 **智能清理维护**：定期检测并清理失效直播链路、空文件及无效台标，自动补充替代资源。
- ⚡ **极速直链调用**：支持 GitHub Raw 地址直接调用，无需下载到本地，复制链接即可使用。

---

## 🚀 快速开始

### 方式一：直接调用（推荐，零配置）
无需部署，复制链接到播放器即可使用。

1.  **添加直播源**：
    - 打开你的 IPTV 播放器（如 TiviMate, Perfect Player, 电视家等）。
    - 在源设置中，粘贴 `live.m3u` 或 `live.txt` 的直链地址。
2.  **配置 EPG 节目单**：
    - 在播放器的 EPG 设置中，粘贴 `e.xml` 或 `e.xml.gz` 的直链地址。
3.  **启用台标**：
    - 播放器会根据频道名称自动匹配上述台标规则，通常无需额外设置即可显示。

### 方式二：Fork 仓库自用（支持自定义）
适合需要个性化定制的用户。

1.  **Fork 仓库**：点击本页右上角的 **Fork** 按钮，将仓库复制到你的 GitHub 账户下。
2.  **启用 Actions**：
    - 进入你 Fork 的仓库。
    - 点击顶部 **Actions** 标签页。
    - 点击 **“I understand my workflows, go ahead and enable them”** 以启用自动化工作流。
3.  **自定义配置**（可选）：
    - 修改 `.github/workflows/` 目录下的 YAML 文件，可以调整更新频率、添加自定义数据源等。
4.  **使用自有资源**：
    - 将资源链接中的 `CCSH/IPTV` 替换为 `你的用户名/IPTV` 即可调用自己仓库的资源。
5.  **手动触发更新**：
    - 在 **Actions** 页面，选择对应的工作流，点击 **Run workflow** 可随时手动更新。

---

## ⚠️ 免责声明

1.  **项目性质**：本项目为**纯技术开源工具**，仅用于个人技术研究、学习与非商业交流，**严禁任何商业用途**。
2.  **数据来源**：项目本身不存储、不制作、不修改任何直播流及 EPG 数据。所有内容均来自互联网公开可访问的资源，相关版权归原始提供方或广播电视机构所有。
3.  **无责任担保**：开发者按 **“现状”** 提供本工具，不保证数据的可用性、准确性、时效性及功能稳定性。对于因第三方源变更、网络问题等导致的功能异常，开发者无义务提供兜底维护。
4.  **使用者责任**：使用者需自行确保使用行为符合所在国家/地区的法律法规。因违规使用、恶意采集本工具引发的任何法律纠纷、经济损失或行政处罚，均由使用者自行承担全部责任，与项目开发者无关。
5.  **接受条款**：使用本项目即表示您已充分阅读、理解并自愿接受本声明全部条款。若不同意，请勿下载、安装或使用本项目的任何代码及资源。

---

## 📜 开源许可证
本项目基于 **MIT License** 开源。
© CCSH

---

## 🎁 支持与赞赏
如果这个工具对您有帮助，并希望支持项目的持续维护与优化，欢迎通过下方的赞赏码给予鼓励。感谢您的认可！

![赞赏码](https://raw.githubusercontent.com/CCSH/CCSH/refs/heads/main/ccsh.png)

---
**祝您使用愉快！** 

<a href="#top">
    <img src="https://img.shields.io/badge/-返回顶部-orange.svg" alt="#" align="right">
</a>
