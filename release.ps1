# Auto-Release Script mit Version-Bump

$version = Get-Content "version.txt" -Raw
$parts = $version.Trim().Split(".")
$parts[2] = [int]$parts[2] + 1
$newVersion = $parts -join "."

Write-Host "📦 Release v$newVersion" -ForegroundColor Cyan

# Version file aktualisieren
$newVersion | Set-Content "version.txt"

# Git commit
git add version.txt
git commit -m "chore: Version auf v$newVersion bump"

# Git Tag
git tag -a "v$newVersion" -m "Release v$newVersion"

# Push
$env:GIT_SSH_COMMAND="ssh -i $env:USERPROFILE\.ssh\id_ed25519"
git push origin main
git push origin "v$newVersion"

Write-Host "✅ Release v$newVersion erfolgreich!" -ForegroundColor Green
