param(
    [switch]$SkipBuilderReset,
    [switch]$SkipImagePull,
    [switch]$SkipFallbackBuild,
    [switch]$SkipSmokeTests,
    [switch]$Tidy,
    [switch]$TidySoft,
    [switch]$TidyHard,
    [switch]$Interactive,
    [string]$BuilderName = "cursor-builder",
    [string]$RootImageTag = "poc-root-fallback",
    [string]$BackendImageTag = "poc-backend-fallback"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "=== $Title ===" -ForegroundColor Cyan
}

function Require-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found on PATH: $Name"
    }
}

function Cleanup-DevcontainerCache {
    $cachePath = Join-Path $env:TEMP "devcontainercli"
    if (Test-Path $cachePath) {
        Remove-Item -Recurse -Force $cachePath
        Write-Host "Cleared: $cachePath"
    } else {
        Write-Host "Cache not found: $cachePath"
    }
}

function Remove-InactiveBuildxBuilders {
    Write-Host "Removing inactive buildx builders."
    docker buildx rm --all-inactive | Out-Null
}

function Remove-FallbackImage {
    param([string]$ImageTag)
    $result = docker images -q $ImageTag 2>$null
    if (-not [string]::IsNullOrWhiteSpace($result)) {
        docker image rm -f $ImageTag | Out-Null
        Write-Host "Removed image: $ImageTag"
    } else {
        Write-Host "Image not found, skipping: $ImageTag"
    }
}

function Run-DeepCleanup {
    param([switch]$Hard)

    Write-Section "Deep cleanup"

    Run-Steady "Clear devcontainer cache" {
        Cleanup-DevcontainerCache
    } -IgnoreFailure

    Run-Steady "Remove inactive buildx builders" {
        Remove-InactiveBuildxBuilders
    } -IgnoreFailure

    if ($Hard) {
        Run-Steady "Remove stale fallback images" {
            Remove-FallbackImage -ImageTag $RootImageTag
            Remove-FallbackImage -ImageTag $BackendImageTag
        } -IgnoreFailure

        Run-Steady "Prune dangling build cache" {
            docker builder prune -f | Out-Null
        } -IgnoreFailure
    }

    Write-Section "Cleanup complete"
}

function Buildx-HasBuilder {
    param([string]$Name)
    $listOutput = docker buildx ls
    $lines = $listOutput -split "`r?`n"

    foreach ($line in $lines) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed -like "NAME*") {
            continue
        }

        if ($trimmed.StartsWith("*")) {
            $trimmed = $trimmed.Substring(1).TrimStart()
        }

        if ($trimmed -eq [string]::Empty) {
            continue
        }

        $parts = $trimmed -split "\s+"
        if ($parts.Count -gt 0 -and $parts[0] -eq $Name) {
            return $true
        }
    }

    return $false
}

function Run-Steady {
    param(
        [string]$Message,
        [scriptblock]$Action,
        [switch]$IgnoreFailure
    )

    Write-Host "-> $Message" -ForegroundColor DarkGray
    try {
        & $Action
    } catch {
        if ($IgnoreFailure) {
            Write-Warning "$Message failed: $($_.Exception.Message)"
        } else {
            throw
        }
    }
}

function Smoke-TestContainer {
    param(
        [string]$Image,
        [string]$Label
    )

    Write-Host ""
    Write-Host "Smoke test: $Label ($Image)" -ForegroundColor Green

    $cmd = @(
        "python3 --version",
        "python3 -m pip --version",
        "az --version | head -n 1",
        "docker --version",
        "echo '[docker ps]'",
        "if [ -S /var/run/docker.sock ]; then docker ps; else echo '[info] docker socket unavailable inside image'; fi"
    ) -join "; "

    docker run --rm $Image sh -lc "$cmd"
}

function Show-RepairMenu {
    Write-Host ""
    Write-Host "==============================" -ForegroundColor Cyan
    Write-Host " Cursor Devcontainer Repair UI " -ForegroundColor Cyan
    Write-Host "==============================" -ForegroundColor Cyan
    Write-Host " 1) Teljes javítás (stabilizálás + fallback rebuild + smoke)"
    Write-Host " 2) Csak stabilizálás (preflight + buildx + cache)"
    Write-Host " 3) Csak fallback rebuild"
    Write-Host " 4) Csak smoke check"
    Write-Host " 5) TidySoft (gyors takarítás)"
    Write-Host " 6) TidyHard (mély takarítás)"
    Write-Host " 0) Kilépés"
    Write-Host ""

    do {
        $selection = Read-Host "Válassz módot [0-6]"
        if ($selection -match "^[0-6]$") {
            return $selection
        }
        Write-Warning "Érvénytelen választás, kérlek 0 és 6 közötti számot adj meg."
    } while ($true)
}

