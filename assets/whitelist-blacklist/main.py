#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
直播源响应时间检测工具
功能：检测远程直播源的响应时间
特点：
- 已在blacklist_auto中的链接直接判定失败，不检测
- 白名单失败显示0.00ms，不加入黑名单
- 新的失败链接追加到blacklist_auto
- 支持手动输入多个URL，空格/换行/逗号分隔
- 黑名单写入模式：BLACKLIST_MERGE = True 合并 / False 复写
"""

import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from datetime import datetime, timedelta, timezone
import os
from urllib.parse import urlparse, quote, unquote
import socket
import ssl
import re
from typing import List, Tuple, Set, Dict
import logging
import sys

# 获取文件路径
def get_file_paths():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    return {
        "urls": os.path.join(parent_dir, 'urls.txt'),
        "blacklist_auto": os.path.join(current_dir, 'blacklist_auto.txt'),
        "whitelist_manual": os.path.join(current_dir, 'whitelist_manual.txt'),
        "whitelist_auto": os.path.join(current_dir, 'whitelist_auto.txt'),
        "whitelist_respotime": os.path.join(current_dir, 'whitelist_respotime.txt'),
        "log": os.path.join(current_dir, 'log.txt')
    }

FILE_PATHS = get_file_paths()

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(FILE_PATHS["log"], mode='w', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Config:
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    USER_AGENT_URL = "okhttp/3.14.9"

    TIMEOUT_FETCH = 5
    TIMEOUT_CHECK = 2.5
    TIMEOUT_CONNECT = 1.5
    TIMEOUT_READ = 1.5

    MAX_WORKERS = 30

    # 黑名单写入模式（bool）：
    #   True  = 合并（保留旧黑名单 + 追加新失败）
    #   False = 复写（只保留本次检测失败的链接）
    BLACKLIST_MERGE = False

class StreamChecker:
    def __init__(self, manual_urls=None):
        self.start_time = datetime.now()
        self.ipv6_available = self._check_ipv6()
        self.blacklist_urls = self._load_blacklist()
        self.whitelist_urls = set()
        self.whitelist_lines = []
        self.new_failed_urls = set()
        self.manual_urls = manual_urls or []

    def _check_ipv6(self):
        try:
            sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('2001:4860:4860::8888', 53))
            sock.close()
            return result == 0
        except:
            return False

    def _load_blacklist(self) -> Set[str]:
        # 复写模式：不加载旧黑名单
        if not Config.BLACKLIST_MERGE:
            logger.info("复写模式：跳过加载旧黑名单")
            return set()

        blacklist = set()
        try:
            if os.path.exists(FILE_PATHS["blacklist_auto"]):
                with open(FILE_PATHS["blacklist_auto"], 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('更新时间') or line.startswith('blacklist'):
                            continue
                        if ',' in line:
                            parts = line.split(',')
                            url = parts[-1].strip()
                        else:
                            url = line
                        if '://' in url:
                            blacklist.add(url)
                logger.info(f"加载黑名单: {len(blacklist)} 个链接")
        except Exception as e:
            logger.error(f"加载黑名单失败: {e}")
        return blacklist

    def _save_blacklist(self):
        # 复写模式：无论本次是否有新失败，都重写黑名单文件
        if not Config.BLACKLIST_MERGE:
            self._write_blacklist_file(self.new_failed_urls)
            logger.info(f"黑名单已复写: {len(self.new_failed_urls)} 个")
            return

        # 合并模式：没有新失败就不动文件
        if not self.new_failed_urls:
            return

        try:
            existing_lines = []
            has_header = False
            if os.path.exists(FILE_PATHS["blacklist_auto"]):
                with open(FILE_PATHS["blacklist_auto"], 'r', encoding='utf-8') as f:
                    existing_lines = [line.rstrip('\n') for line in f]
                    for line in existing_lines[:3]:
                        if line.startswith('更新时间') or line.startswith('blacklist'):
                            has_header = True

            all_content = []
            if not has_header:
                bj_time = datetime.now(timezone.utc) + timedelta(hours=8)
                version = f"{bj_time.strftime('%Y%m%d %H:%M')},url"
                all_content.extend(["更新时间,#genre#", version, "", "blacklist,#genre#"])

            existing_urls = set()
            for line in existing_lines:
                if line and not line.startswith('更新时间') and not line.startswith('blacklist') and line.strip():
                    url = line.split(',')[-1].strip() if ',' in line else line.strip()
                    if url and '://' in url and url not in existing_urls:
                        existing_urls.add(url)
                        all_content.append(line)

            for url in self.new_failed_urls:
                if url not in existing_urls:
                    existing_urls.add(url)
                    all_content.append(url)

            os.makedirs(os.path.dirname(FILE_PATHS["blacklist_auto"]), exist_ok=True)
            with open(FILE_PATHS["blacklist_auto"], 'w', encoding='utf-8') as f:
                f.write('\n'.join(all_content))

            logger.info(f"黑名单已更新: 新增 {len(self.new_failed_urls)} 个")
        except Exception as e:
            logger.error(f"保存黑名单失败: {e}")

    def _write_blacklist_file(self, urls: Set[str]):
        """按标准格式重写黑名单文件（复写模式使用）"""
        bj_time = datetime.now(timezone.utc) + timedelta(hours=8)
        version = f"{bj_time.strftime('%Y%m%d %H:%M')},url"
        all_content = ["更新时间,#genre#", version, "", "blacklist,#genre#"]
        all_content.extend(sorted(urls))
        os.makedirs(os.path.dirname(FILE_PATHS["blacklist_auto"]), exist_ok=True)
        with open(FILE_PATHS["blacklist_auto"], 'w', encoding='utf-8') as f:
            f.write('\n'.join(all_content))

    def read_file(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip()]
        except:
            return []

    def create_ssl_context(self):
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context

    def check_http(self, url, timeout):
        start = time.perf_counter()
        try:
            headers = {"User-Agent": Config.USER_AGENT, "Connection": "close", "Range": "bytes=0-512"}
            req = urllib.request.Request(url, headers=headers, method="HEAD")
            opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=self.create_ssl_context()))
            with opener.open(req, timeout=timeout) as resp:
                elapsed = (time.perf_counter() - start) * 1000
                return 200 <= resp.getcode() < 400, round(elapsed, 2)
        except urllib.error.HTTPError as e:
            return e.code in (301,302), round((time.perf_counter()-start)*1000,2)
        except:
            return False, round((time.perf_counter()-start)*1000,2)

    def check_rtmp_rtsp(self, url, timeout):
        start = time.perf_counter()
        try:
            parsed = urlparse(url)
            if not parsed.hostname: return False, 0
            port = parsed.port or (1935 if url.startswith('rtmp') else 554)
            ips = []
            try:
                addrs = socket.getaddrinfo(parsed.hostname, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
                ips = [(a[4][0], a[0]) for a in addrs[:2]]
            except: pass
            for ip, af in ips:
                s = None
                try:
                    s = socket.socket(af, socket.SOCK_STREAM)
                    s.settimeout(timeout)
                    s.connect((ip, port))
                    if url.startswith('rtmp'):
                        s.send(b'\x03')
                        s.settimeout(Config.TIMEOUT_READ)
                        return bool(s.recv(1)), round((time.perf_counter()-start)*1000,2)
                    else:
                        return True, round((time.perf_counter()-start)*1000,2)
                except: continue
                finally:
                    if s: s.close()
            return False, round((time.perf_counter()-start)*1000,2)
        except:
            return False, round((time.perf_counter()-start)*1000,2)

    def check_url(self, url, is_whitelist=False):
        try:
            u = quote(unquote(url), safe=':/?&=#')
            t = Config.TIMEOUT_CHECK * 1.5 if is_whitelist else Config.TIMEOUT_CHECK
            if url.startswith(('http://','https://')):
                return self.check_http(u,t)
            elif url.startswith(('rtmp://','rtsp://')):
                return self.check_rtmp_rtsp(u,t)
            else:
                start = time.perf_counter()
                parsed = urlparse(url)
                if not parsed.hostname: return False,0
                p = parsed.port or 80
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(Config.TIMEOUT_CONNECT)
                s.connect((parsed.hostname,p))
                s.close()
                return True, round((time.perf_counter()-start)*1000,2)
        except:
            return False, round((time.perf_counter()-start)*1000,2)

    def fetch_remote(self, urls):
        all_lines = []
        for url in urls:
            try:
                req = urllib.request.Request(quote(unquote(url), safe=':/?&=#'), headers={"User-Agent":Config.USER_AGENT_URL})
                with urllib.request.urlopen(req, timeout=Config.TIMEOUT_FETCH) as r:
                    c = r.read().decode('utf-8','replace')
                    if "#EXTM3U" in c:
                        lines = self.parse_m3u(c)
                    else:
                        lines = [l.strip() for l in c.split('\n') if l.strip() and '://' in l and ',' in l]
                    all_lines.extend(lines)
                    logger.info(f"获取 {url} → {len(lines)} 条")
            except Exception as e:
                logger.error(f"拉取失败 {url}: {e}")
        return all_lines

    def parse_m3u(self, content):
        lines, name = [], ""
        for l in content.split('\n'):
            l = l.strip()
            if l.startswith("#EXTINF"):
                m = re.search(r',(.+)$', l)
                if m: name = m.group(1).strip()
            elif l.startswith(('http://','https://','rtmp://','rtsp://')) and name:
                lines.append(f"{name},{l}")
                name = ""
        return lines

    def load_whitelist(self):
        for line in self.read_file(FILE_PATHS["whitelist_manual"]):
            if ',' in line and '://' in line:
                n, u = line.split(',',1)
                self.whitelist_urls.add(u.strip())
                self.whitelist_lines.append(line)
        logger.info(f"白名单: {len(self.whitelist_urls)} 个")

    def prepare_lines(self, lines):
        to_check, pre_fail, url2line = [], [], {}
        skip = 0
        for line in lines:
            if ',' not in line or '://' not in line: continue
            n, u = line.split(',',1)
            u = u.strip().split('#')[0].split('$')[0]
            full = f"{n},{u}"
            url2line[u] = full
            if u in self.blacklist_urls and u not in self.whitelist_urls:
                pre_fail.append(full)
                skip += 1
            else:
                to_check.append((u, full))
        logger.info(f"黑名单跳过: {skip} | 待检测: {len(to_check)}")
        return to_check, pre_fail, url2line

    def batch_check(self, to_check, url2line):
        ok, bad = [], []
        total = len(to_check)
        logger.info(f"开始检测 {total} 个")
        with ThreadPoolExecutor(Config.MAX_WORKERS) as e:
            fut = {}
            for u,l in to_check:
                wl = u in self.whitelist_urls
                fut[e.submit(self.check_url,u,wl)] = (u,l,wl)
            cnt = 0
            for f in as_completed(fut):
                u,l,wl = fut[f]
                cnt += 1
                try:
                    valid, t = f.result()
                    if valid:
                        ok.append((l,t))
                    else:
                        if wl:
                            ok.append((l,0.00))
                        else:
                            bad.append(l)
                            self.new_failed_urls.add(u)
                except:
                    if wl:
                        ok.append((l,0.00))
                    else:
                        bad.append(l)
                        self.new_failed_urls.add(u)
                if cnt % 50 == 0:
                    v = sum(1 for _,x in ok if x>0)
                    logger.info(f"进度 {cnt}/{total} | 有效 {v} | 失败 {len(bad)}")
        ok.sort(key=lambda x:x[1])
        v = sum(1 for _,x in ok if x>0)
        logger.info(f"完成 | 有效 {v} | 新增失败 {len(bad)}")
        return ok, bad

    def save_results(self, ok, bad, pre_fail):
        t = datetime.now(timezone.utc)+timedelta(hours=8)
        ver = f"{t.strftime('%Y%m%d %H:%M')},url"
        resp = ["更新时间,#genre#", ver, "", "响应时间,名称,URL,#genre#"]
        for l,rt in ok: resp.append(f"{rt:.2f}ms,{l}")
        clean = ["更新时间,#genre#", ver, "", "直播源,#genre#"]
        clean.extend(l for l,_ in ok)
        fail = ["更新时间,#genre#", ver, "", "失败链接,#genre#"]
        fail.extend(bad+pre_fail)
        self._write(FILE_PATHS["whitelist_respotime"], resp)
        self._write(FILE_PATHS["whitelist_auto"], clean)
        self._write(FILE_PATHS["blacklist_auto"], fail)
        logger.info(f"保存成功：白名单{len(ok)}条，黑名单{len(bad+pre_fail)}条")

    def _write(self, p, lines):
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p,'w',encoding='utf-8') as f: f.write('\n'.join(lines))

    def run(self):
        logger.info("="*50)
        logger.info("直播源检测工具")
        logger.info("="*50)
        self.load_whitelist()
        if self.manual_urls:
            logger.info(f"✅ 使用手动输入URL：{len(self.manual_urls)} 个")
            all_lines = self.fetch_remote(self.manual_urls)
        else:
            logger.info("ℹ️ 使用默认 urls.txt")
            ru = self.read_file(FILE_PATHS["urls"])
            if not ru:
                logger.error("未找到 urls.txt")
                return
            all_lines = self.fetch_remote(ru)
        all_lines.extend(self.whitelist_lines)
        tc, pf, ul = self.prepare_lines(all_lines)
        s, f = self.batch_check(tc, ul)
        self._save_blacklist()
        self.save_results(s,f,pf)
        logger.info(f"总耗时：{(datetime.now()-self.start_time).total_seconds():.1f}s")
        logger.info("="*50)

# ================= 多URL解析 =================
def parse_input_urls(text):
    if not text: return []
    text = text.replace('\n',' ').replace(',',' ').strip()
    return [u.strip() for u in text.split() if u.strip() and '://' in u]

# ================= 命令行参数解析 =================
def parse_args(argv):
    """
    --merge / -m        合并（默认）
    --overwrite / -o    复写
    --no-merge          复写
    也支持环境变量 BLACKLIST_MERGE=0/1/true/false
    """
    manual_urls = []
    merge = Config.BLACKLIST_MERGE

    env = os.environ.get("BLACKLIST_MERGE", "").strip().lower()
    if env in ("0", "false", "no", "off"):
        merge = False
    elif env in ("1", "true", "yes", "on"):
        merge = True

    i = 1
    while i < len(argv):
        arg = argv[i]
        if arg in ("--merge", "-m"):
            merge = True
        elif arg in ("--overwrite", "-o", "--no-merge"):
            merge = False
        elif arg.startswith("--"):
            pass  # 忽略未知参数
        else:
            manual_urls.extend(parse_input_urls(arg))
        i += 1

    Config.BLACKLIST_MERGE = merge
    return manual_urls

if __name__ == "__main__":
    manual_urls = parse_args(sys.argv)
    logger.info(f"黑名单模式：{'合并' if Config.BLACKLIST_MERGE else '复写'}")
    checker = StreamChecker(manual_urls=manual_urls)
    try:
        checker.run()
    except KeyboardInterrupt:
        logger.info("用户中断")
    except Exception as e:
        logger.error(f"错误：{e}")
