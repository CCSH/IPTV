# 直播源&EPG网络采集工具

轻量的直播源、EPG电子节目指南网络采集同步工具，自动拉取公开资源并格式化输出，适配IPTV/电视盒子等常用场景。

## 📁 文件下载
### 直播源
| 格式 | 完整 | 精简 | 其他 |
| ---- | ---- | ---- | ---- |
| txt | [live.txt](https://raw.githubusercontent.com/CCSH/IPTV/refs/heads/main/live.txt) | [live_lite.txt](https://raw.githubusercontent.com/CCSH/IPTV/refs/heads/main/live_lite.txt) | [other.txt](https://raw.githubusercontent.com/CCSH/IPTV/refs/heads/main/others.txt) |
| m3u | [live.m3u](https://raw.githubusercontent.com/CCSH/IPTV/refs/heads/main/live.m3u) | [live_lite.m3u](https://raw.githubusercontent.com/CCSH/IPTV/refs/heads/main/live_lite.m3u) | - |

### EPG
| 格式 | 下载链接 |
| ---- | ---- |
| XML | [e.xml](https://raw.githubusercontent.com/CCSH/IPTV/refs/heads/main/e.xml) |
| GZ | [e.xml.gz](https://raw.githubusercontent.com/CCSH/IPTV/refs/heads/main/e.xml.gz) |

## 🔄 自动更新说明（北京时间）
| 文件类型 | 更新频率 |
| ---- | ---- |
| 直播源 | 每日 0 点更新一次 ✅ |
| 黑白名单 | 每周四 4 点更新一次 ✅ |
| EPG | 从 0:30 开始每 4 小时更新一次 ✅ |

## ✨ 功能说明
- 定时采集公开直播源/EPG数据，自动更新本地文件
- 多源容错，主源失效自动切换备用源
- 支持数据压缩，减少存储与传输体积
- 提供 GitHub Actions 自动更新工作流，无需本地部署

## 🚀 快速使用
1. Fork 本仓库到个人 GitHub 账号
2. 启用仓库的 GitHub Actions 功能（仓库 → Actions → I understand my workflows, go ahead and enable them）
3. 自动按配置定时更新，也可在 Actions 页面手动触发工作流
4. 直接调用仓库中的 `e.xml`/`e.xml.gz` 或直播源文件使用

## ⚠️ 免责声明
本项目为**纯技术开源工具**，仅用于个人技术研究、学习与非商业交流，**严禁任何商业用途**。
项目不存储、不制作、不修改任何直播流及 EPG 数据，所有内容均来自互联网公开可访问资源，相关版权归原始提供方/广播电视机构所有。
开发者按**现状**提供本工具，不保证数据的可用性、准确性、时效性及功能稳定性，第三方源变更、网络问题等导致的功能异常，开发者无义务提供兜底维护。
使用者需自行确保使用行为符合所在地区法律法规，因违规使用、恶意采集本工具引发的任何法律纠纷、经济损失、行政处罚，均由使用者自行承担全部责任，与项目开发者无关。
使用本项目即表示你已充分阅读、理解并自愿接受本声明全部条款，若不同意则请勿下载、安装、使用本项目任何代码及资源。

## 📜 许可证
MIT License © [CCSH]