function Apply-InteractiveProfile {
    param([string]$Selection)

    switch ($Selection) {
        "1" {
            Write-Host "Mód: Teljes javítás"
        }
        "2" {
            Write-Host "Mód: Csak stabilizálás"
            $script:SkipFallbackBuild = $true
            $script:SkipSmokeTests = $true
        }
        "3" {
            Write-Host "Mód: Csak fallback rebuild"
            $script:SkipBuilderReset = $true
            $script:SkipSmokeTests = $true
        }
        "4" {
            Write-Host "Mód: Csak smoke check"
            $script:SkipBuilderReset = $true
            $script:SkipImagePull = $true
            $script:SkipFallbackBuild = $true
        }
        "5" {
            Write-Host "Mód: TidySoft"
            $script:TidySoft = $true
        }
        "6" {
            Write-Host "Mód: TidyHard"
            $script:TidyHard = $true
        }
        "0" {
            Write-Host "Kilépés"
            return $false
        }
    }

    return $true
}

# 1) Validate required commands
if ($Interactive) {
    $selection = Show-RepairMenu
    if (-not (Apply-InteractiveProfile -Selection $selection)) {
        return
    }
}

Write-Section "Preflight checks"
Require-Command "docker"
Require-Command "wsl"

Run-Steady "Docker client/server versions" {
    docker version
}

Run-Steady "Buildx plugin versions and status" {
    docker buildx version
    docker buildx ls
}

Run-Steady "WSL status" {
    wsl --status
}

# Optional deep cleanup mode - stop after cleanup.
if ($TidySoft) {
    Run-DeepCleanup
    return
}

if ($Tidy -or $TidyHard) {
    if ($Tidy -and -not $TidyHard) {
        Write-Host " -Tidy detected; using hard cleanup behavior for backward compatibility."
    }

    Run-DeepCleanup -Hard
    return
}

# 2) Optional stabilization steps
Write-Section "Buildx and cache stabilization"
if (-not $SkipBuilderReset) {
    Run-Steady "Create/activate Cursor builder" {
        if (Buildx-HasBuilder -Name $BuilderName) {
            Write-Host "Builder '$BuilderName' already exists, switching to it."
            docker buildx use $BuilderName | Out-Null
        } else {
            Write-Host "Builder '$BuilderName' not found, creating."
            docker buildx create --name $BuilderName --driver docker-container --use | Out-Null
        }
    }

    Run-Steady "Bootstrap buildx builder" {
        docker buildx inspect --bootstrap $BuilderName
    } -IgnoreFailure
}

if (-not $SkipImagePull) {
    Run-Steady "Pull base image" {
        docker pull mcr.microsoft.com/devcontainers/python:3.12
    }
}

Run-Steady "Clear temporary devcontainer cache" {
    Cleanup-DevcontainerCache
} -IgnoreFailure

# 3) Optional fallback path rebuild
if (-not $SkipFallbackBuild) {
    Write-Section "Rebuild fallback Dockerfiles"
    Run-Steady "Build root fallback image" {
        docker build -f .devcontainer/Dockerfile.fallback -t $RootImageTag .
    }
    Run-Steady "Build backend fallback image" {
        docker build -f poc-backend/.devcontainer/Dockerfile.fallback -t $BackendImageTag poc-backend
    }
}

# 4) Smoke checks
if (-not $SkipSmokeTests) {
    Write-Section "Smoke checks in fallback images"
    Smoke-TestContainer -Image $RootImageTag -Label "root (.devcontainer)"
    Smoke-TestContainer -Image $BackendImageTag -Label "backend (poc-backend/.devcontainer)"
}

Write-Section "How to continue"
Write-Host "Root open: use .devcontainer/devcontainer.json (features) or devcontainer.fallback.json if needed."
Write-Host "Backend open: use poc-backend/.devcontainer/devcontainer.json (features) or devcontainer.fallback.json if needed."
Write-Host "If build still fails under features, open the matching .*fallback.json for a local-image path."
