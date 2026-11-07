# push.ps1 - push the 00 project folder (lsl-core-story-prompt) to its GitHub repo.
# ASCII only. Run it through "shuangji-tuisong" .bat (double click). Never force-pushes.
#
# What it does:
#   1. Reads the repo URL from repo.txt and the version from lsl-core-story-prompt\SKILL.md.
#   2. Finds a working route: system proxy -> local proxy ports (http / socks5h) -> direct.
#   3. Safety: if the version tag is already on the remote -> "Already done" and stop.
#      If the remote main has commits this folder does not have -> STOP (no force push).
#   4. Makes one commit for this version (message from msg\vX.Y.Z.txt) and an annotated tag.
#   5. Shows the commit list and waits for Y. Then pushes main and the tag (4 tries each).
#
# Test switches (not needed for normal use):
#   -Yes                  do not ask, push directly
#   $env:LCSP_REMOTE      override the remote URL (for a local test repo)
#   $env:LCSP_NOPROXY=1   skip proxy detection, go direct

param([switch]$Yes)
$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; $OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

$Here = $PSScriptRoot
$Root = Split-Path -Parent $Here
$SkillMd = Join-Path (Join-Path $Root 'lsl-core-story-prompt') 'SKILL.md'
$Changelog = Join-Path (Join-Path $Root 'lsl-core-story-prompt') 'CHANGELOG.md'
$LogDir = Join-Path $Here 'log'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
try { Start-Transcript -Path (Join-Path $LogDir ("push-" + $Stamp + ".txt")) -Append | Out-Null } catch {}

function Say($t) { Write-Host $t }
function Fail($t) { Write-Host ""; Write-Host ("STOP: " + $t) -ForegroundColor Red; try { Stop-Transcript | Out-Null } catch {}; exit 1 }

# ---------- 0. git and inputs ----------
$gitCmd = Get-Command git -ErrorAction SilentlyContinue
if (-not $gitCmd) { Fail "git is not installed (or not on PATH)." }

$URL = ''
if ($env:LCSP_REMOTE) { $URL = $env:LCSP_REMOTE }
else {
  $RepoFile = Join-Path $Here 'repo.txt'
  if (-not (Test-Path $RepoFile)) { Fail "repo.txt not found next to push.ps1." }
  foreach ($line in (Get-Content -Path $RepoFile -Encoding UTF8)) {
    $l = $line.Trim()
    if ($l -match '^(https://|git@|ssh://|file://)') { $URL = $l; break }
  }
}
if (-not $URL) { Fail "No repo URL in repo.txt (one line starting with https://)." }

