import urllib.request
from urllib.parse import quote, unquote
import re
import os
from datetime import datetime, timedelta, timezone
import opencc

# ===================== 全局核心配置 =====================
# 指定按TXT文件内顺序排列的分类，其余自动字典序排序，按需增删
ORDERED_CHANNEL_TYPES = ["央视频道", "卫视频道", "港澳台", "电影频道", "电视剧频道", "综艺频道", "NewTV"]
# 频道名称清理字符集
REMOVAL_LIST = [
    "「IPV4」", "「IPV6」", "[ipv6]", "[ipv4]", "_电信", "电信", "（HD）", "[超清]",
    "高清", "超清", "-HD", "(HK)", "AKtv", "@", "IPV6", "🎞️", "🎦", " ",
    "[BD]", "[VGA]", "[HD]", "[SD]", "(1080p)", "(720p)", "(480p)"
]
# 网络请求配置
USER_AGENT = "PostmanRuntime-ApipostRuntime/1.1.0"
URL_FETCH_TIMEOUT = 10
# 白名单测速阈值(ms)
RESPONSE_TIME_THRESHOLD = 2000
# M3U相关配置
TVG_URL = "https://github.com/CCSH/IPTV/raw/refs/heads/main/e.xml.gz"
LOGO_URL_TPL = "https://raw.githubusercontent.com/CCSH/IPTV/refs/heads/main/logo/{}.png"

# ===================== 通用工具函数 =====================
def get_project_dirs() -> dict:
    script_abspath = os.path.abspath(__file__)
    root_dir = os.path.dirname(script_abspath)
    return {
        "root": root_dir,
        "blacklist_auto": os.path.join(root_dir, "assets/whitelist-blacklist/blacklist_auto.txt"),
        "blacklist_manual": os.path.join(root_dir, "assets/whitelist-blacklist/blacklist_manual.txt"),
        "whitelist_manual": os.path.join(root_dir, "assets/whitelist-blacklist/whitelist_manual.txt"),
        "whitelist_auto": os.path.join(root_dir, "assets/whitelist-blacklist/whitelist_auto.txt"),
        "blackhost_count": os.path.join(root_dir, "assets/whitelist-blacklist/blackhost_count.txt"),
        "corrections_name": os.path.join(root_dir, "assets/corrections_name.txt"),
        "urls": os.path.join(root_dir, "assets/urls.txt"),
        "main_channel": os.path.join(root_dir, "主频道"),
        "local_channel": os.path.join(root_dir, "地方台")
    }

def read_txt(file_path: str, strip: bool = True, skip_empty: bool = True) -> list:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if strip:
                lines = [line.strip() for line in lines]
            if skip_empty:
                lines = [line for line in lines if line]
            return lines
    except FileNotFoundError:
        print(f"[ERROR] 文件未找到: {file_path}")
        return []
    except Exception as e:
        print(f"[ERROR] 读取文件 {file_path} 失败: {str(e)}")
        return []

def write_txt(file_path: str, data: list or str) -> None:
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        if isinstance(data, list):
            data = '\n'.join([str(line) for line in data])
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(data)
        print(f"[SUCCESS] 文件写入成功: {os.path.basename(file_path)}")
    except Exception as e:
        print(f"[ERROR] 写入文件 {file_path} 失败: {str(e)}")

def safe_quote_url(url: str) -> str:
    try:
        unquoted = unquote(url)
        return quote(unquoted, safe=':/?&=')
    except Exception:
        return url

def traditional_to_simplified(text: str) -> str:
    if not hasattr(traditional_to_simplified, "converter"):
        traditional_to_simplified.converter = opencc.OpenCC('t2s')
    return traditional_to_simplified.converter.convert(text) if text else ""

# ===================== 黑名单/纠错字典处理 =====================
def load_blacklist(blacklist_auto_path: str, blacklist_manual_path: str) -> set:
    def _extract_black_urls(file_path):
        lines = read_txt(file_path)
        urls = []
        for line in lines:
            if "," in line:
                url = line.split(',')[1].strip()
                if url:
                    urls.append(url)
        return urls
    auto_urls = _extract_black_urls(blacklist_auto_path)
    manual_urls = _extract_black_urls(blacklist_manual_path)
    combined = set(auto_urls + manual_urls)
    print(f"[INFO] 合并黑名单URL数: {len(combined)}")
    return combined

