import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from datetime import datetime, timedelta, timezone
import os
from urllib.parse import quote, unquote, urlparse
import socket
import subprocess
from typing import List, Tuple, Dict, Optional

TIMEOUT_URL_CHECK = 3
TIMEOUT_URL_FETCH = 5
MAX_WORKERS = 50
USER_AGENT = "PostmanRuntime-ApipostRuntime/1.1.0"
SKIP_STRINGS = ['#genre#', '#EXTINF:-1', '"ext"']
REQUIRED_STRINGS = ['://']
socket.setdefaulttimeout(5)

blacklist_host_dict: Dict[str, int] = {}

def read_txt_to_array(file_name: str) -> List[str]:
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
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(data_list))
        print(f"[SUCCESS] 文件已生成: {file_path}")
    except Exception as e:
        print(f"[ERROR] 写入文件 {file_path} 失败: {str(e)}")

def get_host_from_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        return parsed.netloc if parsed.netloc else ""
    except Exception:
        return ""

def safe_quote_url(url: str) -> str:
    try:
        unquoted = unquote(url)
        return quote(unquoted, safe=':/?&=')
    except Exception:
        return url

def get_file_dirs() -> Dict[str, str]:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    parent2_dir = os.path.dirname(parent_dir)
    return {
        "current": current_dir,
        "parent2": parent2_dir,
        "urls": os.path.join(parent_dir, 'urls.txt'),
        "live": os.path.join(parent2_dir, 'live.txt'),
        "blacklist_auto": os.path.join(current_dir, 'blacklist_auto.txt'),
        "others": os.path.join(parent2_dir, 'others.txt'),
        "whitelist_manual": os.path.join(current_dir, 'whitelist_manual.txt'),
        "whitelist_auto": os.path.join(current_dir, 'whitelist_auto.txt'),
        "whitelist_auto_tv": os.path.join(current_dir, 'whitelist_auto_tv.txt'),
        "blackhost_count": os.path.join(current_dir, "blackhost_count.txt")
    }

def record_black_host(host: str) -> None:
    if not host:
        return
    blacklist_host_dict[host] = blacklist_host_dict.get(host, 0) + 1

def check_p3p_url(url: str, timeout: int) -> bool:
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
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-timeout', f'{timeout * 1000000}', url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout
        )
        return result.returncode == 0
    except Exception:
        return False

def check_rtp_url(url: str, timeout: int) -> bool:
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
    except Exception:
        return False

def check_url(url: str, timeout: int = TIMEOUT_URL_CHECK) -> Tuple[Optional[float], bool]:
    start_time = time.time()
    try:
        encoded_url = safe_quote_url(url)
        if url.startswith("http"):
            req = urllib.request.Request(encoded_url, headers={"User-Agent": USER_AGENT})
            req.set_timeout(timeout)
            with urllib.request.urlopen(req) as resp:
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
    except Exception:
        record_black_host(get_host_from_url(url))
        return None, False

def is_m3u_content(text: str) -> bool:
    return text.strip().startswith("#EXTM3U") if text else False

def convert_m3u_to_txt(m3u_content: str) -> List[str]:
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
    try:
        req = urllib.request.Request(safe_quote_url(url), headers={"User-Agent": USER_AGENT})
        req.set_timeout(TIMEOUT_URL_FETCH)
        with urllib.request.urlopen(req) as resp:
            text = resp.read().decode('utf-8', errors='ignore')
            if is_m3u_content(text):
                return convert_m3u_to_txt(text)
            else:
                return [
                    line.strip() for line in text.split('\n')
                    if line.strip() and "#genre#" not in line and "," in line and "://" in line
                ]
    except Exception as e:
        print(f"[ERROR] 拉取远程源失败 {url}: {str(e)}")
        return []

def clean_url_dollar(lines: List[str]) -> List[str]:
    clean_lines = []
    for line in lines:
        if "," in line and "://" in line:
            dollar_idx = line.rfind('$')
            clean_lines.append(line[:dollar_idx] if dollar_idx != -1 else line)
    return clean_lines

def split_url_hash(lines: List[str]) -> List[str]:
    split_lines = []
    for line in lines:
        if "," not in line or "://" not in line:
            continue
        channel_name, channel_url = line.split(',', 1)
        if "#" not in channel_url:
            split_lines.append(line)
        else:
            for url in channel_url.split('#'):
                url = url.strip()
                if "://" in url:
                    split_lines.append(f"{channel_name},{url}")
    return split_lines

