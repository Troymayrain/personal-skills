#!/usr/bin/env python3
"""通过本地 Mihomo API 测量真实代理，并在每轮保存可恢复的报告。"""
import argparse
import concurrent.futures
import datetime
import http.client
import json
import math
import os
from pathlib import Path
import signal
import socket
import statistics
import tempfile
import time
from typing import Any, Dict, List, Optional, Tuple
import urllib.parse


class APIError(Exception):
    """本地控制接口的脱敏错误。"""


class UnixHTTP(http.client.HTTPConnection):
    """通过 Unix socket 访问本地 Mihomo 控制器。"""

    def __init__(self, path: str, timeout: float) -> None:
        super().__init__('localhost', timeout=timeout)
        self.path = path

    def connect(self) -> None:
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self.path)


class API:
    """只读访问本地 Mihomo 控制器；认证信息只从环境变量读取。"""

    def __init__(self, controller: Optional[str], unix_socket: Optional[str], timeout: float) -> None:
        self.timeout = timeout
        self.unix_socket = unix_socket
        self.token = os.environ.get('MIHOMO_API_SECRET')
        if unix_socket:
            if not Path(unix_socket).is_absolute():
                raise ValueError('Unix socket path must be absolute')
            self.host, self.port = 'localhost', None
        else:
            u = urllib.parse.urlsplit(controller or '')
            if (u.scheme != 'http' or u.hostname not in {'127.0.0.1', 'localhost', '::1'}
                    or u.username or u.password or u.query or u.fragment
                    or u.path not in {'', '/'}):
                raise ValueError('Controller must be a loopback HTTP origin without credentials')
            self.host, self.port = u.hostname, u.port or 80

    def get(self, path: str) -> Dict[str, Any]:
        c = (UnixHTTP(self.unix_socket, self.timeout) if self.unix_socket
             else http.client.HTTPConnection(self.host, self.port, timeout=self.timeout))
        headers = {'Accept': 'application/json'}
        if self.token:
            headers['Authorization'] = 'Bearer ' + self.token
        try:
            c.request('GET', path, headers=headers)
            response = c.getresponse()
            body = response.read(2_000_000)
            if response.status != 200:
                raise APIError('HTTP ' + str(response.status))
            try:
                data = json.loads(body)
            except (ValueError, UnicodeError) as exc:
                raise APIError('Invalid API JSON') from exc
            if not isinstance(data, dict):
                raise APIError('Unexpected API response')
            return data
        except (OSError, http.client.HTTPException) as exc:
            raise APIError('Local controller connection failed or timed out') from exc
        finally:
            c.close()


def read_targets(path: str, default_limit: Optional[float]) -> List[Dict[str, Any]]:
    """验证目标清单，不读取节点的凭据或输出原始配置。"""
    raw = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(raw, list) or not raw:
        raise ValueError('Targets must be a nonempty JSON array')
    rows: List[Dict[str, Any]] = []
    seen = set()
    for item in raw:
        if isinstance(item, str):
            item = {'name': item}
        if not isinstance(item, dict):
            raise ValueError('Targets must be node names or objects')
        name = item.get('name')
        limit = item.get('max_ms', default_limit)
        if not isinstance(name, str) or not name.strip() or name in seen:
            raise ValueError('Node names must be nonempty and unique')
        if limit is not None and (isinstance(limit, bool) or not isinstance(limit, (int, float))
                                  or not math.isfinite(limit) or limit <= 0):
            raise ValueError('max_ms must be a positive finite number or null')
        seen.add(name)
        rows.append({'name': name, 'max_ms': limit, 'samples_ms': [], 'errors': []})
    return rows


def summarize(row: Dict[str, Any], expected_samples: int, completed_rounds: int) -> Dict[str, Any]:
    """仅对全部请求轮次完成、且全部成功的采样提供排名用均值。"""
    values = [v for v in row['samples_ms'] if v is not None]
    failures = len(row['samples_ms']) - len(values)
    complete = len(row['samples_ms']) == expected_samples
    eligible = complete and completed_rounds == expected_samples and failures == 0
    limit = row['max_ms']
    return {**row, 'failures': failures, 'complete': complete,
            'eligible_for_ranking': eligible,
            'mean_ms': statistics.mean(values) if eligible else None,
            'median_ms': statistics.median(values) if values else None,
            'max_observed_ms': max(values) if values else None,
            'strict_pass': (failures == 0 and complete and bool(values) and max(values) < limit)
            if limit is not None else None}