def load_corrections(corrections_path: str) -> dict:
    corrections = {}
    lines = read_txt(corrections_path)
    for line in lines:
        if not line or "," not in line:
            continue
        parts = line.split(',')
        correct_name = parts[0].strip()
        for wrong_name in parts[1:]:
            wrong_name = wrong_name.strip()
            if wrong_name:
                corrections[wrong_name] = correct_name
    print(f"[INFO] 加载频道纠错规则数: {len(corrections)}")
    return corrections

# ===================== 频道名称/URL处理 =====================
def clean_channel_name(name: str) -> str:
    if not name:
        return ""
    for item in REMOVAL_LIST:
        name = name.replace(item, "")
    name = name.replace("CCTV-", "CCTV")
    name = name.replace("CCTV0", "CCTV")
    name = name.replace("PLUS", "+")
    name = name.replace("NewTV-", "NewTV")
    name = name.replace("iHOT-", "iHOT")
    name = name.replace("NEW", "New")
    name = name.replace("New_", "New")
    return name.strip()

def clean_url(url: str) -> str:
    if not url:
        return ""
    dollar_idx = url.rfind('$')
    return url[:dollar_idx].strip() if dollar_idx != -1 else url.strip()

def correct_channel_name(name: str, corrections: dict) -> str:
    if not name or name not in corrections:
        return name
    return corrections[name] if corrections[name] != name else name

# ===================== 频道字典加载 =====================
def load_channel_dictionaries(main_dir: str, local_dir: str) -> tuple[dict, dict, list]:
    main_channels = {
        "央视频道": "央视频道.txt", "卫视频道": "卫视频道.txt", "体育频道": "体育频道.txt",
        "电影频道": "电影.txt", "电视剧频道": "电视剧.txt", "港澳台": "港澳台.txt",
        "国际台": "国际台.txt", "纪录片": "纪录片.txt", "戏曲频道": "戏曲频道.txt",
        "解说频道": "解说频道.txt", "春晚": "春晚.txt", "NewTV": "NewTV.txt",
        "iHOT": "iHOT.txt", "儿童频道": "儿童频道.txt", "综艺频道": "综艺频道.txt",
        "埋堆堆": "埋堆堆.txt", "音乐频道": "音乐频道.txt", "游戏频道": "游戏频道.txt",
        "收音机频道": "收音机频道.txt", "直播中国": "直播中国.txt", "MTV": "MTV.txt",
        "咪咕直播": "咪咕直播.txt"
    }
    local_channels = {
        "上海频道": "上海频道.txt", "浙江频道": "浙江频道.txt", "江苏频道": "江苏频道.txt",
        "广东频道": "广东频道.txt", "湖南频道": "湖南频道.txt", "安徽频道": "安徽频道.txt",
        "海南频道": "海南频道.txt", "内蒙频道": "内蒙频道.txt", "湖北频道": "湖北频道.txt",
        "辽宁频道": "辽宁频道.txt", "陕西频道": "陕西频道.txt", "山西频道": "山西频道.txt",
        "山东频道": "山东频道.txt", "云南频道": "云南频道.txt", "北京频道": "北京频道.txt",
        "重庆频道": "重庆频道.txt", "福建频道": "福建频道.txt", "甘肃频道": "甘肃频道.txt",
        "广西频道": "广西频道.txt", "贵州频道": "贵州频道.txt", "河北频道": "河北频道.txt",
        "河南频道": "河南频道.txt", "黑龙江频道": "黑龙江频道.txt", "吉林频道": "吉林频道.txt",
        "江西频道": "江西频道.txt", "宁夏频道": "宁夏频道.txt", "青海频道": "青海频道.txt",
        "四川频道": "四川频道.txt", "天津频道": "天津频道.txt", "新疆频道": "新疆频道.txt"
    }
    lite_sort = [
        "央视频道", "卫视频道", "港澳台", "电影频道", "电视剧频道", "综艺频道",
        "NewTV", "iHOT", "体育频道", "咪咕直播", "埋堆堆", "音乐频道", "游戏频道", "解说频道"
    ]

    main_dict = {}
    for chn_type, filename in main_channels.items():
        file_path = os.path.join(main_dir, filename)
        lines = read_txt(file_path)
        main_dict[chn_type] = lines
        print(f"[INFO] 加载主频道 {chn_type}: {len(lines)} 个")

    local_dict = {}
    for chn_type, filename in local_channels.items():
        file_path = os.path.join(local_dir, filename)
        lines = read_txt(file_path)
        local_dict[chn_type] = lines
        print(f"[INFO] 加载地方台 {chn_type}: {len(lines)} 个")

    return main_dict, local_dict, lite_sort