if (-not (Test-Path $SkillMd)) { Fail "lsl-core-story-prompt\SKILL.md not found." }
$Ver = ''
foreach ($line in (Get-Content -Path $SkillMd -Encoding UTF8)) {
  if ($line -match '^# lsl core story prompt v(\d+\.\d+\.\d+)') { $Ver = $Matches[1]; break }
}
if (-not $Ver) { Fail "Cannot read the version from the title line of SKILL.md." }
$Tag = "v" + $Ver
$MsgFile = Join-Path (Join-Path $Here 'msg') ($Tag + '.txt')
if (-not (Test-Path $MsgFile)) { Fail ("Commit message file msg\" + $Tag + ".txt is missing.") }

$RelDate = ''
if (Test-Path $Changelog) {
  $cl = Get-Content -Path $Changelog -Encoding UTF8 -Raw
  $pat = '## v' + [regex]::Escape($Ver) + '\D{0,6}(\d{4}-\d{2}-\d{2})'
  if ($cl -match $pat) { $RelDate = $Matches[1] }
}

Say "=============================================="
Say (" Project : " + $Root)
Say (" Remote  : " + $URL)
Say (" Version : " + $Tag + $(if ($RelDate) { "  (release date " + $RelDate + ")" } else { "" }))
Say "=============================================="

# ---------- 1. route (proxy) ----------
function Test-Port([int]$p) {
  try {
    $c = New-Object System.Net.Sockets.TcpClient
    $a = $c.BeginConnect('127.0.0.1', $p, $null, $null)
    $ok = $a.AsyncWaitHandle.WaitOne(300) -and $c.Connected
    $c.Close(); return $ok
  } catch { return $false }
}
function Test-Route($proxy) {
  for ($i = 1; $i -le 2; $i++) {
    if ($proxy) { & git -c ("http.proxy=" + $proxy) -c http.lowSpeedLimit=1000 -c http.lowSpeedTime=20 ls-remote $URL HEAD *> $null }
    else { & git -c http.lowSpeedLimit=1000 -c http.lowSpeedTime=20 ls-remote $URL HEAD *> $null }
    if ($LASTEXITCODE -ne 0) { return $false }
  }
  return $true
}
$Proxy = $null; $Found = $false
if ($env:LCSP_NOPROXY -eq '1') {
  if (Test-Route $null) { $Found = $true }
} else {
  $cands = New-Object System.Collections.ArrayList
  try {
    $ie = Get-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -ErrorAction Stop
    if ($ie.ProxyEnable -eq 1 -and $ie.ProxyServer) {
      $ps = [string]$ie.ProxyServer
      if ($ps -match 'https=([^;]+)') { $ps = $Matches[1] } elseif ($ps -match 'http=([^;]+)') { $ps = $Matches[1] }
      if ($ps -notmatch '://') { $ps = 'http://' + $ps }
      [void]$cands.Add($ps)
    }
  } catch {}
  foreach ($p in @(7890, 7897, 7891, 10809, 10808, 1080)) {
    if (Test-Port $p) { [void]$cands.Add("http://127.0.0.1:" + $p); [void]$cands.Add("socks5h://127.0.0.1:" + $p) }
  }
  foreach ($c in $cands) {
    Say ("Trying route: " + $c)
    if (Test-Route $c) { $Proxy = $c; $Found = $true; break }
  }
  if (-not $Found) { Say "Trying route: direct"; if (Test-Route $null) { $Found = $true } }
}
if (-not $Found) { Fail "Cannot reach the remote. Open Clash (127.0.0.1:7890) and check that the repo exists and you are signed in to GitHub, then run again." }
Say ("Route OK: " + $(if ($Proxy) { $Proxy } else { "direct" }))
$PX = @(); if ($Proxy) { $PX = @('-c', ("http.proxy=" + $Proxy)) }

# ---------- 2. already done? ----------
$remoteTag = & git @PX ls-remote --tags $URL ("refs/tags/" + $Tag)
if ($LASTEXITCODE -ne 0) { Fail "ls-remote for tags failed." }
if ($remoteTag) { Say ""; Say ("Already done: " + $Tag + " is already on the remote. Nothing to push."); try { Stop-Transcript | Out-Null } catch {}; exit 0 }

# ---------- 3. local repo ----------
Set-Location -Path $Root
if (-not (Test-Path (Join-Path $Root '.git'))) {
  Say "No local repo here yet: git init"
  & git init -q
  & git symbolic-ref HEAD refs/heads/main
}
& git config core.quotepath false
$hasOrigin = (& git remote) -contains 'origin'
if ($hasOrigin) { & git remote set-url origin $URL } else { & git remote add origin $URL }

& git @PX fetch -q --tags origin
if ($LASTEXITCODE -ne 0) { Fail "git fetch failed." }
$RemoteMain = (& git rev-parse --verify --quiet refs/remotes/origin/main 2>$null)
$lsMain = (& git @PX ls-remote $URL refs/heads/main)
if ($lsMain -and -not $RemoteMain) { Fail "The remote has a main branch but it could not be fetched into this folder. Not pushing. Tell Claude." }
if ($lsMain -and $RemoteMain -and (-not ([string]$lsMain).StartsWith([string]$RemoteMain))) { Fail "The fetched main does not match the remote main. Run again; if it repeats, tell Claude." }
$LocalHead = (& git rev-parse --verify --quiet HEAD 2>$null)

if ($RemoteMain) {
  if (-not $LocalHead) {
    Say "Remote already has commits (for example a README made on GitHub). Building on top of them."
    & git reset -q --mixed $RemoteMain
    $gone = (& git ls-files --deleted)
    foreach ($f in $gone) { if ($f) { & git checkout -q $RemoteMain -- $f } }
  } else {
    & git merge-base --is-ancestor $RemoteMain HEAD
    if ($LASTEXITCODE -ne 0) { Fail "The remote main has commits that are not in this folder (someone pushed from elsewhere). Not pushing. Tell Claude." }
  }
}

# ---------- 4. commit and tag ----------
& git add -A
$big = @()
foreach ($f in (& git diff --cached --name-only --diff-filter=AM)) {
  if ($f -and (Test-Path -LiteralPath $f)) { $len = (Get-Item -Force -LiteralPath $f).Length; if ($len -gt 50MB) { $big += ($f + " (" + [math]::Round($len / 1MB) + " MB)") } }
}
if ($big.Count -gt 0) { Fail ("Files over 50 MB, move them out or add them to .gitignore: " + ($big -join ', ')) }

& git diff --cached --quiet
$hasChanges = ($LASTEXITCODE -ne 0)
$LocalHead = (& git rev-parse --verify --quiet HEAD 2>$null)

$aName = ''; $aMail = ''
if ($RemoteMain) { $aName = (& git log -1 --format=%an $RemoteMain); $aMail = (& git log -1 --format=%ae $RemoteMain) }
if (-not $aName) { $aName = (& git config user.name) }
if (-not $aMail) { $aMail = (& git config user.email) }
if (-not $aName) { $aName = 'lisuiliang2026' }
if (-not $aMail) { $aMail = 'lisuiliang2026@users.noreply.github.com' }
$env:GIT_AUTHOR_NAME = $aName; $env:GIT_AUTHOR_EMAIL = $aMail
$env:GIT_COMMITTER_NAME = $aName; $env:GIT_COMMITTER_EMAIL = $aMail
if ($RelDate -and $RelDate -ne (Get-Date -Format 'yyyy-MM-dd')) { $env:GIT_AUTHOR_DATE = ($RelDate + "T12:00:00+08:00") }

$localTag = (& git rev-parse --verify --quiet ("refs/tags/" + $Tag) 2>$null)
if ($hasChanges -or -not $LocalHead) {
  if ($localTag) { Say ("Local tag " + $Tag + " was never pushed and files changed since: moving it."); & git tag -d $Tag | Out-Null }
  & git commit -q -F $MsgFile
  if ($LASTEXITCODE -ne 0) { Fail "git commit failed." }
  & git tag -a $Tag -m ("lsl-core-story-prompt " + $Tag)
  if ($LASTEXITCODE -ne 0) { Fail "git tag failed." }
} elseif (-not $localTag) {
  & git tag -a $Tag -m ("lsl-core-story-prompt " + $Tag)
  if ($LASTEXITCODE -ne 0) { Fail "git tag failed." }
} else {
  $tagCommit = (& git rev-list -n 1 $Tag)
  if ($tagCommit -ne (& git rev-parse HEAD)) { Fail ("Local tag " + $Tag + " points to another commit. Tell Claude.") }
  Say ("Nothing new to commit; pushing the existing commit and tag " + $Tag + ".")
}

# ---------- 5. confirm ----------
Say ""
Say "Commits that will be on the remote main (newest first):"
& git --no-pager log --oneline --decorate -n 10
Say ""
if (-not $Yes) {
  $ans = Read-Host ("Push main and tag " + $Tag + " to " + $URL + " ? Type Y to push")
  if ($ans -ne 'Y' -and $ans -ne 'y') { Say "Cancelled. Nothing was pushed (the local commit stays; running again will reuse it)."; try { Stop-Transcript | Out-Null } catch {}; exit 0 }
}

# ---------- 6. push ----------
function Push-Ref($spec) {
  for ($i = 1; $i -le 4; $i++) {
    Say ("git push " + $spec + "  (try " + $i + " of 4)")
    & git @PX -c http.postBuffer=524288000 -c http.version=HTTP/1.1 push origin $spec
    if ($LASTEXITCODE -eq 0) { return $true }
    Start-Sleep -Seconds 5
  }
  return $false
}
if (-not (Push-Ref 'HEAD:refs/heads/main')) { Fail "Pushing main failed 4 times. If git said 'rejected' or 'non-fast-forward', someone changed the remote: tell Claude. Otherwise check Clash and run again (it is safe to rerun)." }
if (-not (Push-Ref ("refs/tags/" + $Tag + ":refs/tags/" + $Tag))) { Fail ("Main is pushed but the tag " + $Tag + " failed 4 times. Run again (it is safe to rerun).") }

Say ""
Say ("DONE. Pushed main and tag " + $Tag + " to " + $URL)
try { Stop-Transcript | Out-Null } catch {}
exit 0
