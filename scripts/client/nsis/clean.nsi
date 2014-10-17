; Includes
!include "MUI2.nsh"

!addincludedir "include"
!addplugindir "plugins"

!include "getFQDN.nsi"


!define APPNAME "Openport"
!define INSTDIR "$PROGRAMFILES\${APPNAME}"
!define OPENPORT_EXE "openport.exe"
!define version 0.9.0

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



Section "StopService"

	SimpleSC::StopService "OpenportService" 1 20

SectionEnd
!insertmacro MUI_PAGE_INSTFILES


Page custom pre_service_page leave_service_page

var dialog
var hwnd
var Label
var InstallServiceCheckbox
var InstallServiceCheckbox_state

Var password
Var username
Var domain
Function pre_service_page
	nsDialogs::Create 1018
    Pop $dialog
	
	${NSD_CreateLabel} 0 0 100% 24u "If you want to install Openport as a service, so your shares restart when you reboot, then enter your windows password here, and check the checkbox below:"
	Pop $Label

	${NSD_CreatePassword} 0 40 50% 10% ""
    Pop $hwnd
    SendMessage $hwnd ${EM_SETPASSWORDCHAR} 149 0 # 149 = medium dot
	
	${NSD_CreateCheckbox} 0 65 100% 10u "Install Openport as a service"
	Pop $InstallServiceCheckbox
	${NSD_Check} $InstallServiceCheckbox

	nsDialogs::Show
FunctionEnd

Section ""
SectionEnd


Function leave_service_page
    ${NSD_GetText} $hwnd $0
	StrCpy $password $0
	
	
	${NSD_GetState} $InstallServiceCheckbox $InstallServiceCheckbox_state
	
	${If} $InstallServiceCheckbox_state == 0
        Return
    ${EndIf}
	
	System::Call "advapi32::GetUserName(t .r0, *i ${NSIS_MAX_STRLEN} r1) i.r2"
	StrCpy $username $0 
	
	Call regGetFQDN
	pop $0
	StrCpy $domain $0 
	
	SimpleSC::StopService "OpenportService" 0 20
	SimpleSC::RemoveService "OpenportService"

	
	SimpleSC::InstallService "OpenportService" "Openport" 16 2 "$INSTDIR\openport_service.exe" "" "$domain\$username" "$password"
	Pop $0
    ${If} $0 != 0
        SimpleSC::InstallService "OpenportService" "Openport" 16 2 "$INSTDIR\openport_service.exe" "" ".\$username" "$password"
        Pop $0
		${If} $0 != 0
			MessageBox MB_OK "Could not install the service. Wrong password? $domain\$username  Error code: $0"
			Abort
		${EndIf}
    ${EndIf}
	
	
	SimpleSC::GrantServiceLogonPrivilege  "$domain\$username"
	Pop $0
	${If} $0 != 0
		MessageBox MB_OK "Error code: $0"
		Abort
	${EndIf}

	
	
	SimpleSC::StartService "OpenportService" "" 30
	Pop $0
    ${If} $0 != 0	
		${If} $0 == 1069
			MessageBox MB_OK "Invalid password."
			Abort
		${EndIf}
        MessageBox MB_OK "Could not start the service. Error code: $0"
        Abort
    ${EndIf}
	
	MessageBox MB_OK "Service installed and running."

	
FunctionEnd


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
	file /r ..\dist\*.* 
	file ..\resources\logo-base.ico
	file ..\manager\install_service.bat
;	file ..\resources\server.pem
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
	
;	# Start Menu
;	createShortCut "$SMPROGRAMS\${APPNAME}.lnk" "$INSTDIR\${OPENPORT_MANAGER_EXE}" "" "$INSTDIR\logo-base.ico"

	${EnvVarUpdate} $0 "PATH" "A" "HKLM" "$INSTDIR"
SectionEnd

Section "Uninstall"
	Delete $INSTDIR\Uninstall.exe
	RMDir /r /REBOOTOK $INSTDIR
	${un.EnvVarUpdate} $0 "PATH" "R" "HKLM" "$INSTDIR"   
;	DeleteRegKey HKCR "*\shell\${APPNAME}"
;	DeleteRegKey HKCR "Directory\shell\${APPNAME}"
;	Delete "$SMPROGRAMS\${APPNAME}.lnk"
SectionEnd