# ===================== 频道分类核心 =====================
class ChannelClassifier:
    def __init__(self, main_dict: dict, local_dict: dict, blacklist: set):
        self.main_dict = main_dict
        self.local_dict = local_dict
        self.blacklist = blacklist
        self.channel_data = {}
        self.other_lines = []
        self.other_urls = set()
        self.all_urls = {}
        for chn_type in list(main_dict.keys()) + list(local_dict.keys()):
            self.channel_data[chn_type] = []
            self.all_urls[chn_type] = set()

    def check_url_exist(self, chn_type: str, url: str) -> bool:
        if url in self.all_urls.get(chn_type, set()) or "127.0.0.1" in url:
            return True
        return False

    def add_channel_line(self, chn_type: str, line: str, url: str):
        self.channel_data[chn_type].append(line)
        self.all_urls[chn_type].add(url)

    def add_other_line(self, line: str, url: str):
        if url not in self.other_urls and url not in self.blacklist:
            self.other_urls.add(url)
            self.other_lines.append(line)

    def classify(self, channel_name: str, channel_url: str, line: str):
        if channel_url in self.blacklist or not channel_url:
            return
        for chn_type, chn_names in self.main_dict.items():
            if channel_name in chn_names and not self.check_url_exist(chn_type, channel_url):
                self.add_channel_line(chn_type, line, channel_url)
                return
        for chn_type, chn_names in self.local_dict.items():
            if channel_name in chn_names and not self.check_url_exist(chn_type, channel_url):
                self.add_channel_line(chn_type, line, channel_url)
                return
        self.add_other_line(line, channel_url)

    def get_channel_data(self, chn_type: str) -> list:
        return self.channel_data.get(chn_type, [])

    def get_all_other(self) -> list:
        return self.other_lines

# ===================== 数据处理与生成 =====================
def is_m3u_content(text: str) -> bool:
    if not text:
        return False
    first_line = text.strip().splitlines()[0].strip()
    return first_line.startswith("#EXTM3U")

def convert_m3u_to_txt(m3u_content: str) -> list:
    lines = [line.strip() for line in m3u_content.split('\n') if line.strip()]
    txt_lines, channel_name = [], ""
    for line in lines:
        if line.startswith("#EXTM3U"):
            continue
        elif line.startswith("#EXTINF"):
            channel_name = line.split(',')[-1].strip()
        elif line.startswith(("http", "rtmp", "p3p")):
            if channel_name:
                txt_lines.append(f"{channel_name},{line}")
        elif "#genre#" not in line and "," in line and "://" in line:
            if re.match(r'^[^,]+,[^\s]+://[^\s]+$', line):
                txt_lines.append(line)
    return txt_lines

def process_remote_url(url: str, classifier: ChannelClassifier, corrections: dict):
    print(f"[PROCESS] 拉取远程源: {url}")
    classifier.other_lines.append(f"{url},#genre#")
    try:
        headers = {'User-Agent': USER_AGENT}
        req = urllib.request.Request(safe_quote_url(url), headers=headers)
        with urllib.request.urlopen(req, timeout=URL_FETCH_TIMEOUT) as resp:
            data = resp.read()
            text = None
            for encoding in ['utf-8', 'gbk', 'gb2312', 'iso-8859-1']:
                try:
                    text = data.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            if not text:
                print(f"[ERROR] 远程源 {url} 解码失败")
                return
            if is_m3u_content(text):
                lines = convert_m3u_to_txt(text)
            else:
                lines = [line.strip() for line in text.split('\n') if line.strip()]
        print(f"[PROCESS] 远程源 {url} 提取有效行: {len(lines)}")
        for line in lines:
            process_single_line(line, classifier, corrections)
        classifier.other_lines.append('\n')
    except Exception as e:
        print(f"[ERROR] 处理远程源 {url} 失败: {str(e)}")

