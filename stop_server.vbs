' Script VBS pour arrêter le serveur Flask
' Auteurs: SHARKYBLUSTER / Mistral Vibe

Set objShell = CreateObject("WScript.Shell")

' Trouver le PID du processus écoutant sur le port 5000
Set objWMIService = GetObject("winmgmts:\\.\root\cimv2")

' Méthode 1: Chercher le processus python.exe exécutant app.py
Set colProcesses = objWMIService.ExecQuery("SELECT * FROM Win32_Process WHERE CommandLine LIKE '%app.py%'")

If colProcesses.Count > 0 Then
    For Each objProcess in colProcesses
        pid = objProcess.ProcessId
        objShell.Run "taskkill /f /pid " & pid, 0, True
        WScript.Sleep 500
    Next
    MsgBox "Serveur FTP arrêté avec succès!", vbInformation, "Serveur FTP"
    WScript.Quit
End If

' Méthode 2: Si la méthode 1 n'a rien trouvé, chercher par port
Set objShellCmd = CreateObject("WScript.Shell")
Set objExec = objShellCmd.Exec("netstat -ano | findstr :5000 | findstr LISTENING")
strOutput = objExec.StdOut.ReadAll()

If strOutput <> "" Then
    ' Extraire le PID de la sortie
    arrLines = Split(strOutput, vbCrLf)
    For Each line In arrLines
        If line <> "" Then
            arrParts = Split(line)
            pid = arrParts(UBound(arrParts))
            If IsNumeric(pid) Then
                objShell.Run "taskkill /f /pid " & pid, 0, True
                WScript.Sleep 500
            End If
        End If
    Next
    MsgBox "Serveur FTP arrêté avec succès!", vbInformation, "Serveur FTP"
Else
    MsgBox "Aucun serveur FTP en cours d'exécution sur le port 5000.", vbExclamation, "Serveur FTP"
End If
