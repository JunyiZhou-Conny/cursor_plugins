#!/usr/bin/env python3
"""Local handoff utilities. No generation API, uploads, credentials, or paid jobs.

Python 3.10+, standard library only. Manifest is an explicit file allowlist.
The GLB inspector is a metadata inventory, NOT a full glTF/geometry validator.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import ipaddress
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import struct
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from zipfile import ZipFile, ZIP_DEFLATED

TEMPLATES = Path(__file__).resolve().parents[1] / 'assets' / 'templates'
PRIVACY = {'shareable_document', 'project_asset', 'private_reference', 'secret', 'unknown'}
RESERVED = {'ASSETS.json', 'PACKAGE_MANIFEST.json', 'DOWNLOADS.html', 'CHECKSUMS.sha256'}
SECRET_PARTS = {'.git', '.ssh', '.aws', '.gnupg', 'node_modules', '__pycache__'}


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def dump(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + '\n'


def safe_path(root: Path, relative: str) -> Path:
    """Reject escapes, ambiguous OS paths, and any existing symlink component."""
    if not isinstance(relative, str) or not relative or '\\' in relative or ':' in relative:
        raise ValueError('local_path must be a nonempty portable relative path')
    p = PurePosixPath(relative)
    if p.is_absolute() or '..' in p.parts or '.' == relative or '\x00' in relative:
        raise ValueError('Unsafe local_path')
    root = root.resolve()
    current = root
    for part in p.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('Symlink paths are not accepted')
    resolved = current.resolve()
    if not resolved.is_relative_to(root) or resolved == root:
        raise ValueError('Path escapes project root')
    return resolved


def secret_path(relative: str) -> bool:
    parts = PurePosixPath(relative).parts
    name = parts[-1].lower()
    return (any(p.lower() in SECRET_PARTS for p in parts)
            or name == '.env' or name.startswith('.env.')
            or name in {'id_rsa', 'id_ed25519', 'credentials', 'credentials.json', 'token.json'}
            or name.endswith(('.pem', '.key', '.p12', '.pfx')))


def read_manifest(path: Path, root: Path) -> dict:
    manifest = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(manifest, dict) or manifest.get('schema_version') != '1.0' or not isinstance(manifest.get('assets'), list):
        raise ValueError('Expected ASSETS manifest schema_version=1.0 and assets array')
    hosts = manifest.get('allowed_download_hosts', [])
    if not isinstance(hosts, list) or any(not isinstance(x, str) or not x for x in hosts):
        raise ValueError('allowed_download_hosts must be a list of explicit host rules')
    ids, paths = set(), set()
    for a in manifest['assets']:
        if (not isinstance(a, dict) or not isinstance(a.get('id'), str)
                or not re.fullmatch(r'[a-z0-9][a-z0-9_-]*', a['id'])):
            raise ValueError('Every asset needs a unique lowercase id')
        if a['id'] in ids:
            raise ValueError('Duplicate asset id')
        ids.add(a['id'])
        rel = a.get('local_path')
        safe_path(root, rel)
        normalized = PurePosixPath(rel).as_posix()
        if normalized in paths or normalized in RESERVED:
            raise ValueError('Duplicate or reserved local_path')
        paths.add(normalized)
        if a.get('privacy') not in PRIVACY:
            raise ValueError('Every asset needs explicit privacy classification')
        for field in ('required', 'package_include'):
            if not isinstance(a.get(field), bool):
                raise ValueError(f'{field} must be boolean')
        n = a.get('expected_bytes')
        if n is not None and (type(n) is not int or n < 1):
            raise ValueError('expected_bytes must be null or a positive integer')
        h = a.get('expected_sha256')
        if h is not None and (not isinstance(h, str) or not re.fullmatch(r'[a-fA-F0-9]{64}', h)):
            raise ValueError('expected_sha256 must be null or a 64-digit hex string')
        if a.get('url') is not None and not isinstance(a['url'], str):
            raise ValueError('url must be a string or null')
    return manifest


def url_allowed(url: str, rules: list[str]) -> str:
    p = urllib.parse.urlsplit(url)
    if (p.scheme != 'https' or not p.hostname or p.username or p.password
            or p.port not in (None, 443)):
        raise ValueError('Only credential-free HTTPS asset URLs on port 443 are accepted')
    host = p.hostname.lower().rstrip('.')
    try:
        if not ipaddress.ip_address(host).is_global:
            raise ValueError('Nonpublic IP addresses are not accepted')
    except ValueError as e:
        if str(e) == 'Nonpublic IP addresses are not accepted':
            raise
    matched = any((host.endswith('.' + r[2:].lower()) if r.startswith('*.')
                   else host == r.lower().rstrip('.')) for r in rules)
    if not matched:
        raise ValueError(f'Host is not explicitly allowed: {host}')
    return url


class CheckedRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, hosts: list[str]):
        super().__init__()
        self.hosts = hosts

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        url_allowed(newurl, self.hosts)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def validate_file(path: Path, asset: dict) -> dict:
    if not path.is_file() or path.is_symlink():
        raise ValueError('Expected a regular file')
    size = path.stat().st_size
    if not size:
        raise ValueError('Empty file')
    if asset.get('expected_bytes') is not None and size != asset['expected_bytes']:
        raise ValueError(f'File size mismatch: got {size}, expected {asset["expected_bytes"]}')
    with path.open('rb') as f:
        head = f.read(256)
    fmt = asset.get('format') or Path(asset['local_path']).suffix.lower().lstrip('.')
    if fmt == 'glb':
        if len(head) < 12 or head[:4] != b'glTF':
            raise ValueError('Not a GLB: possibly an HTML error response')
        _, version, declared = struct.unpack('<4sII', head[:12])
        if version != 2 or declared != size:
            raise ValueError('Invalid GLB version/declared file length')
    elif fmt == 'png' and not head.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('Not a PNG')
    elif fmt in ('jpg', 'jpeg') and not head.startswith(b'\xff\xd8\xff'):
        raise ValueError('Not a JPEG')
    elif fmt in ('avif', 'heif', 'heic') and head[4:8] != b'ftyp':
        raise ValueError('Missing ISO-BMFF ftyp header')
    elif fmt in ('glb', 'obj', 'fbx', 'stl', 'usdz') and head.lstrip().lower().startswith((b'<!doctype html', b'<html')):
        raise ValueError('Received HTML instead of a model')
    h = sha256(path)
    expected = asset.get('expected_sha256')
    if expected and expected.lower() != h:
        raise ValueError('SHA256 does not match the supplied expected value')
    return {'bytes': size, 'sha256': h, 'expected_hash_matched': bool(expected),
            'check_scope': 'file existence, optional size/hash, selected format headers only'}


def download_one(a: dict, root: Path, hosts: list[str], timeout: float = 30,
                 retries: int = 2, max_bytes: int = 1024**3) -> dict:
    target = safe_path(root, a['local_path'])
    if secret_path(a['local_path']) or a['privacy'] in {'secret', 'unknown'}:
        raise ValueError('Refusing secret/unknown asset')
    if target.exists():
        return {'id': a['id'], 'status': 'already_present', **validate_file(target, a)}
    if not a.get('url'):
        return {'id': a['id'], 'status': 'missing_no_url'}
    url_allowed(a['url'], hosts)
    if a.get('expected_bytes', 0) and a['expected_bytes'] > max_bytes:
        raise ValueError('Expected file exceeds configured download cap')
    target.parent.mkdir(parents=True, exist_ok=True)
    opener = urllib.request.build_opener(CheckedRedirect(hosts))
    # Retry only transport problems. This sends GET requests, never generation POSTs.
    last_error = None
    for attempt in range(retries + 1):
        tmp = None
        try:
            fd, tempname = tempfile.mkstemp(prefix=target.name + '.', suffix='.part', dir=target.parent)
            tmp = Path(tempname)
            request = urllib.request.Request(a['url'], headers={'User-Agent': '3D-Asset-Handoff/1.0'})
            with os.fdopen(fd, 'wb') as f:
                with opener.open(request, timeout=timeout) as response:
                    url_allowed(response.geturl(), hosts)
                    content_len = response.headers.get('Content-Length')
                    if content_len and int(content_len) > max_bytes:
                        raise ValueError('Response exceeds configured download cap')
                    total = 0
                    while block := response.read(1024 * 1024):
                        total += len(block)
                        if total > max_bytes:
                            raise ValueError('Download exceeds configured byte cap')
                        f.write(block)
            result = validate_file(tmp, a)
            # Hard-link is same-directory and fails rather than overwriting a racing writer.
            os.link(tmp, target)
            return {'id': a['id'], 'status': 'downloaded', **result}
        except urllib.error.HTTPError as e:
            last_error = f'HTTP {e.code}'
            if e.code not in (408, 429, 500, 502, 503, 504) or attempt == retries:
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last_error = type(e).__name__
            if attempt == retries:
                raise
        finally:
            if tmp is not None:
                tmp.unlink(missing_ok=True)
        time.sleep(min(2 ** attempt, 8))
    raise RuntimeError(last_error or 'Download failed')


def inspect_glb(path: Path) -> dict:
    size = path.stat().st_size
    chunks, doc = [], None
    with path.open('rb') as f:
        hdr = f.read(12)
        if len(hdr) != 12:
            raise ValueError('Truncated GLB header')
        magic, ver, declared = struct.unpack('<4sII', hdr)
        if magic != b'glTF' or ver != 2 or declared != size:
            raise ValueError('Not a length-consistent GLB v2')
        while f.tell() < size:
            h = f.read(8)
            if len(h) != 8:
                raise ValueError('Truncated chunk header')
            n, kind = struct.unpack('<II', h)
            if n % 4 or f.tell() + n > size:
                raise ValueError('Unaligned/truncated GLB chunk')
            if not chunks and kind != 0x4E4F534A:
                raise ValueError('First chunk must be JSON')
            chunks.append({'kind': kind, 'offset': f.tell(), 'bytes': n})
            if kind == 0x4E4F534A:
                if doc is not None or n > 32 * 1024 * 1024:
                    raise ValueError('Duplicate or oversized JSON chunk')
                doc = json.loads(f.read(n).decode('utf-8'))
            else:
                f.seek(n, 1)
    if not isinstance(doc, dict):
        raise ValueError('Missing JSON object')
    accessors = doc.get('accessors', [])
    def count(i):
        if i is None:
            return None
        if type(i) is not int or not 0 <= i < len(accessors):
            raise ValueError('Invalid accessor index')
        n = accessors[i].get('count')
        if type(n) is not int or n < 0:
            raise ValueError('Invalid accessor count')
        return n
    primitives, triangles, unknown = [], 0, False
    for mi, mesh in enumerate(doc.get('meshes', [])):
        for pi, p in enumerate(mesh.get('primitives', [])):
            vc = count(p.get('attributes', {}).get('POSITION'))
            ic = count(p.get('indices'))
            n = ic if ic is not None else vc
            mode = p.get('mode', 4)
            t = (n // 3 if mode == 4 else max(0, n - 2) if mode in (5, 6) else 0) if n is not None else None
            unknown |= t is None
            triangles += t or 0
            primitives.append({'mesh': mi, 'primitive': pi, 'mode': mode,
                               'vertex_count_metadata': vc, 'index_count_metadata': ic,
                               'triangle_count_metadata': t,
                               'extensions': list(p.get('extensions', {}))})
    uris = []
    for group in ('images', 'buffers'):
        for i, o in enumerate(doc.get(group, [])):
            u = o.get('uri')
            if u:
                uris.append({'group': group, 'index': i,
                             'kind': 'data_uri' if u.startswith('data:') else 'external',
                             'uri': '(embedded data URI)' if u.startswith('data:') else u})
    names = [n.get('name', '') for n in doc.get('nodes', [])]
    return {'inspection_kind': 'glb_metadata_inventory_only', 'timestamp': utc(),
            'file_name': path.name, 'bytes': size, 'sha256': sha256(path), 'chunks': chunks,
            'counts': {k: len(doc.get(k, [])) for k in ('nodes', 'meshes', 'materials', 'textures', 'images', 'cameras', 'animations', 'skins')},
            'node_names': names, 'eye_name_candidates': [n for n in names if 'eye' in n.lower()],
            'focus_name_candidates': [n for n in names if n.startswith('focus-')],
            'animation_names': [a.get('name') for a in doc.get('animations', [])],
            'extensions_used': doc.get('extensionsUsed', []),
            'extensions_required': doc.get('extensionsRequired', []),
            'resource_uris': uris, 'primitives': primitives,
            'total_triangle_count_metadata': None if unknown else triangles,
            'limitations': ['Not a full glTF Validator report.', 'No geometry decompression, binary accessor validation, manifold or visual checks.',
                            'Counts describe unique mesh primitives, not instantiated scene totals; degenerate triangles are not removed.',
                            'Eye names do not establish independent eyes or valid pivots.', 'No external resources fetched.']}


def init_project(root: Path) -> dict:
    if root.exists():
        raise ValueError('Project already exists; inspect/resume it rather than overwriting')
    root.mkdir(parents=True)
    for name in ('BRIEF.md', 'RUN_STATE.json', 'ASSETS.json', 'HANDOFF.md', 'NEXT_AGENT_PROMPT.md', 'QA_REPORT.md'):
        shutil.copy2(TEMPLATES / name, root / name)
    for folder in ('evidence', 'assets/model', 'assets/textures', 'assets/preview', 'assets/reference'):
        (root / folder).mkdir(parents=True, exist_ok=True)
    state = json.loads((root / 'RUN_STATE.json').read_text())
    state.update(run_id=root.name, updated_at=utc())
    (root / 'RUN_STATE.json').write_text(dump(state), encoding='utf-8')
    manifest = json.loads((root / 'ASSETS.json').read_text())
    manifest['run_id'] = root.name
    (root / 'ASSETS.json').write_text(dump(manifest), encoding='utf-8')
    return {'status': 'initialized', 'root': str(root), 'note': 'Templates only. No generation, no credentials, no paid call.'}


def download_page(rows: list[dict]) -> str:
    body = []
    for a in rows:
        link = html.escape(a['id'])
        if a['status'] == 'local_included':
            href = urllib.parse.quote(a['local_path'], safe='/')
            link = f'<a href="{href}">{link}</a>'
        elif a.get('url'):
            p = urllib.parse.urlsplit(a['url'])
            if p.scheme == 'https' and p.hostname and not p.username and not p.password:
                link = f'<a rel="noopener noreferrer" referrerpolicy="no-referrer" href="{html.escape(a["url"], quote=True)}">{link}（远程）</a>'
        body.append('<tr><td>' + link + '</td><td>' + html.escape(a['status']) + '</td><td>'
                    + html.escape(str(a.get('bytes', a.get('expected_bytes')) or '未知')) + '</td></tr>')
    return '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>3D 交接下载清单</title><style>body{font:16px/1.7 system-ui;max-width:1000px;margin:40px auto;padding:0 20px}table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #ddd;padding:12px;text-align:left}code{background:#eee}</style>
<h1>三维资产下载与归档清单</h1><p>local_included 为实际进入 ZIP 的文件；remote_only 需要联网另存；missing 表示本地和链接均缺失。</p>
<p>这是私人项目交接，不是公开发布许可。未入包的私密参考不会在此列出；检查 PACKAGE_MANIFEST.json 的排除记录。</p>
<table><thead><tr><th>文件</th><th>状态</th><th>字节数（远程项为报告值）</th></tr></thead><tbody>''' + ''.join(body) + '</tbody></table></html>\n'


def package(manifest_path: Path, root: Path, output: Path, include_private: bool = False) -> dict:
    manifest = read_manifest(manifest_path, root)
    output = output.resolve()
    if output.exists() or output.with_suffix(output.suffix + '.sha256').exists():
        raise ValueError('Output/checksum already exists; choose a new version name')
    rows, excluded, local, missing = [], [], [], []
    for a in manifest['assets']:
        reason = None
        if not a['package_include']:
            reason = 'not_selected'
        elif secret_path(a['local_path']) or a['privacy'] in {'secret', 'unknown'}:
            reason = 'privacy_or_secret_path'
        elif a['privacy'] == 'private_reference' and not include_private:
            reason = 'private_reference_requires_permission'
        if reason:
            excluded.append({'id': a['id'], 'reason': reason, 'required': a['required']})
            if a['required']:
                missing.append(a['id'])
            continue
        p = safe_path(root, a['local_path'])
        if p == output:
            raise ValueError('Archive cannot contain itself')
        row = dict(a)
        if p.exists():
            info = validate_file(p, a)
            row.update(info, status='local_included')
            local.append((a['local_path'], p))
        else:
            row['status'] = 'remote_only' if a.get('url') else 'missing'
            if a['required']:
                missing.append(a['id'])
        rows.append(row)
    report = {'schema_version': '1.0', 'created_at': utc(), 'run_id': manifest.get('run_id'),
              'archive_scope': 'private_project_handoff_not_publication_approval',
              'archive_completeness': 'partial' if missing else 'all_selected_required_files_present',
              'does_not_certify_model_quality': True, 'missing_required_local_files': missing,
              'assets': rows, 'excluded': excluded}
    clean_manifest = {k: v for k, v in manifest.items() if k != 'assets'}
    clean_manifest['assets'] = [dict(a) for a in rows]
    generated = {
        'ASSETS.json': dump(clean_manifest).encode(),
        'PACKAGE_MANIFEST.json': dump(report).encode(),
        'DOWNLOADS.html': download_page(rows).encode()}
    sums = [f'{sha256(p)}  {name}' for name, p in local]
    sums.extend(f'{hashlib.sha256(data).hexdigest()}  {name}' for name, data in generated.items())
    generated['CHECKSUMS.sha256'] = ('\n'.join(sorted(sums)) + '\n').encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=output.name, suffix='.part', dir=output.parent)
    os.close(fd)
    temp = Path(name)
    try:
        with ZipFile(temp, 'w', ZIP_DEFLATED, compresslevel=5) as z:
            for rel, p in local:
                z.write(p, arcname=rel)
            for rel, data in generated.items():
                z.writestr(rel, data)
        with ZipFile(temp) as z:
            bad = z.testzip()
            if bad:
                raise ValueError(f'ZIP integrity failed: {bad}')
        os.link(temp, output)
    finally:
        temp.unlink(missing_ok=True)
    output.with_suffix(output.suffix + '.sha256').write_text(sha256(output) + '  ' + output.name + '\n', encoding='utf-8')
    return {'status': 'packaged', 'archive': str(output), 'bytes': output.stat().st_size,
            'sha256': sha256(output), 'archive_completeness': report['archive_completeness'],
            'missing_required_local_files': missing, 'excluded_count': len(excluded)}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    c = sub.add_parser('init'); c.add_argument('directory', type=Path)
    c = sub.add_parser('inspect'); c.add_argument('model', type=Path); c.add_argument('--out', type=Path)
    c = sub.add_parser('fetch'); c.add_argument('manifest', type=Path); c.add_argument('--root', type=Path, required=True)
    c.add_argument('--only', nargs='+'); c.add_argument('--timeout', type=float, default=30)
    c.add_argument('--retries', type=int, default=2); c.add_argument('--max-mb', type=int, default=1024)
    c = sub.add_parser('pack'); c.add_argument('manifest', type=Path); c.add_argument('--root', type=Path, required=True)
    c.add_argument('--out', type=Path, required=True); c.add_argument('--include-private', action='store_true',
                   help='Use only with explicit permission to include source/private references')
    a = p.parse_args(argv)
    try:
        code = 0
        if a.command == 'init':
            result = init_project(a.directory.resolve())
        elif a.command == 'inspect':
            result = inspect_glb(a.model)
            if a.out:
                if a.out.exists():
                    raise ValueError('Inspection output already exists; choose a new version')
                a.out.parent.mkdir(parents=True, exist_ok=True)
                a.out.write_text(dump(result), encoding='utf-8')
        elif a.command == 'pack':
            result = package(a.manifest, a.root.resolve(), a.out, a.include_private)
        else:
            if not (0 < a.timeout <= 300 and 0 <= a.retries <= 5 and 0 < a.max_mb <= 8192):
                raise ValueError('Invalid timeout/retries/size limit')
            root = a.root.resolve()
            m = read_manifest(a.manifest, root)
            ids = {x['id'] for x in m['assets']}
            if a.only and set(a.only) - ids:
                raise ValueError('Unknown --only asset id')
            entries = [x for x in m['assets'] if (x['id'] in a.only if a.only else x['required'])]
            results = []
            for entry in entries:
                try:
                    r = download_one(entry, root, m.get('allowed_download_hosts', []), a.timeout, a.retries, a.max_mb * 1000 * 1000)
                except (OSError, ValueError, RuntimeError) as e:
                    # Do not echo token-bearing URLs from HTTP error strings into reports.
                    r = {'id': entry['id'], 'status': 'failed', 'error_type': type(e).__name__,
                         'error': f'HTTP {e.code}' if isinstance(e, urllib.error.HTTPError) else str(e)[:300]}
                results.append(r)
            result = {'timestamp': utc(), 'results': results, 'generation_submissions': 0}
            evidence = safe_path(root, 'evidence')
            evidence.mkdir(parents=True, exist_ok=True)
            dest = evidence / ('downloads_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f') + '.json')
            dest.write_text(dump(result), encoding='utf-8')
            code = 1 if any(x['status'] in {'failed', 'missing_no_url'} for x in results) else 0
        print(dump(result))
        return code
    except (OSError, ValueError, RuntimeError) as e:
        print(f'{type(e).__name__}: {e}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
