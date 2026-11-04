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
    $allowed = @('workspace.sqlite3','workspace.sqlite3-wal','workspace.sqlite3-shm','workspace.sqlite3-journal','startup.log','update-result.json','.vidocq-owner.json','local-ai.json','local-ai.json.part','credentials.dpapi','credentials.dpapi.part','automations.json','automations.json.part','browser-relay.json','checker-health.json','checker-health.json.part','search-connection.json','search-connection.json.part')
    $allowed += @('local-ai/runtime.zip','local-ai/runtime.zip.part','local-ai/installed.json','local-ai/installed.json.part','local-ai/Qwen3-4B-Instruct-2507-Q4_K_M.gguf','local-ai/Qwen3-4B-Instruct-2507-Q4_K_M.gguf.part','local-ai/runtime/ggml-vulkan.dll','local-ai/runtime/ggml-vulkan.dll.part','local-ai/runtime/libomp.dll','local-ai/runtime/libomp.dll.part','local-ai/runtime/llama-server-impl.dll','local-ai/runtime/llama-server-impl.dll.part','local-ai/runtime/llama-common.dll','local-ai/runtime/llama-common.dll.part','local-ai/runtime/ggml-cpu-cooperlake.dll','local-ai/runtime/ggml-cpu-cooperlake.dll.part','local-ai/runtime/ggml-cpu-sse42.dll','local-ai/runtime/ggml-cpu-sse42.dll.part','local-ai/runtime/ggml-cpu-zen4.dll','local-ai/runtime/ggml-cpu-zen4.dll.part','local-ai/runtime/ggml-cpu-haswell.dll','local-ai/runtime/ggml-cpu-haswell.dll.part','local-ai/runtime/ggml-cpu-sandybridge.dll','local-ai/runtime/ggml-cpu-sandybridge.dll.part','local-ai/runtime/LICENSE-LLVM-OpenMP','local-ai/runtime/LICENSE-LLVM-OpenMP.part','local-ai/runtime/ggml-base.dll','local-ai/runtime/ggml-base.dll.part','local-ai/runtime/llama-server.exe','local-ai/runtime/llama-server.exe.part','local-ai/runtime/ggml-cpu-ivybridge.dll','local-ai/runtime/ggml-cpu-ivybridge.dll.part','local-ai/runtime/ggml-cpu-cascadelake.dll','local-ai/runtime/ggml-cpu-cascadelake.dll.part','local-ai/runtime/llama.dll','local-ai/runtime/llama.dll.part','local-ai/runtime/ggml.dll','local-ai/runtime/ggml.dll.part','local-ai/runtime/ggml-cpu-piledriver.dll','local-ai/runtime/ggml-cpu-piledriver.dll.part','local-ai/runtime/mtmd.dll','local-ai/runtime/mtmd.dll.part','local-ai/runtime/ggml-cpu-icelake.dll','local-ai/runtime/ggml-cpu-icelake.dll.part','local-ai/runtime/ggml-cpu-cannonlake.dll','local-ai/runtime/ggml-cpu-cannonlake.dll.part','local-ai/runtime/ggml-cpu-sapphirerapids.dll','local-ai/runtime/ggml-cpu-sapphirerapids.dll.part','local-ai/runtime/ggml-cpu-skylakex.dll','local-ai/runtime/ggml-cpu-skylakex.dll.part','local-ai/runtime/ggml-cpu-alderlake.dll','local-ai/runtime/ggml-cpu-alderlake.dll.part','local-ai/runtime/ggml-cpu-x64.dll','local-ai/runtime/ggml-cpu-x64.dll.part')
    foreach ($file in $task.files) {
        $path = [IO.Path]::GetFullPath($file.path)
        $rootPrefix = $root.TrimEnd('\') + '\'
        if (-not $path.StartsWith($rootPrefix, [StringComparison]::OrdinalIgnoreCase)) { throw 'File outside owned scope.' }
        $relative = $path.Substring($rootPrefix.Length).Replace('\', '/')
        $managedHarvester = ($relative -match '^harvester/(runs|schedules)\.sqlite(-wal|-shm|-journal)?$') -or ($relative -match '^harvester/run-artifacts/[0-9a-f-]{36}/evidence\.json(\.tmp)?$')
        if ($relative -notin $allowed -and -not $managedHarvester) { throw 'File outside owned scope.' }
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
    $artifactParents = @($task.files | Where-Object { $_.path -match '[\\/]run-artifacts[\\/][0-9a-f-]{36}[\\/]evidence\.json' } | ForEach-Object { [IO.Path]::GetDirectoryName($_.path) } | Select-Object -Unique)
    foreach ($directory in $artifactParents) {
        Check-NoLinks $directory
        if ((Test-Path -LiteralPath $directory) -and @(Get-ChildItem -LiteralPath $directory -Force).Count -eq 0) { Remove-Item -LiteralPath $directory }
    }
    foreach ($relativeDirectory in @('local-ai/runtime','local-ai','harvester/run-artifacts','harvester','osintgram','photon')) {
        $directory = Join-Path $root $relativeDirectory
        Check-NoLinks $directory
        if ((Test-Path -LiteralPath $directory) -and @(Get-ChildItem -LiteralPath $directory -Force).Count -eq 0) { Remove-Item -LiteralPath $directory }
    }
    if (@(Get-ChildItem -LiteralPath $root -Force).Count -eq 0) { Remove-Item -LiteralPath $root }
    Remove-Item -LiteralPath $jobPath -Force
    Remove-Item -LiteralPath $PSCommandPath -Force
    if (@(Get-ChildItem -LiteralPath $helperRoot -Force).Count -eq 0) { Remove-Item -LiteralPath $helperRoot }
} catch {
    # Preserve actionable failure information rather than claiming erasure.
    [IO.File]::WriteAllText((Join-Path $helperRoot 'failure.txt'), 'Vidocq burn did not fully complete. Review the previewed paths. ' + $_.Exception.Message)
}
