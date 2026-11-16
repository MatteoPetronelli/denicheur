# Installe (ou remplace) la tâche planifiée "Denicheur" pour l'utilisateur courant, sans droits administrateur.
# Usage : powershell -ExecutionPolicy Bypass -File scripts\installer_taches.ps1
$ErrorActionPreference = 'Stop'
$depot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $depot '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { $python = (Get-Command python).Source }
New-Item -ItemType Directory -Force (Join-Path $depot 'logs') | Out-Null

# La sortie est ajoutée à logs\run.log ; cmd gère la redirection, le dépôt est le répertoire de travail.
$commande = "/c `"`"$python`" -m denicheur run --mode auto >> logs\run.log 2>&1`""
$action = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument $commande -WorkingDirectory $depot
$declencheur = New-ScheduledTaskTrigger -Daily -At '08:30'
$repetition = New-ScheduledTaskTrigger -Once -At '08:30' -RepetitionInterval (New-TimeSpan -Hours 1) `
    -RepetitionDuration (New-TimeSpan -Hours 12)
$declencheur.Repetition = $repetition.Repetition
$reglages = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

# -Force remplace la tâche existante : relancer le script ne crée jamais de doublon.
Register-ScheduledTask -TaskName 'Denicheur' -Action $action -Trigger $declencheur -Settings $reglages `
    -Force | Out-Null
Get-ScheduledTask -TaskName 'Denicheur' | Select-Object TaskName, State
