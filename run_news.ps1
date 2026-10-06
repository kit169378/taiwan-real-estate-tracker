Set-Location C:\Real-estate

# Task Scheduler does not load the normal PATH, so use the full path to claude
$Claude = "C:\Users\User\.local\bin\claude.exe"

# Read claude output as UTF-8 so Chinese text is not garbled in the log
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

if (-not (Test-Path logs)) { New-Item -ItemType Directory -Path logs | Out-Null }
$Log = "logs\news_$(Get-Date -Format 'yyyy-MM-dd_HHmm').log"

"=== start $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" | Out-File -FilePath $Log -Encoding utf8
& $Claude -p (Get-Content prompt_news.md -Raw -Encoding UTF8) --allowedTools "WebSearch,WebFetch,Read,Write" 2>&1 |
    Out-File -FilePath $Log -Encoding utf8 -Append
"=== end $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), exit code $LASTEXITCODE ===" | Out-File -FilePath $Log -Encoding utf8 -Append
