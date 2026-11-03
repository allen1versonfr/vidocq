# Updates and recovery

[← Project overview](../README.md)

## First upgrade

The original portable executable is version 2.2.1 and does not contain an updater. Close it, download the current **Vidocq.exe** from [Releases](https://github.com/allen1versonfr/test/releases/latest), and replace the old executable once. Keep it in a writable folder. Notebook data is stored separately, so replacing the EXE does not remove findings.

## Updating from Vidocq

1. Open **Updates**. Vidocq also checks GitHub at launch.
2. If access is required, enter your GitHub token and select **Check for updates**.
3. Review the available version and release notes, then choose **Download update**.
4. After verification completes, select **Install and restart**. Vidocq closes while a separate helper replaces the executable and starts the new app.

The updater accepts newer stable semantic versions such as `v2.4.0`. It rejects prereleases, drafts, equal/older versions, ambiguous executable assets, invalid sizes, and missing SHA-256 digests. The expected release asset is named exactly **Vidocq.exe**. Source-mode runs can check versions; in-app installation is supported by the frozen Windows executable.

## Access to this private repository

Use a fine-grained GitHub personal access token scoped to `allen1versonfr/test`, with **Contents: read** permission. The token must belong to an account with access to this repository. Enter it only in Vidocq’s Updates field. Never paste it into an issue, source file, screenshot, or pull request.

Vidocq retains a token entered in the app only in memory for the session. It sends the token only to `api.github.com`; authorization is stripped before following a download redirect to GitHub’s allowed download hosts. The token is not written into update-job files or the notebook.

For automatic authenticated checks across launches, you may set **VIDOCQ_GITHUB_TOKEN** as an environment variable on your own machine, then restart Vidocq. That variable is managed by your operating system; it is not encrypted credential storage. Leaving it unset and entering the token per session avoids persistent storage by this method. If the repository becomes public later, unauthenticated checks and downloads can work without a token.

## Verification

Each download must match both GitHub’s expected asset size and its SHA-256 digest. Failed or incomplete downloads are discarded before installation. The release also includes **SHA256SUMS.txt** and **BUILD_INFO.json**.

To check a manual download in PowerShell:

```powershell
Get-FileHash .\Vidocq.exe -Algorithm SHA256
```

Compare the hash with SHA256SUMS.txt from the same release. This checks that the bytes match the published file. It is not a code signature or independent proof that the repository or build environment is trustworthy. Current releases are unsigned.

## Recovery

A copy of the previous executable is kept beside the installed EXE as `Vidocq.exe.previous`. If the new app fails to signal successful startup, the helper attempts to restore and restart the previous version. Recovery can still be affected by permissions, antivirus locks, interrupted power, or operating-system failures.

If manual recovery is needed:

1. Close Vidocq and confirm its processes have exited.
2. Preserve the failed executable under a different name for diagnosis.
3. Copy `Vidocq.exe.previous` to `Vidocq.exe`, or download a known working executable from Releases.
4. Start Vidocq again. Do not delete the notebook database.

Update outcome information is saved to `%LOCALAPPDATA%\Vidocq\update-result.json`. Startup diagnostics are in `startup.log` in the same folder. The Updates tab displays the last recorded installation outcome.

An update will not request administrator access. If the containing folder is protected, move the portable application to a folder your account can write to rather than running the updater elevated.
