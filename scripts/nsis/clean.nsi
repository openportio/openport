!define APP_NAME "OpenPort-It"
!define INSTDIR "$PROGRAMFILES\${APP_NAME}"

Name "${APP_NAME}"
OutFile "${APP_NAME}.exe"
ShowInstDetails show
LicenseData "license.txt"

RequestExecutionLevel admin ;Require admin rights on NT6+ (When UAC is turned on)
 
InstallDir ${INSTDIR}

page license
page directory
page instfiles
UninstPage uninstConfirm
UninstPage instfiles

Section # hidden section
	setOutPath $INSTDIR
	file /r ..\dist\*.* 
	#messageBox MB_OK "instdir: $INSTDIR"
	WriteRegStr HKCR "*\shell\${APP_NAME}\command" "" "$INSTDIR\${APP_NAME}.exe $\"%1$\""
	writeUninstaller $INSTDIR\uninstaller.exe
SectionEnd

Section "Uninstall"
	Delete $INSTDIR\uninstaller.exe
	RMDir /r /REBOOTOK $INSTDIR
	DeleteRegKey HKCR "*\shell\${APP_NAME}"
SectionEnd