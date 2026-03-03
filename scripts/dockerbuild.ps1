#!/usr/bin/env pwsh

param(
  [Parameter(Position=0)]
  [string]$Version = '',
  [Alias('h')]
  [switch]$Help
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Show-Usage {
  @"
用法: .\script\dockerbuild.ps1 [版本标签]
示例: .\script\dockerbuild.ps1 v0.0.3

参数:
  -Version <string>  Git 标签版本 (留空则自动计算)
  -Help              显示帮助
"@ | Write-Host
}

if ($Help) { Show-Usage; exit 0 }

# 彩色日志函数
function Write-Info($msg)    { Write-Host "➤ $msg" -ForegroundColor Blue }
function Write-Success($msg) { Write-Host "✔ $msg" -ForegroundColor Green }
function Write-Warn($msg)    { Write-Host "⚠ $msg" -ForegroundColor Yellow }
function Write-ErrorMsg($msg){ Write-Host "✖ $msg" -ForegroundColor Red }

function Banner {
  Write-Host ('=' * 46) -ForegroundColor Blue
  Write-Host "Docker Tag 发布脚本" -ForegroundColor Blue
  Write-Host "版本: $Version" -ForegroundColor Blue
  Write-Host ('=' * 46) -ForegroundColor Blue
}

function Ensure-Git {
  if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-ErrorMsg '未找到 git 命令，请先安装 Git 并确保在 PATH 中。'
    exit 1
  }
}

# 获取最新标签（按语义版本排序）
function Get-LatestTag {
  try {
    $tags = git tag --list 'v*' --sort=-version:refname
    if (-not $tags) { return $null }
    return ($tags | Select-Object -First 1).Trim()
  } catch {
    return $null
  }
}

# 将尾数 +1：优先识别 vMAJOR.MINOR.PATCH，否则对末尾数字增量
function Bump-Tail([string]$tag) {
  if ([string]::IsNullOrWhiteSpace($tag)) { return 'v0.0.1' }
  $semver = [regex]::Match($tag, '^v(\d+)\.(\d+)\.(\d+)$')
  if ($semver.Success) {
    $a = [int]$semver.Groups[1].Value
    $b = [int]$semver.Groups[2].Value
    $c = ([int]$semver.Groups[3].Value) + 1
    return "v$($a).$($b).$($c)"
  }
  $general = [regex]::Match($tag, '^(.*?)(\d+)$')
  if ($general.Success) {
    $prefix = $general.Groups[1].Value
    $n = ([int]$general.Groups[2].Value) + 1
    return "$prefix$n"
  }
  return "$tag-1"
}

try {
  Ensure-Git

  # 若未显式传入版本参数，则依据最新标签自动计算
  $VersionProvided = $PSBoundParameters.ContainsKey('Version') -and -not [string]::IsNullOrWhiteSpace($Version)
  if (-not $VersionProvided) {
    $latest = Get-LatestTag
    if ($latest) {
      Write-Info "检测到当前最新标签: $latest"
      $Version = Bump-Tail $latest
      Write-Info "自动计算版本: $Version"
    } else {
      Write-Warn '未发现任何标签，使用默认 v0.0.1'
      $Version = 'v0.0.1'
    }
  }

  Banner

  Write-Info "创建 Git 标签 $Version"
  $existing = git tag -l $Version | Where-Object { $_ -eq $Version }
  if (-not $existing) {
    $branch = (git branch --show-current).Trim()
    git tag $Version | Out-Null
    Write-Success "标签 $Version 创建成功（分支 $branch）"
  }
  else {
    Write-Warn "标签 $Version 已存在，跳过创建"
  }

  Write-Info "推送标签到远程 origin"
  git push origin $Version | Out-Null
  Write-Success "标签 $Version 推送完成"
}
catch {
  Write-ErrorMsg "脚本执行失败: $($_.Exception.Message)"
  exit 1
}