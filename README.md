## 更新频率(北京时间)
|直播源|黑白名单|
| ---- | ---- |
|每日4点|每周五0点|

## 直播源
||完整|精简|其他|
| ---- | ---- | ---- | ---- |
|txt|[live.txt](https://raw.githubusercontent.com/CCSH/IPTV/refs/heads/main/live.txt)|[live_lite.txt](https://raw.githubusercontent.com/CCSH/IPTV/refs/heads/main/live_lite.txt)|[other.txt](https://raw.githubusercontent.com/CCSH/IPTV/refs/heads/main/others.txt)
|m3u|[live.m3u](https://raw.githubusercontent.com/CCSH/IPTV/refs/heads/main/live.m3u)|[live_lite.m3u](https://raw.githubusercontent.com/CCSH/IPTV/refs/heads/main/live_lite.m3u)||

## EPG
|xml|gz|
| ---- | ---- |
|[XML](https://raw.githubusercontent.com/CCSH/IPTV/refs/heads/main/e.xml)|[GZ](https://raw.githubusercontent.com/CCSH/IPTV/refs/heads/main/e.xml.gz)|

## 自动更新说明
本仓库的 EPG 核心文件（e.xml / e.xml.gz）由 GitHub Actions 实现全自动定时更新，更新规则如下：

✅ 更新频率：每 6 小时更新一次

✅ 北京时间：UTC+8 小时，即每日8:30、14:30、20:30、次日 2:30
>EPG来自 https://epg.112114.xyz/
