import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from datetime import datetime, timedelta, timezone
import os
from urllib.parse import urlparse, quote, unquote
import socket
import subprocess

timestart = datetime.now()
USER_AGENT = "PostmanRuntime-ApipostRuntime/1.1.0"
TIMEOUT_CHECK = 5
TIMEOUT_FETCH = 8
MAX_WORKERS = 30
blacklist_dict = {}
urls_all_lines = []
url_statistics = []

def read_txt_to_array(file_name):
    try:
        with open(file_name, 'r', encoding='utf-8') as file:
            return [line.strip() for line in file.readlines() if line.strip()]
    except FileNotFoundError:
        print(f"File '{file_name}' not found.")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

def read_txt_file(file_path):
    skip_strings = ['#genre#', '#EXTINF:-1', '"ext"']
    required_strings = ['://']
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return [
                line.strip() for line in file
                if not any(skip_str in line for skip_str in skip_strings)
                and all(req_str in line for req_str in required_strings)
            ]
    except Exception as e:
        print(f"Read file error {file_path}: {e}")
        return []

def get_host_from_url(url: str) -> str:
    try:
        return urlparse(url).netloc or ""
    except Exception:
        return ""

def record_host(host):
    if not host:
        return
    blacklist_dict[host] = blacklist_dict.get(host, 0) + 1

def check_p3p_url(url, timeout):
    try:
        parsed = urlparse(url)
        host, port = parsed.hostname, parsed.port or 80
        path = parsed.path or "/"
        if not host or not port:
            return False
        with socket.create_connection((host, port), timeout=timeout) as s:
            request = (
                f"GET {path} P3P/1.0\r\n"
                f"Host: {host}\r\n"
                f"User-Agent: {USER_AGENT}\r\n"
                f"Connection: close\r\n\r\n"
            )
            s.sendall(request.encode())
            return b"P3P" in s.recv(1024)
    except Exception:
        return False

def check_p2p_url(url, timeout):
    try:
        parsed = urlparse(url)
        host, port, path = parsed.hostname, parsed.port, parsed.path
        if not host or not port or not path:
            return False
        with socket.create_connection((host, port), timeout=timeout) as s:
            request = f"YOUR_CUSTOM_REQUEST {path}\r\nHost: {host}\r\n\r\n"
            s.sendall(request.encode())
            return b"SOME_EXPECTED_RESPONSE" in s.recv(1024)
    except Exception:
        return False

def check_rtmp_url(url, timeout):
    try:
        subprocess.run(
            ['ffprobe', '-v', 'quiet', url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout
        )
        return True
    except Exception:
        return False

def check_rtp_url(url, timeout):
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

# 核心修复：重构check_url，所有协议统一统计真实耗时
def check_url(url, timeout=TIMEOUT_CHECK):
    try:
        encoded_url = quote(unquote(url), safe=':/?&=')
        start_time = time.time()  # 移到try内，检测开始才计时（修复非HTTP协议计时异常）
        # 按协议分支检测
        if url.startswith("http"):
            req = urllib.request.Request(encoded_url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status != 200:
                    raise Exception(f"HTTP Status Error: {resp.status}")
        elif url.startswith("p3p"):
            if not check_p3p_url(encoded_url, timeout):
                raise Exception("P3P Check Failed")
        elif url.startswith("p2p"):
            if not check_p2p_url(encoded_url, timeout):
                raise Exception("P2P Check Failed")
        elif url.startswith(("rtmp", "rtsp")):
            if not check_rtmp_url(encoded_url, timeout):
                raise Exception("RTMP/RTSP Check Failed")
        elif url.startswith("rtp"):
            if not check_rtp_url(encoded_url, timeout):
                raise Exception("RTP Check Failed")
        else:
            raise Exception(f"Unsupported Scheme: {url.split('://')[0]}")
        # 所有协议检测成功后，统一计算真实耗时
        real_elapsed = (time.time() - start_time) * 1000
        return real_elapsed, True
    except Exception:
        record_host(get_host_from_url(url))
        return None, False

def is_m3u_content(text):
    return text.strip().startswith("#EXTM3U") if text else False

def convert_m3u_to_txt(m3u_content):
    lines = [line.strip() for line in m3u_content.split('\n') if line.strip()]
    txt_lines, channel_name = [], ""
    for line in lines:
        if line.startswith("#EXTINF"):
            channel_name = line.split(',')[-1].strip()
        elif line.startswith(("http", "rtmp", "rtsp", "p3p", "p2p", "rtp")) and channel_name:
            txt_lines.append(f"{channel_name},{line}")
    return txt_lines

def process_url(url):
    try:
        encoded_url = quote(unquote(url), safe=':/?&=')
        req = urllib.request.Request(encoded_url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=TIMEOUT_FETCH) as resp:
            text = resp.read().decode('utf-8', errors='replace')
            if is_m3u_content(text):
                m3u_lines = convert_m3u_to_txt(text)
                url_statistics.append(f"{len(m3u_lines)},{url.strip()}")
                urls_all_lines.extend(m3u_lines)
            else:
                valid_lines = [
                    line.strip() for line in text.split('\n')
                    if line.strip() and "#genre#" not in line and "," in line and "://" in line
                ]
                url_statistics.append(f"{len(valid_lines)},{url.strip()}")
                urls_all_lines.extend(valid_lines)
    except Exception as e:
        print(f"Process URL error {url}: {e}")

def split_url(lines):
    newlines = []
    for line in lines:
        if "," not in line or "://" not in line:
            continue
        channel_name, channel_url = line.split(',', 1)
        if "#" not in channel_url:
            newlines.append(line)
        else:
            for url in channel_url.split('#'):
                url = url.strip()
                if "://" in url:
                    newlines.append(f"{channel_name},{url}")
    return newlines

def clean_url(lines):
    newlines = []
    for line in lines:
        if "," in line and "://" in line:
            dollar_idx = line.rfind('$')
            newlines.append(line[:dollar_idx] if dollar_idx != -1 else line)
    return newlines

def remove_duplicates_url(lines):
    url_set, newlines = set(), []
    for line in lines:
        if "," in line and "://" in line:
            _, url = line.split(',', 1)
            url = url.strip()
            if url not in url_set:
                url_set.add(url)
                newlines.append(line)
    return newlines

# 真实耗时
def process_line(line, whitelist):
    if "#genre#" in line or "://" not in line or not line.strip():
        return None, None
    parts = line.split(',', 1)
    if len(parts) != 2:
        return None, None
    name, url = parts
    url = url.strip()
    
    # 执行一次check_url检测，避免重复请求
    elapsed_time, is_valid = check_url(url)
    
    # 按是否是白名单，分别处理结果（完全保留原需求逻辑）
    if url in whitelist:
        # 白名单：成功返真实耗时，失败兜底0.01ms（保留，不进黑名单）
        return (elapsed_time if is_valid else 0.01, line)
    else:
        # 非白名单：成功返真实耗时，失败返None（进黑名单）
        return (elapsed_time, line) if is_valid else (None, line)

def process_urls_multithreaded(lines, whitelist, max_workers=MAX_WORKERS):
    successlist, blacklist = [], []
    if not lines:
        return successlist, blacklist
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_line, line, whitelist): line for line in lines}
        for future in as_completed(futures):
            elapsed, result = future.result()
            if result:
                if elapsed is not None:
                    successlist.append(f"{elapsed:.2f}ms,{result}")
                else:
                    blacklist.append(result)
    # 按真实响应时间升序排序，兜底0.01ms的白名单链接会排在最前
    successlist.sort(key=lambda x: float(x.split(',')[0].replace('ms', '')))
    blacklist.sort()
    return successlist, blacklist

