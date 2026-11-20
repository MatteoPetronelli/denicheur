# Installe (ou remplace) les tâches planifiées "Denicheur" (collecte) et "DenicheurBot" (bot Telegram) pour
# l'utilisateur courant, sans droits administrateur.
# Usage : powershell -ExecutionPolicy Bypass -File scripts\installer_taches.ps1
$ErrorActionPreference = 'Stop'
$depot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $depot '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { $python = (Get-Command python).Source }
New-Item -ItemType Directory -Force (Join-Path $depot 'logs') | Out-Null

# S4U : la tâche tourne sans fenêtre, ni à l'écran ni dans la barre des tâches, sans mot de passe à saisir.
# Limite : pas d'accès aux ressources réseau avec ton identité (inutile ici, tout est local ou via HTTPS).
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType S4U -RunLevel Limited

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
    -Principal $principal -Force | Out-Null
Get-ScheduledTask -TaskName 'Denicheur' | Select-Object TaskName, State

# Bot Telegram : processus long lancé à l'ouverture de session, relancé s'il s'arrête ; sortie dans logs\bot.log.
$commandeBot = "/c `"`"$python`" -m denicheur bot >> logs\bot.log 2>&1`""
$actionBot = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument $commandeBot -WorkingDirectory $depot
$ouverture = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
$reglagesBot = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName 'DenicheurBot' -Action $actionBot -Trigger $ouverture -Settings $reglagesBot `
    -Principal $principal -Force | Out-Null
Get-ScheduledTask -TaskName 'DenicheurBot' | Select-Object TaskName, State
