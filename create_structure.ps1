$baseDir = "F:\Neurion QPE\The-Neurion-QPE-System"

$directories = @(
    "core\models",
    "core\features",
    "core\integrity",
    "core\synthesis",
    "integrations\ig_markets",
    "integrations\ic_markets",
    "integrations\data_feeds",
    "trading",
    "api\routes",
    "data\market_data",
    "data\models",
    "data\checkpoints",
    "data\logs",
    "ui\dashboard",
    "ui\console",
    "tests\unit",
    "tests\integration",
    "tests\simulation",
    "docs",
    "deployment\docker",
    "deployment\monitoring",
    "config\profiles",
    "scripts"
)

foreach ($dir in $directories) {
    $fullPath = Join-Path $baseDir $dir
    New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
    Write-Host "Created: $dir" -ForegroundColor Green
}

Write-Host "`n✅ All directories created successfully!" -ForegroundColor Cyan