def write_list(file_path, data_list):
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(data_list))
        print(f"File generated: {file_path}")
    except Exception as e:
        print(f"Write file error {file_path}: {e}")

def remove_prefix_from_lines(lines):
    result = []
    for line in lines:
        if "," in line and "://" in line and "ms," in line:
            result.append(",".join(line.split(",")[1:]))
    return result

def get_file_paths():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    parent2_dir = os.path.dirname(parent_dir)
    return {
        "urls": os.path.join(parent_dir, 'urls.txt'),
        "live": os.path.join(parent2_dir, 'live.txt'),
        "blacklist_auto": os.path.join(current_dir, 'blacklist_auto.txt'),
        "others": os.path.join(parent2_dir, 'others.txt'),
        "whitelist_manual": os.path.join(current_dir, 'whitelist_manual.txt'),
        "whitelist_auto": os.path.join(current_dir, 'whitelist_auto.txt'),
        "whitelist_auto_tv": os.path.join(current_dir, 'whitelist_auto_tv.txt')
    }

if __name__ == "__main__":
    file_paths = get_file_paths()
    remote_urls = read_txt_to_array(file_paths["urls"])
    
    for url in remote_urls:
        if url.startswith("http"):
            print(f"Process remote URL: {url}")
            process_url(url)

    lines_whitelist = read_txt_file(file_paths["whitelist_manual"])
    lines = urls_all_lines

    print(f"Original data count: {len(lines)}")
    lines = split_url(lines)
    lines_whitelist = split_url(lines_whitelist)
    lines = clean_url(lines)
    lines_whitelist = clean_url(lines_whitelist)
    lines = remove_duplicates_url(lines)
    lines_whitelist = remove_duplicates_url(lines_whitelist)
    clean_count = len(lines)
    print(f"Cleaned data count: {clean_count}")

    whitelist_set = set()
    for line in lines_whitelist:
        if "," in line and "://" in line:
            _, url = line.split(',', 1)
            whitelist_set.add(url.strip())
    print(f"Whitelist URL count: {len(whitelist_set)}")

    successlist, blacklist = process_urls_multithreaded(lines, whitelist_set)
    ok_count, ng_count = len(successlist), len(blacklist)
    print(f"Check done - Success: {ok_count}, Failed: {ng_count}")

    bj_time = datetime.now(timezone.utc) + timedelta(hours=8)
    version = f"{bj_time.strftime('%Y%m%d %H:%M')},url"
    success_tv = remove_prefix_from_lines(successlist)

    success_output = [
        "更新时间,#genre#", version, "",
        "RespoTime,whitelist,#genre#"
    ] + successlist
    success_tv_output = [
        "更新时间,#genre#", version, "",
        "whitelist,#genre#"
    ] + success_tv
    black_output = [
        "更新时间,#genre#", version, "",
        "blacklist,#genre#"
    ] + blacklist

    write_list(file_paths["whitelist_auto"], success_output)
    write_list(file_paths["whitelist_auto_tv"], success_tv_output)
    write_list(file_paths["blacklist_auto"], black_output)

    end_time = datetime.now()
    elapsed = end_time - timestart
    mins, secs = int(elapsed.total_seconds() // 60), int(elapsed.total_seconds() % 60)
    print("="*50)
    print(f"Start time: {timestart.strftime('%Y%m%d %H:%M:%S')}")
    print(f"End time: {end_time.strftime('%Y%m%d %H:%M:%S')}")
    print(f"Elapsed time: {mins} min {secs} sec")
    print(f"Original count: {len(urls_all_lines)}")
    print(f"Cleaned count: {clean_count}")
    print(f"Success count: {ok_count}")
    print(f"Failed count: {ng_count}")
    print("="*50)

    for stat in url_statistics:
        print(stat)
