param([Parameter(Mandatory=$true)][string]$Job)
$ErrorActionPreference = 'Stop'
$jobPath = [IO.Path]::GetFullPath($Job)
$task = Get-Content -LiteralPath $jobPath -Raw | ConvertFrom-Json
$helperRoot = [IO.Path]::GetFullPath($task.helper_directory)
if ([IO.Path]::GetDirectoryName($jobPath) -ne $helperRoot -or -not ([IO.Path]::GetFileName($helperRoot).StartsWith('Vidocq-burn-'))) { throw 'Invalid helper scope.' }
function Check-NoLinks([string]$Path) {
    $node = [IO.Path]::GetFullPath($Path)
    while ($node) {
        if (Test-Path -LiteralPath $node) {
            $item = Get-Item -LiteralPath $node -Force
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Reparse point refused.' }
        }
        $parent = [IO.Path]::GetDirectoryName($node)
        if ($parent -eq $node) { break }
        $node = $parent
    }
}
try {
    $targetProcess = Get-Process -Id $task.parent_pid -ErrorAction SilentlyContinue
    if ($targetProcess) { Wait-Process -Id $task.parent_pid -Timeout 90 -ErrorAction Stop }
    $root = [IO.Path]::GetFullPath($task.root)
    Check-NoLinks $root
    $marker = Join-Path $root '.vidocq-owner.json'
    $identity = Get-Content -LiteralPath $marker -Raw | ConvertFrom-Json
    if ($identity.application -ne 'Vidocq' -or $identity.id -ne $task.owner) { throw 'Ownership mismatch.' }
    $allowed = @('workspace.sqlite3','workspace.sqlite3-wal','workspace.sqlite3-shm','workspace.sqlite3-journal','startup.log','update-result.json','.vidocq-owner.json')
    foreach ($file in $task.files) {
        $path = [IO.Path]::GetFullPath($file.path)
        if ([IO.Path]::GetDirectoryName($path) -ne $root -or [IO.Path]::GetFileName($path) -notin $allowed) { throw 'File outside owned scope.' }
        Check-NoLinks $path
    }
    if ($task.executable) {
        $primary = [IO.Path]::GetFullPath($task.executable.path)
        if ([IO.Path]::GetExtension($primary) -ne '.exe') { throw 'Invalid executable scope.' }
        foreach ($entry in $task.executable_files) {
            $exePath = [IO.Path]::GetFullPath($entry.path)
            if ($exePath -ne $primary -and $exePath -ne ($primary + '.previous')) { throw 'Executable outside previewed scope.' }
            Check-NoLinks $exePath
            $digest = [Security.Cryptography.SHA256]::Create()
            $stream = [IO.File]::OpenRead($exePath)
            try { $hash = [BitConverter]::ToString($digest.ComputeHash($stream)).Replace('-', '').ToLowerInvariant() }
            finally { $stream.Dispose(); $digest.Dispose() }
            if ($hash -ne $entry.sha256) { throw 'Executable identity mismatch.' }
        }
        foreach ($entry in $task.executable_files) {
            $exePath = [IO.Path]::GetFullPath($entry.path)
            # The one-file bootloader can outlive the Python parent briefly.
            for ($attempt = 0; $attempt -lt 60; $attempt++) {
                try { Remove-Item -LiteralPath $exePath -Force; break }
                catch { if ($attempt -eq 59) { throw }; Start-Sleep -Seconds 1 }
            }
        }
    }
    foreach ($file in $task.files) {
        if (Test-Path -LiteralPath $file.path) { Remove-Item -LiteralPath $file.path -Force }
    }
    if (@(Get-ChildItem -LiteralPath $root -Force).Count -eq 0) { Remove-Item -LiteralPath $root }
    Remove-Item -LiteralPath $jobPath -Force
    Remove-Item -LiteralPath $PSCommandPath -Force
    if (@(Get-ChildItem -LiteralPath $helperRoot -Force).Count -eq 0) { Remove-Item -LiteralPath $helperRoot }
} catch {
    # Preserve actionable failure information rather than claiming erasure.
    [IO.File]::WriteAllText((Join-Path $helperRoot 'failure.txt'), 'Vidocq burn did not fully complete. Review the previewed paths. ' + $_.Exception.Message)
}
