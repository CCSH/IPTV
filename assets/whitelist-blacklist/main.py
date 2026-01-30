import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from datetime import datetime, timedelta, timezone
import os
from urllib.parse import quote, unquote, urlparse
import socket
import subprocess
from typing import List, Tuple, Dict, Optional

# ===================== 全局配置（集中管理，方便修改）=====================
TIMEOUT_URL_CHECK = 6  # URL检测超时时间(秒)
TIMEOUT_URL_FETCH = 10  # 远程源拉取超时时间(秒)
MAX_WORKERS = 30  # 线程池最大工作数
USER_AGENT = "PostmanRuntime-ApipostRuntime/1.1.0"  # 统一请求头
# 需要跳过/包含的字符串（集中管理）
SKIP_STRINGS = ['#genre#', '#EXTINF:-1', '"ext"']
REQUIRED_STRINGS = ['://']

# ===================== 通用工具函数 =====================
def read_txt_to_array(file_name: str) -> List[str]:
    """读取文本文件到数组，自动去除首尾空格，处理异常"""
    try:
        with open(file_name, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    except FileNotFoundError:
        print(f"[ERROR] 文件未找到: {file_name}")
        return []
    except Exception as e:
        print(f"[ERROR] 读取文件 {file_name} 失败: {str(e)}")
        return []

def read_txt_file(file_path: str) -> List[str]:
    """按规则过滤读取文本文件：跳过指定字符串 + 必须包含指定字符串"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return [
                line.strip() for line in f
                if line.strip() and not any(s in line for s in SKIP_STRINGS)
                and all(r in line for r in REQUIRED_STRINGS)
            ]
    except Exception as e:
        print(f"[ERROR] 过滤读取文件 {file_path} 失败: {str(e)}")
        return []

def write_list(file_path: str, data_list: List[str]) -> None:
    """写入列表到文件，自动处理目录创建"""
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(data_list))
        print(f"[SUCCESS] 文件已生成: {file_path}")
    except Exception as e:
        print(f"[ERROR] 写入文件 {file_path} 失败: {str(e)}")

def get_host_from_url(url: str) -> str:
    """从URL中提取host，异常返回空字符串"""
    try:
        parsed = urlparse(url)
        return parsed.netloc if parsed.netloc else ""
    except Exception:
        return ""

def safe_quote_url(url: str) -> str:
    """URL安全编解码：先解码再编码，避免重复编码"""
    try:
        unquoted = unquote(url)
        return quote(unquoted, safe=':/?&=')
    except Exception:
        return url

def get_file_dirs() -> Dict[str, str]:
    """统一获取所有文件路径，避免多处硬编码，便于维护"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    parent2_dir = os.path.dirname(parent_dir)
    return {
        "current": current_dir,
        "parent2": parent2_dir,
        # 输入文件
        "urls": os.path.join(parent2_dir, 'urls.txt'),
        "live": os.path.join(parent2_dir, 'live.txt'),
        "blacklist_auto": os.path.join(current_dir, 'blacklist_auto.txt'),
        "others": os.path.join(parent2_dir, 'others.txt'),
        "whitelist_manual": os.path.join(current_dir, 'whitelist_manual.txt'),
        # 输出文件
        "whitelist_auto": os.path.join(current_dir, 'whitelist_auto.txt'),
        "whitelist_auto_tv": os.path.join(current_dir, 'whitelist_auto_tv.txt'),
        "blackhost_count": os.path.join(current_dir, "blackhost_count.txt")
    }

# ===================== URL检测相关函数 =====================
# 黑名单Host统计字典（全局，避免函数内重复定义）
blacklist_host_dict: Dict[str, int] = {}

def record_black_host(host: str) -> None:
    """记录黑名单Host，计数+1"""
    if not host:
        return
    blacklist_host_dict[host] = blacklist_host_dict.get(host, 0) + 1

def check_p3p_url(url: str, timeout: int) -> bool:
    """检测P3P协议URL"""
    try:
        parsed = urlparse(url)
        host, port = parsed.hostname, parsed.port or 80
        if not host or not port:
            return False
        with socket.create_connection((host, port), timeout=timeout) as s:
            request = (
                f"GET {parsed.path or '/'} P3P/1.0\r\n"
                f"Host: {host}\r\n"
                f"User-Agent: {USER_AGENT}\r\n"
                f"Connection: close\r\n\r\n"
            )
            s.sendall(request.encode())
            return b"P3P" in s.recv(1024)
    except Exception:
        return False

def check_p2p_url(url: str, timeout: int) -> bool:
    """检测P2P协议URL（保留原有逻辑，待完善协议）"""
    try:
        parsed = urlparse(url)
        host, port = parsed.hostname, parsed.port
        if not host or not port or not parsed.path:
            return False
        with socket.create_connection((host, port), timeout=timeout) as s:
            request = f"YOUR_CUSTOM_REQUEST {parsed.path}\r\nHost: {host}\r\n\r\n"
            s.sendall(request.encode())
            return b"SOME_EXPECTED_RESPONSE" in s.recv(1024)
    except Exception:
        return False

def check_rtmp_url(url: str, timeout: int) -> bool:
    """检测RTMP/RTSP协议URL，调用ffprobe"""
    try:
        # 屏蔽ffprobe所有输出，仅判断返回码
        subprocess.run(
            ['ffprobe', '-v', 'quiet', url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout
        )
        return True
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, Exception):
        return False

def check_rtp_url(url: str, timeout: int) -> bool:
    """检测RTP协议URL，UDP连接"""
    try:
        parsed = urlparse(url)
        host, port = parsed.hostname, parsed.port
        if not host or not port:
            return False
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(timeout)
            s.connect((host, port))
            s.sendto(b'', (host, port))
            s.recv(1)
        return True
    except (socket.timeout, socket.error, Exception):
        return False

def check_url(url: str, timeout: int = TIMEOUT_URL_CHECK) -> Tuple[Optional[float], bool]:
    """
    统一检测URL是否可访问
    :return: (响应时间(毫秒), 是否有效)
    """
    start_time = time.time()
    try:
        encoded_url = safe_quote_url(url)
        if url.startswith("http"):
            # HTTP/HTTPS协议
            req = urllib.request.Request(encoded_url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                success = resp.status == 200
        elif url.startswith("p3p"):
            success = check_p3p_url(encoded_url, timeout)
        elif url.startswith("p2p"):
            success = check_p2p_url(encoded_url, timeout)
        elif url.startswith(("rtmp", "rtsp")):
            success = check_rtmp_url(encoded_url, timeout)
        elif url.startswith("rtp"):
            success = check_rtp_url(encoded_url, timeout)
        else:
            success = False

        elapsed = (time.time() - start_time) * 1000 if success else None
        return elapsed, success
    except Exception as e:
        # 检测失败记录Host
        record_black_host(get_host_from_url(url))
        return None, False

# ===================== M3U处理相关函数 =====================
def is_m3u_content(text: str) -> bool:
    """判断是否为M3U格式内容"""
    return text.strip().startswith("#EXTM3U") if text else False

def convert_m3u_to_txt(m3u_content: str) -> List[str]:
    """M3U格式转换为 频道名,URL 格式"""
    lines = [line.strip() for line in m3u_content.split('\n') if line.strip()]
    txt_lines, channel_name = [], ""
    for line in lines:
        if line.startswith("#EXTINF"):
            channel_name = line.split(',')[-1].strip()
        elif line.startswith(("http", "rtmp", "rtsp", "p3p", "p2p", "rtp")):
            if channel_name:
                txt_lines.append(f"{channel_name},{line}")
    return txt_lines

def process_remote_url(url: str) -> List[str]:
    """拉取远程URL内容，解析为 频道名,URL 格式（支持M3U和普通文本）"""
    try:
        req = urllib.request.Request(safe_quote_url(url), headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=TIMEOUT_URL_FETCH) as resp:
            text = resp.read().decode('utf-8', errors='ignore')  # 忽略解码错误
            if is_m3u_content(text):
                return convert_m3u_to_txt(text)
            else:
                # 普通文本：过滤有效行
                return [
                    line.strip() for line in text.split('\n')
                    if line.strip() and "#genre#" not in line and "," in line and "://" in line
                ]
    except Exception as e:
        print(f"[ERROR] 拉取远程源失败 {url}: {str(e)}")
        return []

# ===================== 数据清洗相关函数 =====================
def clean_url_dollar(lines: List[str]) -> List[str]:
    """清理URL中的$符号：去掉$及后面的内容"""
    clean_lines = []
    for line in lines:
        if "," in line and "://" in line:
            dollar_idx = line.rfind('$')
            clean_lines.append(line[:dollar_idx] if dollar_idx != -1 else line)
    return clean_lines

def split_url_hash(lines: List[str]) -> List[str]:
    """拆分URL中的#符号（加速源），修复原有BUG"""
    split_lines = []
    for line in lines:
        if "," not in line or "://" not in line:
            continue
        # 仅拆分1次，避免频道名包含,的情况
        channel_name, channel_url = line.split(',', 1)
        if "#" not in channel_url:
            split_lines.append(line)
        else:
            # 拆分#后的所有加速源，逐个添加
            for url in channel_url.split('#'):
                url = url.strip()
                if "://" in url:
                    split_lines.append(f"{channel_name},{url}")
    return split_lines

def remove_duplicates_url(lines: List[str]) -> List[str]:
    """按URL去重，保留首次出现的频道名"""
    url_set, unique_lines = set(), []
    for line in lines:
        if "," in line and "://" in line:
            parts = line.split(',', 1)
            if len(parts) < 2:
                continue
            url = parts[1].strip()
            if url not in url_set:
                url_set.add(url)
                unique_lines.append(line)
    return unique_lines

def extract_whitelist_set(whitelist_lines: List[str]) -> set:
    """从白名单中提取URL集合，用于快速判断"""
    url_set = set()
    for line in whitelist_lines:
        if "," in line and "://" in line:
            parts = line.split(',', 1)
            if len(parts) >= 2:
                url_set.add(parts[1].strip())
    return url_set

# ===================== 多线程处理 =====================
def process_line(line: str, whitelist_set: set) -> Tuple[Optional[float], Optional[str]]:
    """处理单条数据，检测URL，返回（响应时间，原始行）"""
    if not line or "#genre#" in line or "://" not in line:
        return None, None
    line = line.strip()
    if "," not in line:
        return None, None
    
    channel_name, url = line.split(',', 1)
    url = url.strip()
    # 白名单直接通过
    if url in whitelist_set:
        return 0.0, line
    # 检测URL
    elapsed_time, is_valid = check_url(url)
    return (elapsed_time, line) if is_valid else (None, line)

def process_urls_multithreaded(lines: List[str], whitelist_set: set, max_workers: int = MAX_WORKERS) -> Tuple[List[str], List[str]]:
    """多线程处理所有URL，返回（成功列表，黑名单列表）"""
    success_list, black_list = [], []
    if not lines:
        return success_list, black_list
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        futures = {executor.submit(process_line, line, whitelist_set): line for line in lines}
        # 处理完成的任务
        for future in as_completed(futures):
            elapsed_time, result_line = future.result()
            if result_line:
                if elapsed_time is not None:
                    success_list.append(f"{elapsed_time:.2f}ms,{result_line}")
                else:
                    black_list.append(result_line)
    # 排序：成功列表按响应时间升序，黑名单按字符升序
    success_list.sort(key=lambda x: float(x.split(',')[0].replace('ms', '')))
    black_list.sort()
    return success_list, black_list

# ===================== 结果处理 =====================
def generate_output_lines(success_list: List[str], black_list: List[str]) -> Tuple[List[str], List[str], List[str]]:
    """生成带时间戳的输出行，适配原有格式"""
    # 北京时间戳
    bj_time = datetime.now(timezone.utc) + timedelta(hours=8)
    version = f"{bj_time.strftime('%Y%m%d %H:%M')},url"
    # 处理TV版成功列表（去掉响应时间）
    success_tv = [line.split(',', 1)[1] for line in success_list if ',' in line]
    # 构造输出行
    success_output = [
        "更新时间,#genre#", version, '',
        "RespoTime,whitelist,#genre#"
    ] + success_list
    success_tv_output = [
        "更新时间,#genre#", version, '',
        "whitelist,#genre#"
    ] + success_tv
    black_output = [
        "更新时间,#genre#", version, '',
        "blacklist,#genre#"
    ] + black_list
    return success_output, success_tv_output, black_output

def save_blackhost_count(file_path: str) -> None:
    """保存黑名单Host统计结果"""
    if not blacklist_host_dict:
        print("[INFO] 无黑名单Host记录")
        return
    # 按计数降序排序
    sorted_hosts = sorted(blacklist_host_dict.items(), key=lambda x: x[1], reverse=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        for host, count in sorted_hosts:
            f.write(f"{host}: {count}\n")
    print(f"[SUCCESS] 黑名单Host统计已保存: {file_path}")

# ===================== 主函数 =====================
if __name__ == "__main__":
    start_time = datetime.now()
    print(f"[START] 程序开始执行: {start_time.strftime('%Y%m%d %H:%M:%S')}")
    file_dirs = get_file_dirs()
    url_statistics = []  # 远程源统计
    urls_all_lines = []  # 所有待检测的URL行

    # 1. 拉取远程源
    remote_urls = read_txt_to_array(file_dirs["urls"])
    for url in remote_urls:
        if url.startswith("http"):
            print(f"[PROCESS] 拉取远程源: {url}")
            m3u_lines = process_remote_url(url)
            url_statistics.append(f"{len(m3u_lines)},{url.strip()}")
            urls_all_lines.extend(m3u_lines)
            print(f"[PROCESS] 远程源 {url} 提取到 {len(m3u_lines)} 条数据")

    # 2. 读取本地文件并合并（保留原有逻辑，可根据需要开启）
    # lines1 = read_txt_file(file_dirs["live"])
    # lines2 = read_txt_file(file_dirs["blacklist_auto"])
    # lines3 = read_txt_file(file_dirs["others"])
    # urls_all_lines.extend(lines1 + lines2 + lines3)

    # 3. 数据清洗（分级# -> 去$ -> 去重）
    print(f"[CLEAN] 原始数据条数: {len(urls_all_lines)}")
    urls_all_lines = split_url_hash(urls_all_lines)
    urls_all_lines = clean_url_dollar(urls_all_lines)
    urls_all_lines = remove_duplicates_url(urls_all_lines)
    clean_count = len(urls_all_lines)
    print(f"[CLEAN] 清洗后数据条数: {clean_count}")

    # 4. 处理白名单
    whitelist_lines = read_txt_file(file_dirs["whitelist_manual"])
    whitelist_lines = split_url_hash(whitelist_lines)
    whitelist_lines = clean_url_dollar(whitelist_lines)
    whitelist_lines = remove_duplicates_url(whitelist_lines)
    whitelist_set = extract_whitelist_set(whitelist_lines)
    print(f"[WHITELIST] 白名单有效URL数: {len(whitelist_set)}")

    # 5. 多线程检测URL
    print(f"[CHECK] 开始多线程检测URL，线程数: {MAX_WORKERS}")
    success_list, black_list = process_urls_multithreaded(urls_all_lines, whitelist_set)
    ok_count, ng_count = len(success_list), len(black_list)
    print(f"[CHECK] 检测完成 - 成功: {ok_count} 条, 失败: {ng_count} 条")

    # 6. 生成输出并写入文件
    success_output, success_tv_output, black_output = generate_output_lines(success_list, black_list)
    write_list(file_dirs["whitelist_auto"], success_output)
    write_list(file_dirs["whitelist_auto_tv"], success_tv_output)
    write_list(file_dirs["blacklist_auto"], black_output)

    # 7. 保存黑名单Host统计
    save_blackhost_count(file_dirs["blackhost_count"])

    # 8. 输出执行统计
    end_time = datetime.now()
    elapsed = end_time - start_time
    total_seconds = int(elapsed.total_seconds())
    minutes, seconds = total_seconds // 60, total_seconds % 60

    print("=" * 50)
    print(f"[END] 程序执行完成: {end_time.strftime('%Y%m%d %H:%M:%S')}")
    print(f"[STAT] 执行时间: {minutes} 分 {seconds} 秒")
    print(f"[STAT] 原始数据: {len(urls_all_lines) + (ok_count + ng_count - clean_count)} 条")
    print(f"[STAT] 清洗后: {clean_count} 条")
    print(f"[STAT] 检测成功: {ok_count} 条")
    print(f"[STAT] 检测失败: {ng_count} 条")
    print("=" * 50)

    # 输出远程源统计
    if url_statistics:
        print("[STAT] 远程源数据统计:")
        for stat in url_statistics:
            print(stat)