def remove_duplicates_url(lines: List[str]) -> List[str]:
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
    url_set = set()
    for line in whitelist_lines:
        if "," in line and "://" in line:
            parts = line.split(',', 1)
            if len(parts) >= 2:
                url_set.add(parts[1].strip())
    return url_set

def process_line(line: str, whitelist_set: set) -> Tuple[Optional[float], Optional[str]]:
    if not line or "#genre#" in line or "://" not in line:
        return None, None
    line = line.strip()
    if "," not in line:
        return None, None
    
    channel_name, url = line.split(',', 1)
    url = url.strip()
    if url in whitelist_set:
        return 0.0, line
    elapsed_time, is_valid = check_url(url)
    return (elapsed_time, line) if is_valid else (None, line)

def process_urls_multithreaded(lines: List[str], whitelist_set: set, max_workers: int = MAX_WORKERS) -> Tuple[List[str], List[str]]:
    success_list, black_list = [], []
    if not lines:
        return success_list, black_list
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_line, line, whitelist_set): line for line in lines}
        for future in as_completed(futures):
            elapsed_time, result_line = future.result()
            if result_line:
                if elapsed_time is not None:
                    success_list.append(f"{elapsed_time:.2f}ms,{result_line}")
                else:
                    black_list.append(result_line)
    success_list.sort(key=lambda x: float(x.split(',')[0].replace('ms', '')))
    black_list.sort()
    return success_list, black_list

def generate_output_lines(success_list: List[str], black_list: List[str]) -> Tuple[List[str], List[str], List[str]]:
    bj_time = datetime.now(timezone.utc) + timedelta(hours=8)
    version = f"{bj_time.strftime('%Y%m%d %H:%M')},url"
    success_tv = [line.split(',', 1)[1] for line in success_list if ',' in line]
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
    if not blacklist_host_dict:
        print("[INFO] 无黑名单Host记录")
        return
    sorted_hosts = sorted(blacklist_host_dict.items(), key=lambda x: x[1], reverse=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        for host, count in sorted_hosts:
            f.write(f"{host}: {count}\n")
    print(f"[SUCCESS] 黑名单Host统计已保存: {file_path}")

if __name__ == "__main__":
    start_time = datetime.now()
    print(f"[START] 程序开始执行: {start_time.strftime('%Y%m%d %H:%M:%S')}")
    file_dirs = get_file_dirs()
    url_statistics = []
    urls_all_lines = []

    remote_urls = read_txt_to_array(file_dirs["urls"])
    for url in remote_urls:
        if url.startswith("http"):
            print(f"[PROCESS] 拉取远程源: {url}")
            m3u_lines = process_remote_url(url)
            url_statistics.append(f"{len(m3u_lines)},{url.strip()}")
            urls_all_lines.extend(m3u_lines)
            print(f"[PROCESS] 远程源 {url} 提取到 {len(m3u_lines)} 条数据")

    print(f"[CLEAN] 原始数据条数: {len(urls_all_lines)}")
    urls_all_lines = split_url_hash(urls_all_lines)
    urls_all_lines = clean_url_dollar(urls_all_lines)
    urls_all_lines = remove_duplicates_url(urls_all_lines)
    clean_count = len(urls_all_lines)
    print(f"[CLEAN] 清洗后数据条数: {clean_count}")

    whitelist_lines = read_txt_file(file_dirs["whitelist_manual"])
    whitelist_lines = split_url_hash(whitelist_lines)
    whitelist_lines = clean_url_dollar(whitelist_lines)
    whitelist_lines = remove_duplicates_url(whitelist_lines)
    whitelist_set = extract_whitelist_set(whitelist_lines)
    print(f"[WHITELIST] 白名单有效URL数: {len(whitelist_set)}")

    print(f"[CHECK] 开始多线程检测URL，线程数: {MAX_WORKERS}")
    success_list, black_list = process_urls_multithreaded(urls_all_lines, whitelist_set)
    ok_count, ng_count = len(success_list), len(black_list)
    print(f"[CHECK] 检测完成 - 成功: {ok_count} 条, 失败: {ng_count} 条")

    success_output, success_tv_output, black_output = generate_output_lines(success_list, black_list)
    write_list(file_dirs["whitelist_auto"], success_output)
    write_list(file_dirs["whitelist_auto_tv"], success_tv_output)
    write_list(file_dirs["blacklist_auto"], black_output)

    save_blackhost_count(file_dirs["blackhost_count"])

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

    if url_statistics:
        print("[STAT] 远程源数据统计:")
        for stat in url_statistics:
            print(stat)
