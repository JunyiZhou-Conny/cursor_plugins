"""No paid calls. Synthetic GLBs and mocked HTTP only."""
import io
import json
import hashlib
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import asset_tools as t


def glb(doc=None):
    if doc is None:
        doc = {'asset': {'version': '2.0'},
               'accessors': [{'count': 3}],
               'meshes': [{'primitives': [{'attributes': {'POSITION': 0}}]}],
               'nodes': [{'name': 'eye_candidate', 'mesh': 0}],
               'scenes': [{'nodes': [0]}]}
    raw = json.dumps(doc).encode()
    raw += b' ' * ((-len(raw)) % 4)
    return struct.pack('<4sII', b'glTF', 2, len(raw) + 20) + struct.pack('<II', len(raw), 0x4E4F534A) + raw


def asset(id='model', path='assets/model/original.glb', **kw):
    a = {'id': id, 'role': 'model', 'format': 'glb', 'local_path': path,
         'url': None, 'expected_bytes': None, 'expected_sha256': None,
         'required': True, 'package_include': True, 'privacy': 'project_asset',
         'source': {'kind': 'synthetic_test'}}
    a.update(kw)
    return a


class ToolsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def put(self, relative, data):
        p = self.root / relative
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return p

    def manifest(self, rows):
        p = self.root / 'ASSETS.json'
        p.write_text(t.dump({'schema_version': '1.0', 'run_id': 'synthetic',
                             'allowed_download_hosts': ['*.fal.media'], 'assets': rows}))
        return p

    def test_init(self):
        run = self.root / 'new'
        t.init_project(run)
        state = json.loads((run / 'RUN_STATE.json').read_text())
        self.assertEqual(state['phase'], 'DRAFT')
        self.assertIsNone(state['authorization']['cap'])
        self.assertIsNone(state['active_job'])
        self.assertTrue((run / 'HANDOFF.md').exists())
        t.read_manifest(run / 'ASSETS.json', run)

    def test_init_never_overwrites(self):
        with self.assertRaises(ValueError):
            t.init_project(self.root)

    def test_path_traversal(self):
        for s in ('../outside', 'a/../../x', '/etc/passwd', 'C:/x', 'a\\b', ''):
            with self.subTest(s=s), self.assertRaises(ValueError):
                t.safe_path(self.root, s)

    def test_path_symlink(self):
        (self.root / 'link').symlink_to('/tmp', target_is_directory=True)
        with self.assertRaises(ValueError):
            t.safe_path(self.root, 'link/escape.txt')

    def test_allowed_host(self):
        t.url_allowed('https://v3b.fal.media/files/example.glb', ['*.fal.media'])

    def test_host_suffix_attack(self):
        with self.assertRaises(ValueError):
            t.url_allowed('https://v3b.fal.media.evil.test/x', ['*.fal.media'])

    def test_http_and_credentials_and_port(self):
        for u in ('http://v3b.fal.media/x', 'https://user:secret@v3b.fal.media/x',
                  'https://v3b.fal.media:8080/x'):
            with self.subTest(u=u), self.assertRaises(ValueError):
                t.url_allowed(u, ['*.fal.media'])

    def test_local_ip(self):
        with self.assertRaises(ValueError):
            t.url_allowed('https://127.0.0.1/x', ['127.0.0.1'])

    def test_exact_host(self):
        t.url_allowed('https://assets.example.com/a.glb', ['assets.example.com'])
        with self.assertRaises(ValueError):
            t.url_allowed('https://x.assets.example.com/a.glb', ['assets.example.com'])

    def test_redirect_checked(self):
        handler = t.CheckedRedirect(['*.fal.media'])
        with self.assertRaises(ValueError):
            handler.redirect_request(None, None, 302, 'Found', {}, 'https://evil.test/x')

    def test_inspect_glb(self):
        p = self.put('x.glb', glb())
        r = t.inspect_glb(p)
        self.assertEqual(r['total_triangle_count_metadata'], 1)
        self.assertEqual(r['counts']['meshes'], 1)
        self.assertEqual(r['eye_name_candidates'], ['eye_candidate'])
        self.assertIn('metadata_inventory_only', r['inspection_kind'])

    def test_bad_header(self):
        p = self.put('x.glb', b'<html>error</html>')
        with self.assertRaises(ValueError):
            t.inspect_glb(p)

    def test_length_mismatch(self):
        p = self.put('x.glb', glb() + b'extra')
        with self.assertRaises(ValueError):
            t.inspect_glb(p)

    def test_missing_json(self):
        p = self.put('x.glb', struct.pack('<4sII', b'glTF', 2, 12))
        with self.assertRaises(ValueError):
            t.inspect_glb(p)

    def test_external_resources_not_fetched(self):
        p = self.put('x.glb', glb({'asset': {'version':'2.0'}, 'images': [{'uri':'texture.png'},{'uri':'data:image/png;base64,x'}]}))
        r = t.inspect_glb(p)
        self.assertEqual(r['resource_uris'][0]['kind'], 'external')
        self.assertEqual(r['resource_uris'][1]['uri'], '(embedded data URI)')

    def test_invalid_accessor(self):
        p = self.put('x.glb', glb({'meshes':[{'primitives':[{'indices':900}]}]}))
        with self.assertRaises(ValueError):
            t.inspect_glb(p)

    def test_validate_expected_hash(self):
        data = glb()
        p = self.put('x.glb', data)
        a = asset(expected_bytes=len(data), expected_sha256=hashlib.sha256(data).hexdigest())
        self.assertTrue(t.validate_file(p, a)['expected_hash_matched'])

    def test_local_hash_not_official(self):
        p = self.put('x.glb', glb())
        self.assertFalse(t.validate_file(p, asset())['expected_hash_matched'])

    def test_bad_hash(self):
        p = self.put('x.glb', glb())
        with self.assertRaises(ValueError):
            t.validate_file(p, asset(expected_sha256='0'*64))

    def test_download_skips_existing(self):
        p = self.put('assets/model/original.glb', glb())
        with patch('urllib.request.build_opener') as mocked:
            r = t.download_one(asset(), self.root, ['*.fal.media'])
            mocked.assert_not_called()
            self.assertEqual(r['status'], 'already_present')

    def test_download_missing_url(self):
        self.assertEqual(t.download_one(asset(), self.root, ['*.fal.media'])['status'], 'missing_no_url')

    def response(self, data):
        response = MagicMock()
        response.__enter__.return_value = response
        response.geturl.return_value = 'https://v3b.fal.media/files/synthetic.glb'
        response.headers = {'Content-Length': str(len(data))}
        response.read.side_effect = io.BytesIO(data).read
        return response

    def test_download_atomic_mock(self):
        data = glb()
        opener = MagicMock()
        opener.open.return_value = self.response(data)
        a = asset(url='https://v3b.fal.media/files/synthetic.glb', expected_bytes=len(data))
        with patch('urllib.request.build_opener', return_value=opener):
            r = t.download_one(a, self.root, ['*.fal.media'])
        self.assertEqual(r['status'], 'downloaded')
        self.assertEqual((self.root / a['local_path']).read_bytes(), data)
        self.assertEqual(list(self.root.rglob('*.part')), [])

    def test_bad_download_not_committed(self):
        opener = MagicMock(); opener.open.return_value = self.response(b'<html>oops</html>')
        a = asset(url='https://v3b.fal.media/files/synthetic.glb')
        with patch('urllib.request.build_opener', return_value=opener), self.assertRaises(ValueError):
            t.download_one(a, self.root, ['*.fal.media'])
        self.assertFalse((self.root / a['local_path']).exists())
        self.assertEqual(list(self.root.rglob('*.part')), [])

    def test_download_cap(self):
        a = asset(url='https://v3b.fal.media/files/synthetic.glb', expected_bytes=10000)
        with self.assertRaises(ValueError):
            t.download_one(a, self.root, ['*.fal.media'], max_bytes=10)

    def test_download_existing_invalid_no_overwrite(self):
        self.put('assets/model/original.glb', b'broken')
        with self.assertRaises(ValueError):
            t.download_one(asset(), self.root, ['*.fal.media'])
        self.assertEqual((self.root / 'assets/model/original.glb').read_bytes(), b'broken')

    def test_duplicate_manifest(self):
        p = self.manifest([asset(), asset()])
        with self.assertRaises(ValueError):
            t.read_manifest(p, self.root)

    def test_reserved_manifest(self):
        p = self.manifest([asset(path='DOWNLOADS.html')])
        with self.assertRaises(ValueError):
            t.read_manifest(p, self.root)

    def test_manifest_requires_privacy(self):
        a=asset(); del a['privacy']
        with self.assertRaises(ValueError):
            t.read_manifest(self.manifest([a]), self.root)

    def test_pack_partial_truthful(self):
        a = asset(url='https://v3b.fal.media/files/synthetic.glb')
        result=t.package(self.manifest([a]), self.root, self.root / 'partial.zip')
        self.assertEqual(result['archive_completeness'], 'partial')
        with ZipFile(self.root / 'partial.zip') as z:
            self.assertNotIn(a['local_path'], z.namelist())
            self.assertIn('remote_only', z.read('DOWNLOADS.html').decode())
            self.assertEqual(json.loads(z.read('PACKAGE_MANIFEST.json'))['missing_required_local_files'], ['model'])

    def test_pack_complete_and_checksum(self):
        self.put('assets/model/original.glb', glb())
        out=self.root/'full.zip'
        r=t.package(self.manifest([asset()]), self.root, out)
        self.assertEqual(r['archive_completeness'], 'all_selected_required_files_present')
        with ZipFile(out) as z:
            self.assertEqual(z.read('assets/model/original.glb'), glb())
            for line in z.read('CHECKSUMS.sha256').decode().splitlines():
                h,n=line.split('  ',1)
                self.assertEqual(hashlib.sha256(z.read(n)).hexdigest(), h)
        self.assertTrue(out.with_suffix('.zip.sha256').exists())

    def test_exclude_private_and_secret_no_url_leak(self):
        rows=[asset(id='private', path='photos/private.png',format='png',privacy='private_reference',required=False,
                    url='https://v3b.fal.media/private-secret-reference.png'),
              asset(id='key',path='.env',format='txt',privacy='shareable_document',required=False)]
        self.put('photos/private.png', b'\x89PNG\r\n\x1a\ncontent')
        self.put('.env', b'SECRET_SENTINEL')
        out=self.root/'safe.zip';t.package(self.manifest(rows),self.root,out)
        with ZipFile(out) as z:
            alltext=b''.join(z.read(n) for n in z.namelist())
            self.assertNotIn(b'SECRET_SENTINEL',alltext)
            self.assertNotIn(b'private-secret-reference',alltext)
            self.assertNotIn('.env',z.namelist())

    def test_include_private_explicit(self):
        row=asset(id='private',path='ref.png',format='png',privacy='private_reference')
        self.put('ref.png',b'\x89PNG\r\n\x1a\ncontent')
        out=self.root/'private.zip';t.package(self.manifest([row]),self.root,out,True)
        with ZipFile(out) as z:self.assertIn('ref.png',z.namelist())

    def test_no_archive_overwrite(self):
        self.put('x.zip',b'keep')
        with self.assertRaises(ValueError):
            t.package(self.manifest([]),self.root,self.root/'x.zip')

    def test_pack_hash_mismatch(self):
        self.put('assets/model/original.glb',glb())
        with self.assertRaises(ValueError):
            t.package(self.manifest([asset(expected_sha256='0'*64)]),self.root,self.root/'bad.zip')
        self.assertFalse((self.root/'bad.zip').exists())

    def test_download_page_escapes_html(self):
        page=t.download_page([{'id':'<script>alert(1)</script>','local_path':'x.glb','status':'remote_only',
                              'url':'javascript:alert(1)'}])
        self.assertNotIn('<script>alert',page)
        self.assertNotIn('href="javascript:',page)


if __name__ == '__main__':
    unittest.main()
