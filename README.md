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
本仓库的 EPG 文件（e.xml / e.xml.gz）会通过 GitHub Actions 定时自动更新，更新时间为每天的 16:15、18:15、20:15、22:15、00:15、02:15、04:15、06:15、08:15、10:15、12:15、14:15（UTC 时间，对应北京时间 +8 小时）。
>EPG来自 https://epg.112114.xyz/
