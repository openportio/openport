; Includes
!include "MUI2.nsh"


!define APPNAME "OpenPort-It"
!define INSTDIR "$PROGRAMFILES\${APPNAME}"
!define OPENPORTIT_EXE "openportit.exe"
!define OPENPORT_EXE "openport_app.exe"

Name "${APPNAME}"
OutFile "${APPNAME}.exe"
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
!define MUI_FINISHPAGE_LINK_LOCATION "http://www.openport.be/"

;!define MUI_FINISHPAGE_RUN
;!define MUI_FINISHPAGE_RUN_TEXT "Run ${APPNAME}"
; !define MUI_FINISHPAGE_RUN_FUNCTION "LaunchOpenPort"
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

;--------------------------------
; Language and Branding
!insertmacro MUI_LANGUAGE "English"
BrandingText "http://www.openport.be/"

Section # hidden section
	setOutPath $INSTDIR
	file /r ..\dist\*.* 
	file ..\resources\logo-base.ico
	file ..\resources\server.pem
	#messageBox MB_OK "instdir: $INSTDIR"
	WriteRegStr HKCR "*\shell\${APPNAME}\command" "" "$INSTDIR\${OPENPORTIT_EXE} $\"%1$\""
	WriteRegStr HKCR "Directory\shell\${APPNAME}\command" "" "$INSTDIR\${OPENPORTIT_EXE} $\"%1$\""
	writeUninstaller "$INSTDIR\Uninstall.exe"
	; Write uninstaller to add/remove programs.
	WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "DisplayName" "${APPNAME}"
	WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "DisplayIcon" "$INSTDIR\logo-base.ico"
	WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "Publisher" "Danger Software"
	WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "UninstallString" "$INSTDIR\Uninstall.exe"
	WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "InstallLocation" "$INSTDIR"
	
SectionEnd

Section "Uninstall"
	Delete $INSTDIR\Uninstall.exe
	RMDir /r /REBOOTOK $INSTDIR
	DeleteRegKey HKCR "*\shell\${APPNAME}"
	DeleteRegKey HKCR "Directory\shell\${APPNAME}"
SectionEnd