def checkpoint(path: Path, report: Dict[str, Any]) -> None:
    """在同一目录写私有临时文件，再原子替换已有报告。"""
    fd, tmp_name = tempfile.mkstemp(prefix='.' + path.name + '.', suffix='.tmp', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, allow_nan=False)
            f.write('\n')
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    endpoint = parser.add_mutually_exclusive_group(required=True)
    endpoint.add_argument('--controller')
    endpoint.add_argument('--unix-socket')
    parser.add_argument('--targets', required=True, help='JSON array of proxy names or {name, max_ms} objects')
    parser.add_argument('--output', required=True, help='New report path; never overwrites an existing file')
    parser.add_argument('--unified-delay', choices=['true', 'false'], required=True,
                        help='Value confirmed in the running core configuration')
    parser.add_argument('--network-note', default='Network path not independently verified')
    parser.add_argument('--url', default='https://www.gstatic.com/generate_204',
                        help='Public test URL; independently verify its HTTP response through each finalist')
    parser.add_argument('--samples', type=int, default=10)
    parser.add_argument('--timeout-ms', type=int, default=5000)
    parser.add_argument('--concurrency', type=int, default=2)
    parser.add_argument('--max-ms', type=float)
    args = parser.parse_args()
    if not 1 <= args.samples <= 20 or not 1 <= args.concurrency <= 8 or not 100 <= args.timeout_ms <= 30000:
        parser.error('samples 1..20, concurrency 1..8, timeout-ms 100..30000 required')
    target_url = urllib.parse.urlsplit(args.url)
    if (target_url.scheme not in {'http', 'https'} or not target_url.hostname
            or target_url.username or target_url.password):
        parser.error('Test URL must be HTTP(S), without user credentials')
    # 查询参数可能包含凭据；报告只保留请求路径。
    reported_url = urllib.parse.urlunsplit((target_url.scheme, target_url.netloc, target_url.path,
                                           'REDACTED' if target_url.query else '', ''))
    rows = read_targets(args.targets, args.max_ms)
    api = API(args.controller, args.unix_socket, args.timeout_ms / 1000 + 3)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(fd)
    report: Dict[str, Any] = {
        'started_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'finished_at_utc': None, 'status': 'running', 'metric': 'mihomo-url-test',
        'core_version': None, 'unified_delay': args.unified_delay == 'true',
        'unified_delay_evidence': 'caller-declared; not yet checked against API',
        'test_url': reported_url, 'timeout_ms': args.timeout_ms,
        'concurrency': args.concurrency, 'requested_samples': args.samples, 'completed_rounds': 0,
        'network_note': args.network_note,
        'limitations': ['Network note does not independently verify the physical network path.',
                        'API delay does not independently verify the target HTTP status.'],
        'nodes': [],
    }

    def save(status: str) -> None:
        report['status'] = status
        report['finished_at_utc'] = (datetime.datetime.now(datetime.timezone.utc).isoformat()
                                     if status != 'running' else None)
        report['nodes'] = [summarize(row, args.samples, report['completed_rounds']) for row in rows]
        checkpoint(output, report)

    def measure(row: Dict[str, Any]) -> Tuple[Optional[float], Optional[str]]:
        params = urllib.parse.urlencode({'url': args.url, 'timeout': args.timeout_ms})
        path = '/proxies/' + urllib.parse.quote(row['name'], safe='') + '/delay?' + params
        try:
            delay = api.get(path).get('delay')
            if isinstance(delay, bool) or not isinstance(delay, (float, int)) or not math.isfinite(delay) or delay <= 0:
                raise APIError('Invalid or zero delay')
            return delay, None
        except APIError as exc:
            if str(exc) in {'HTTP 401', 'HTTP 403'}:
                raise
            return None, str(exc)

    try:
        save('running')
        report['core_version'] = api.get('/version').get('version')
        config = api.get('/configs')
        reported = config.get('unified-delay')
        if reported is not None and (not isinstance(reported, bool) or reported != report['unified_delay']):
            raise ValueError('API unified-delay differs from the declared configuration')
        if reported is not None:
            report['unified_delay_evidence'] = 'API /configs'
        else:
            report['unified_delay_evidence'] = 'caller-declared; API did not expose field'
        known = api.get('/proxies').get('proxies', {})
        if not isinstance(known, dict):
            raise APIError('Invalid proxy inventory')
        for row in rows:
            node = known.get(row['name'])
            if not isinstance(node, dict) or 'all' in node or str(node.get('type', '')).lower() in {'direct', 'reject', 'pass'}:
                raise ValueError('A target is missing or is a group/built-in outbound')
        save('running')
        for round_index in range(args.samples):
            # 每批最多提交 concurrency 个请求；认证失败时不提交后续请求。
            for start in range(0, len(rows), args.concurrency):
                batch = rows[start:start + args.concurrency]
                pool = concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency)
                pending = {pool.submit(measure, row): row for row in batch}
                recorded = set()
                try:
                    for future in concurrent.futures.as_completed(pending):
                        row = pending[future]
                        delay, error = future.result()
                        row['samples_ms'].append(delay)
                        row['errors'].append(error)
                        recorded.add(future)
                finally:
                    # 中断时保留已完成但尚未从迭代器取出的样本。
                    for future, row in pending.items():
                        if future not in recorded and future.done() and not future.cancelled():
                            try:
                                delay, error = future.result()
                            except APIError as exc:
                                delay, error = None, str(exc)
                            row['samples_ms'].append(delay)
                            row['errors'].append(error)
                        future.cancel()
                    pool.shutdown(wait=False)
            report['completed_rounds'] = round_index + 1
            save('running')
            print('Round {}/{}: {}/{} succeeded'.format(round_index + 1, args.samples,
                  sum(row['samples_ms'][-1] is not None for row in rows), len(rows)), flush=True)
            if round_index + 1 < args.samples:
                time.sleep(0.2)
        save('complete')
        print('Report saved. Verify the physical network path and target HTTP status separately.')
        return 0
    except KeyboardInterrupt:
        save('interrupted')
        print('Interrupted; completed rounds and recorded partial samples were saved.')
        return 130
    except (APIError, ValueError, OSError) as exc:
        save('authorization_error' if isinstance(exc, APIError) and str(exc) in {'HTTP 401', 'HTTP 403'} else 'error')
        if isinstance(exc, (APIError, ValueError)):
            print('Error:', str(exc))
        else:
            print('Error: local input, controller or report operation failed')
        return 1


if __name__ == '__main__':
    def interrupt_on_termination(signum: int, frame: Any) -> None:
        # 主循环捕获 KeyboardInterrupt 后会保留已有轮次。
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupt_on_termination)
    try:
        raise SystemExit(main())
    except (APIError, ValueError, OSError) as exc:
        if isinstance(exc, (APIError, ValueError)) and not isinstance(exc, json.JSONDecodeError):
            print('Error:', str(exc))
        else:
            print('Error: could not read inputs or initialize report')
        raise SystemExit(1)
