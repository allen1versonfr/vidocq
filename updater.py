"""GitHub release updates. Tokens stay in memory; notebooks are never touched."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from version import VERSION, REPOSITORY

API = 'https://api.github.com/repos/' + REPOSITORY
MAX_SIZE = 256 * 1024 * 1024
DOWNLOAD_HOSTS = {'api.github.com', 'github.com', 'release-assets.githubusercontent.com', 'objects.githubusercontent.com'}


def version_tuple(value):
    match = re.fullmatch(r'v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)', str(value))
    if not match:
        raise ValueError('Release must use a stable vMAJOR.MINOR.PATCH version.')
    return tuple(map(int, match.groups()))


def checked_url(url):
    p = urlparse(url)
    if p.scheme != 'https' or p.hostname not in DOWNLOAD_HOSTS or p.username or p.password or p.port not in (None, 443):
        raise ValueError('Update redirected outside GitHub’s download servers.')
    return url


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        checked_url(newurl)
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected and urlparse(newurl).hostname != 'api.github.com':
            redirected.remove_header('Authorization')
        return redirected


def open_github(url, token='', binary=False):
    checked_url(url)
    headers = {'User-Agent': 'Vidocq/' + VERSION,
               'Accept': 'application/octet-stream' if binary else 'application/vnd.github+json',
               'X-GitHub-Api-Version': '2022-11-28'}
    if token and urlparse(url).hostname == 'api.github.com':
        headers['Authorization'] = 'Bearer ' + token
    return build_opener(SafeRedirect()).open(Request(url, headers=headers), timeout=25)


def select_release(release, current=VERSION):
    if not isinstance(release, dict) or release.get('draft') or release.get('prerelease'):
        raise ValueError('No stable release is available.')
    tag = release.get('tag_name', '')
    if version_tuple(tag) <= version_tuple(current):
        return None
    assets = [a for a in release.get('assets', []) if a.get('name') == 'Vidocq.exe' and a.get('state') == 'uploaded']
    if len(assets) != 1:
        raise ValueError('This release does not contain exactly one Vidocq.exe download.')
    asset = assets[0]
    digest = asset.get('digest', '')
    if not isinstance(digest, str) or not re.fullmatch(r'sha256:[0-9a-fA-F]{64}', digest):
        raise ValueError('GitHub has not supplied a SHA-256 digest. Try checking again later.')
    size, asset_id = asset.get('size'), asset.get('id')
    if type(size) is not int or not 1024 <= size <= MAX_SIZE or type(asset_id) is not int or asset_id <= 0:
        raise ValueError('Invalid executable size or release asset ID.')
    return {'version': tag.lstrip('v'), 'tag': tag, 'size': size, 'sha256': digest[7:].lower(),
            'asset_url': API + '/releases/assets/' + str(asset_id),
            'notes': str(release.get('body') or '')[:12000]}


def fetch_release(token=''):
    try:
        with open_github(API + '/releases/latest', token) as response:
            raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError('Release metadata is too large.')
        release = json.loads(raw)
        # The original unversioned bootstrap release predates the updater.
        if release.get('tag_name') == 'vidocq-windows':
            return None
        return select_release(release)
    except HTTPError as error:
        if error.code in (401, 404):
            raise ValueError('Repository is private or access was denied. Enter a GitHub token with Contents: read access to allen1versonfr/test.') from None
        if error.code in (403, 429):
            raise ValueError('GitHub rate limit or permission restriction. Try later or use a read-only token.') from None
        raise ValueError('GitHub could not return the release. Try again later.') from None


def verify_executable(path, expected_size, expected_hash):
    path = Path(path)
    if path.stat().st_size != expected_size:
        raise ValueError('Update download is incomplete. Your installed app was not changed.')
    hasher = hashlib.sha256()
    with path.open('rb') as stream:
        head = stream.read(2)
        hasher.update(head)
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            hasher.update(chunk)
    if head != b'MZ' or hasher.hexdigest() != expected_hash:
        raise ValueError('Update verification failed. Your installed app was not changed.')


def download_release(release, destination, token='', progress=lambda count: None):
    destination = Path(destination)
    partial = destination.with_suffix('.partial')
    count, started = 0, time.monotonic()
    try:
        with open_github(release['asset_url'], token, binary=True) as response, partial.open('xb') as output:
            while True:
                if time.monotonic() - started > 300:
                    raise ValueError('Update download timed out. Please try again.')
                chunk = response.read(256 * 1024)
                if not chunk:
                    break
                count += len(chunk)
                if count > release['size']:
                    raise ValueError('Update download exceeded the expected size.')
                output.write(chunk)
                progress(count)
            output.flush()
            os.fsync(output.fileno())
        verify_executable(partial, release['size'], release['sha256'])
        os.replace(partial, destination)
    finally:
        partial.unlink(missing_ok=True)


def replace_retry(source, destination, timeout=30):
    deadline = time.monotonic() + timeout
    while True:
        try:
            os.replace(source, destination)
            return
        except PermissionError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.25)


def wait_for_parent(pid, timeout=120):
    if not pid:
        return
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    handle = kernel.OpenProcess(0x00100000, False, pid)
    if not handle:
        if ctypes.get_last_error() == 87:  # Already exited.
            return
        raise OSError('Cannot wait for the existing application to exit.')
    try:
        if kernel.WaitForSingleObject(handle, timeout * 1000) != 0:
            raise TimeoutError('Existing app did not close. Please restart and try again.')
    finally:
        kernel.CloseHandle(handle)


def apply_update(job_file):
    """Run from a temporary copy of the old executable after the parent exits."""
    job = json.loads(Path(job_file).read_text(encoding='utf-8'))
    target, staged = Path(job['target']), Path(job['staged'])
    backup = target.with_name(target.name + '.previous')
    result = Path(job['result'])
    ready = Path(job['ready'])
    moved, installed, child = False, False, None
    try:
        if not target.is_absolute() or target.suffix.lower() != '.exe' or staged.resolve() == target.resolve():
            raise ValueError('Invalid update paths.')
        verify_executable(staged, job['size'], job['sha256'])
        wait_for_parent(job['parent_pid'])
        # Copy beside the target first, so installation uses an atomic same-volume rename.
        candidate = target.with_name(target.name + '.incoming')
        shutil.copyfile(staged, candidate)
        verify_executable(candidate, job['size'], job['sha256'])
        replace_retry(target, backup)
        moved = True
        replace_retry(candidate, target)
        installed = True
        ready.unlink(missing_ok=True)
        env = dict(os.environ, PYINSTALLER_RESET_ENVIRONMENT='1')
        child = subprocess.Popen([str(target), *job.get('launch_args', []), '--update-ready', str(ready)], cwd=str(target.parent), env=env)
        deadline = time.monotonic() + job.get('ready_timeout', 60)
        while not ready.exists():
            if child.poll() is not None or time.monotonic() >= deadline:
                raise RuntimeError('The new application did not start successfully.')
            time.sleep(0.25)
        result.write_text(json.dumps({'status': 'updated', 'version': job['version']}), encoding='utf-8')
        # Retain one previous executable for manual recovery.
        staged.unlink(missing_ok=True)
        return 0
    except Exception:
        if child and child.poll() is None:
            child.terminate()
            child.wait(timeout=15)
        if moved:
            if installed:
                target.unlink(missing_ok=True)
            replace_retry(backup, target)
        result.write_text(json.dumps({'status': 'failed', 'message': 'Update could not finish. The previous version was preserved. Check folder write permissions and try again.'}), encoding='utf-8')
        if moved:
            subprocess.Popen([str(target), *job.get('launch_args', [])], cwd=str(target.parent), env=dict(os.environ, PYINSTALLER_RESET_ENVIRONMENT='1'))
        return 1


class UpdateManager:
    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)
        self.token = os.environ.get('VIDOCQ_GITHUB_TOKEN', '')
        self.lock = threading.RLock()
        self.release = None
        self.directory = None
        self.state = {'phase': 'idle', 'current': VERSION, 'repository': REPOSITORY,
                      'can_install': os.name == 'nt' and bool(getattr(sys, 'frozen', False)),
                      'message': 'Check GitHub for a newer stable release.', 'downloaded': 0}

    def status(self):
        with self.lock:
            result = dict(self.state)
            if self.release:
                result.update({key: self.release[key] for key in ('version', 'size', 'notes')})
            try:
                result['last_install'] = json.loads((self.data_dir / 'update-result.json').read_text())
            except (OSError, ValueError):
                pass
            return result

    def _set(self, **values):
        with self.lock:
            self.state.update(values)

    def check(self, token=None):
        with self.lock:
            if self.state['phase'] in ('checking', 'downloading', 'applying'):
                raise ValueError('An update operation is already running.')
            if token is not None:
                if not isinstance(token, str) or len(token) > 500 or any(c.isspace() for c in token):
                    raise ValueError('Invalid GitHub token.')
                self.token = token
            if self.directory:
                shutil.rmtree(self.directory, ignore_errors=True)
            self.release, self.directory = None, None
            self._set(phase='checking', message='Checking GitHub…', downloaded=0)
        threading.Thread(target=self._check, daemon=True).start()

    def _check(self):
        try:
            release = fetch_release(self.token)
            with self.lock:
                self.release = release
                self._set(phase='available' if release else 'current', message='A newer version is available.' if release else 'Vidocq is up to date.')
        except Exception as error:
            self._set(phase='error', message=str(error) if isinstance(error, ValueError) else 'Could not connect to GitHub. Check your connection and try again.')

    def download(self):
        with self.lock:
            if self.state['phase'] != 'available' or not self.release:
                raise ValueError('Check for an available update first.')
            if not self.state['can_install']:
                raise ValueError('In-app installation is available in the Windows Vidocq.exe build.')
            self.directory = Path(tempfile.mkdtemp(prefix='Vidocq-update-'))
            self._set(phase='downloading', message='Downloading and verifying…', downloaded=0)
        threading.Thread(target=self._download, daemon=True).start()

    def _download(self):
        try:
            download_release(self.release, self.directory / 'Vidocq.exe', self.token,
                             lambda count: self._set(downloaded=count))
            self._set(phase='ready', message='Verified. Ready to install and restart.')
        except Exception as error:
            shutil.rmtree(self.directory, ignore_errors=True)
            self._set(phase='error', message=str(error) if isinstance(error, ValueError) else 'Download failed. Check access and connection, then check for updates again.')

    def install(self):
        with self.lock:
            if self.state['phase'] != 'ready' or not self.state['can_install']:
                raise ValueError('Download and verify an update first.')
            target = Path(sys.executable).resolve()
            self.data_dir.mkdir(parents=True, exist_ok=True)
            job = dict(self.release, target=str(target), staged=str(self.directory / 'Vidocq.exe'),
                       parent_pid=os.getpid(), ready=str(self.directory / 'started'),
                       result=str(self.data_dir / 'update-result.json'))
            # A temporary copy can run while the actual installed EXE is replaced.
            helper = self.directory / 'Vidocq-updater.exe'
            shutil.copyfile(target, helper)
            job_file = self.directory / 'job.json'
            job_file.write_text(json.dumps(job), encoding='utf-8')
            env = dict(os.environ)
            env['PYINSTALLER_RESET_ENVIRONMENT'] = '1'
            subprocess.Popen([str(helper), '--apply-update', str(job_file)], env=env,
                             creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            self._set(phase='applying', message='Closing Vidocq to install the update…')