def process_single_line(line: str, classifier: ChannelClassifier, corrections: dict):
    if "#genre#" in line or "#EXTINF:" in line or "," not in line or "://" not in line:
        return
    try:
        channel_name, channel_address = line.split(',', 1)
    except ValueError:
        return
    channel_name = traditional_to_simplified(channel_name)
    channel_name = clean_channel_name(channel_name)
    channel_name = correct_channel_name(channel_name, corrections)
    channel_address = clean_url(channel_address)
    new_line = f"{channel_name},{channel_address}"
    classifier.classify(channel_name, channel_address, new_line)

def sort_channel_data(channel_data: list, chn_type: str, cfg_list: list) -> list:
    if not channel_data:
        return channel_data
    
    if chn_type in ORDERED_CHANNEL_TYPES:
        cfg_index_map = {cfg_name: idx for idx, cfg_name in enumerate(cfg_list)}
        def _ordered_key(line):
            name = line.split(',')[0] if ',' in line else ""
            return cfg_index_map.get(name, len(cfg_list))
        return sorted(channel_data, key=_ordered_key)
    else:
        def _dict_key(line):
            name = line.split(',')[0] if ',' in line else ""
            pure_name = re.sub(r'[^\w\u4e00-\u9fff]', '', name)
            return pure_name if pure_name else name
        return sorted(channel_data, key=_dict_key)

def generate_live_text(classifier: ChannelClassifier, main_dict: dict, lite_sort: list) -> tuple[list, list]:
    bj_time = datetime.now(timezone.utc) + timedelta(hours=8)
    formatted_time = bj_time.strftime("%Y%m%d %H:%M")
    version = f"{formatted_time},https://gcalic.v.myalicdn.com/gc/wgw05_1/index.m3u8?contentid=2820180516001"
    header = ["更新时间,#genre#", version, '\n']

    lite_lines = header.copy()
    for chn_type in lite_sort:
        chn_data = classifier.get_channel_data(chn_type)
        sorted_data = sort_channel_data(chn_data, chn_type, main_dict[chn_type])
        lite_lines += [f"{chn_type},#genre#"] + sorted_data + ['\n']
    lite_lines = lite_lines[:-1] if lite_lines and lite_lines[-1] == '\n' else lite_lines

    full_lines = lite_lines.copy() + ['\n']
    full_other_types = [
        "儿童频道", "国际台", "纪录片", "戏曲频道", "上海频道", "湖南频道",
        "湖北频道", "广东频道", "浙江频道", "山东频道", "江苏频道", "安徽频道",
        "海南频道", "内蒙频道", "辽宁频道", "陕西频道", "山西频道", "云南频道",
        "北京频道", "重庆频道", "福建频道", "甘肃频道", "广西频道", "贵州频道",
        "河北频道", "河南频道", "黑龙江频道", "吉林频道", "江西频道", "宁夏频道",
        "青海频道", "四川频道", "天津频道", "新疆频道", "春晚", "直播中国", "MTV", "收音机频道"
    ]
    for chn_type in full_other_types:
        chn_data = classifier.get_channel_data(chn_type)
        sort_list = main_dict.get(chn_type, []) or classifier.local_dict.get(chn_type, [])
        sorted_data = sort_channel_data(chn_data, chn_type, sort_list)
        full_lines += [f"{chn_type},#genre#"] + sorted_data + ['\n']
    full_lines = full_lines[:-1] if full_lines and full_lines[-1] == '\n' else full_lines

    return full_lines, lite_lines

