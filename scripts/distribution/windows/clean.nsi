; Includes
!include "MUI2.nsh"

!addincludedir "include"
!addplugindir "plugins"

;!include "getFQDN.nsi"


!define APPNAME "Openport"
!define INSTDIR "$PROGRAMFILES\${APPNAME}"
!define OPENPORT_EXE "openport.exe"
!ifndef VERSION
	!define version 0.0.0
!endif

Name "${APPNAME}"
OutFile "${APPNAME}_${VERSION}.exe"
ShowInstDetails show
LicenseData "license.txt"

RequestExecutionLevel admin ;Require admin rights on NT6+ (When UAC is turned on)
 
InstallDir ${INSTDIR}

;--------------------------------
; Interface settings
!define MUI_ICON "images\logo-base.ico"
!define MUI_WELCOMEFINISHPAGE_BITMAP "images\wizard.bmp"
!define MUI_WELCOMEFINISHPAGE_BITMAP_NOSTRETCH
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP "images\header.bmp"
!define MUI_ABORTWARNING

;--------------------------------
; Pages

!insertmacro MUI_PAGE_LICENSE "LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY


!insertmacro MUI_PAGE_INSTFILES




!define MUI_FINISHPAGE_LINK "Visit the OpenPort website for documentation and support"
!define MUI_FINISHPAGE_LINK_LOCATION "http://www.openport.io/"

;!define MUI_FINISHPAGE_RUN
;!define MUI_FINISHPAGE_RUN_TEXT "Run ${APPNAME}"
; !define MUI_FINISHPAGE_RUN_FUNCTION "LaunchOpenPort"
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

;--------------------------------
; Language and Branding
!insertmacro MUI_LANGUAGE "English"
BrandingText "http://www.openport.io/"


!include "EnvVarUpdate.nsh"

Section # hidden section
	setOutPath $INSTDIR
;	file /r ..\..\client\dist\*.* 
	file /r ..\..\client\dist\openport\*.* 
	file /r ..\..\client\dist\openportw\*.* 
	file /r ..\..\client\dist\openport-gui\*.*
	file ..\..\client\resources\logo-base.ico
;	file ..\..\client\resources\install_windows_service.bat
;	file ..\..\client\resources\server.pem
	#messageBox MB_OK "instdir: $INSTDIR"
;	WriteRegStr HKCR "*\shell\${APPNAME}\command" "" "$INSTDIR\${OPENPORT_EXE} $\"%1$\""
;	WriteRegStr HKCR "Directory\shell\${APPNAME}\command" "" "$INSTDIR\${OPENPORT_EXE} $\"%1$\""
	writeUninstaller "$INSTDIR\Uninstall.exe"
	; Write uninstaller to add/remove programs.
	WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "DisplayName" "${APPNAME}"
	WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "DisplayIcon" "$INSTDIR\logo-base.ico"
	WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "Publisher" "Danger Software"
	WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "UninstallString" "$INSTDIR\Uninstall.exe"
	WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "InstallLocation" "$INSTDIR"
	
	WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "Openport" '"$INSTDIR\openportw.exe"  --restart-shares'
	
	
;	# Start Menu
	createShortCut "$SMPROGRAMS\${APPNAME}.lnk" "$INSTDIR\openport-gui.exe" "" "$INSTDIR\logo-base.ico"

	${EnvVarUpdate} $0 "PATH" "A" "HKLM" "$INSTDIR"
SectionEnd

Section "Uninstall"
	Delete $INSTDIR\Uninstall.exe
	Delete "$SMPROGRAMS\${APPNAME}.lnk"
	RMDir /r /REBOOTOK $INSTDIR
	${un.EnvVarUpdate} $0 "PATH" "R" "HKLM" "$INSTDIR"   
	DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run\" "Openport"
;	DeleteRegKey HKCR "Directory\shell\${APPNAME}"
;	Delete "$SMPROGRAMS\${APPNAME}.lnk"
SectionEnd