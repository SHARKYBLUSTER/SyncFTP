' Script VBS pour lancer le serveur Flask sans afficher le terminal
' Auteurs: SHARKYBLUSTER / Mistral Vibe

Set objShell = CreateObject("WScript.Shell")

' Chemin vers le fichier Python (ajuster si nécessaire)
scriptPath = "app.py"

' Vérifie si le serveur est déjà en cours d'exécution sur le port 5000
Set objWMIService = GetObject("winmgmts:\\.\root\cimv2")
Set colProcesses = objWMIService.ExecQuery("SELECT * FROM Win32_Process WHERE CommandLine LIKE '%" & scriptPath & "%'")

If colProcesses.Count > 0 Then
    MsgBox "Le serveur est déjà en cours d'exécution!", vbExclamation, "Serveur FTP"
    WScript.Quit
End If

' Lancer le serveur Python en arrière-plan (fenêtre cachée)
pythonCommand = "python " & scriptPath
objShell.Run pythonCommand, 0, False

' Attendre 2 secondes pour que le serveur démarre
WScript.Sleep 2000

' Vérifier si le serveur a démarré correctement
Set colProcesses = objWMIService.ExecQuery("SELECT * FROM Win32_Process WHERE CommandLine LIKE '%" & scriptPath & "%'")

If colProcesses.Count = 0 Then
    MsgBox "Échec du démarrage du serveur. Vérifiez que Python et les dépendances sont installées.", vbCritical, "Erreur"
Else
    MsgBox "Serveur FTP lancé avec succès!" & vbCrLf & vbCrLf & "Accédez à: http://localhost:5000", vbInformation, "Serveur FTP"
End If