def make_m3u(txt_file: str, m3u_file: str, tvg_url: str, logo_tpl: str):
    try:
        if not os.path.exists(txt_file):
            print(f"[ERROR] M3U源文件不存在: {txt_file}")
            return
        m3u_content = f"#EXTM3U x-tvg-url=\"{tvg_url}\"\n"
        lines = read_txt(txt_file, strip=True, skip_empty=True)
        group_name = ""
        for line in lines:
            if "," not in line:
                continue
            parts = line.split(',', 1)
            if len(parts) != 2:
                continue
            if "#genre#" in parts[1]:
                group_name = parts[0].strip()
                continue
            channel_name, channel_url = parts[0].strip(), parts[1].strip()
            if not channel_url or "://" not in channel_url:
                continue
            logo_url = logo_tpl.format(channel_name)
            m3u_content += (
                f"#EXTINF:-1  tvg-name=\"{channel_name}\" tvg-logo=\"{logo_url}\"  group-title=\"{group_name}\",{channel_name}\n"
                f"{channel_url}\n"
            )
        write_txt(m3u_file, m3u_content)
    except Exception as e:
        print(f"[ERROR] 生成M3U失败 {m3u_file}: {str(e)}")

# ===================== 主函数执行 =====================
if __name__ == "__main__":
    timestart = datetime.now()
    print(f"[START] 程序开始执行: {timestart.strftime('%Y%m%d %H:%M:%S')}")
    dirs = get_project_dirs()
    
    blacklist = load_blacklist(dirs["blacklist_auto"], dirs["blacklist_manual"])
    corrections = load_corrections(dirs["corrections_name"])
    main_dict, local_dict, lite_sort = load_channel_dictionaries(dirs["main_channel"], dirs["local_channel"])
    classifier = ChannelClassifier(main_dict, local_dict, blacklist)

    print(f"[PROCESS] 处理手动白名单")
    whitelist_manual = read_txt(dirs["whitelist_manual"])
    classifier.other_lines.append("白名单,#genre#")
    for line in whitelist_manual:
        process_single_line(line, classifier, corrections)

    print(f"[PROCESS] 处理自动白名单（响应时间<{RESPONSE_TIME_THRESHOLD}ms）")
    whitelist_auto = read_txt(dirs["whitelist_auto"])
    classifier.other_lines.append("白名单测速,#genre#")
    for line in whitelist_auto:
        if "#genre#" in line or "," not in line or "://" not in line:
            continue
        parts = line.split(",")
        if len(parts) < 2:
            continue
        try:
            resp_time = float(parts[0].replace("ms", ""))
        except ValueError:
            resp_time = 60000
        if resp_time < RESPONSE_TIME_THRESHOLD:
            process_single_line(",".join(parts[1:]), classifier, corrections)

    print(f"[PROCESS] 处理远程URL源")
    urls = read_txt(dirs["urls"])
    for url in urls:
        if url.startswith("http"):
            process_remote_url(url, classifier, corrections)

    print(f"[GENERATE] 生成live.txt/live_lite.txt")
    live_full, live_lite = generate_live_text(classifier, main_dict, lite_sort)
    live_full_path = os.path.join(dirs["root"], "live.txt")
    live_lite_path = os.path.join(dirs["root"], "live_lite.txt")
    others_path = os.path.join(dirs["root"], "others.txt")
    write_txt(live_full_path, live_full)
    write_txt(live_lite_path, live_lite)
    write_txt(others_path, classifier.other_lines)

    print(f"[GENERATE] 生成M3U文件")
    make_m3u(live_full_path, os.path.join(dirs["root"], "live.m3u"), TVG_URL, LOGO_URL_TPL)
    make_m3u(live_lite_path, os.path.join(dirs["root"], "live_lite.m3u"), TVG_URL, LOGO_URL_TPL)

    timeend = datetime.now()
    elapsed = timeend - timestart
    minutes, seconds = int(elapsed.total_seconds() // 60), int(elapsed.total_seconds() % 60)
    blacklist_count = len(blacklist)
    live_count = len(live_full)
    others_count = len(classifier.other_lines)
    
    print("=" * 60)
    print(f"[END] 程序执行完成: {timeend.strftime('%Y%m%d %H:%M:%S')}")
    print(f"[STAT] 执行时间: {minutes} 分 {seconds} 秒")
    print(f"[STAT] 黑名单URL数: {blacklist_count}")
    print(f"[STAT] live.txt行数: {live_count}")
    print(f"[STAT] others.txt行数: {others_count}")
    print("=" * 60)
