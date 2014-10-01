Function regGetFQDN
    Push $0
    Push $1
 
    SetRegView 64
 
    ## Possible system domain Name locations
    ## TODO Adjust order for locations that are most likley to be correct.
        ReadRegStr $1 HKLM "SYSTEM\CurrentControlSet\Services\Tcpip\Parameters"               \
            "Domain"
        StrCmp $1 "" 0 GetHostName
        ReadRegStr $1 HKLM "SOFTWARE\Microsoft\Windows\CurrentVersion\Group Policy\History"   \
            "NetworkName"
        StrCmp $1 "" 0 GetHostName
        ReadRegStr $1 HKLM "SOFTWARE\Microsoft\Windows\CurrentVersion\Telephony"              \
            "DomainName"
        StrCmp $1 "" 0 GetHostName
        ReadRegStr $1 HKLM "SOFTWARE\Microsoft\MSMQ\Parameters\setup"                         \
            "MachineDomainFQDN"
 
    GetHostName:
    ## Possible Registry Hostname locations
        ReadRegStr $0 HKLM "SYSTEM\CurrentControlSet\Control\ComputerName\ActiveComputerName" \
            "ComputerName"
        StrCmp $0 "" 0 FQDNDone
        ReadRegStr $0 HKLM "SYSTEM\CurrentControlSet\Control\ComputerName\ComputerName"       \
            "ComputerName"
        StrCmp $0 "" 0 FQDNDone
        ReadRegStr $1 HKLM "SYSTEM\CurrentControlSet\Services\Tcpip\Parameters"               \
            "Hostname"
        StrCmp $0 "" 0 FQDNDone
 
    FQDNDone:
        StrCmp $1 "" +2
        StrCpy $0 "$0.$1"
 
    SetRegView lastused 
 
    Pop $1
    Exch $0
FunctionEnd





!ifndef GetFQDN
    !verbose push
    !verbose 3
    !ifmacrondef _GetFQDN
        !define GetFQDN "!insertmacro _GetFQDN"
        !macro _InsertFunction_GetFQDN _U_
            Function ${_U_}GetFQDN
                ## This Function uses the GetNetworkParams Win32 API function.
                ##    Additional details are available at:
                ##    http://msdn.microsoft.com/en-us/library/aa365968%28VS.85%29.aspx
                ClearErrors
 
                Push $1
                Push $0
                Push $2
 
                ## Get the required buffer size
                    System::Call "*(&i4 0)i .r0"
                    System::Call 'Iphlpapi::GetNetworkParams(i 0, i r0)i.r1'
                    StrCmp $1 111 BufferOkay
                        SetErrors
                        StrCpy $1 ""
                        Goto CleanUp_End
                    BufferOkay:
 
                ## Allocate Buffer
                    System::Call '*$0(i .r1)'
                    System::Alloc $1
                    Pop $2
 
                ## Populate Buffer with Data
                    System::Call 'Iphlpapi::GetNetworkParams(i $2, *i $1)i.r1'
                    StrCmp $1 0 DataOkay
                        SetErrors
                        StrCpy $1 ""
                        Goto CleanUp
                    DataOkay:
 
                ## Success, lets build the FQDN from the data
                    System::Call '*$2(&t132 .r3,&t132 .r4)'
                    StrCpy $1 "$3.$4"
 
                CleanUp:
                    System::Free $2
                CleanUp_End:
                    System::Free $0
                    Pop $2
                    Pop $0
                    Exch $1
            FunctionEnd
        !macroend
        !insertmacro _InsertFunction_GetFQDN ""
        !macro _GetFQDN _RetVar
            !verbose Push
            !verbose 3
            !ifdef __GLOBAL__
                !if `${_RetVar}` == "UNINSTALL"
                    !ifndef "un.GetFQDN"
                        !insertmacro _InsertFunction_GetFQDN "un."
                        !define "un.GetFQDN" "${GetFQDN}"
                    !endif
                !else
                    !undef GetFQDN
                    !error "Syntax Error: ${GetFQDN} ${_RetVar}"
                !endif
            !else
                !ifdef __UNINSTALL__
                    !ifndef un.GetFQDN
                        !undef GetFQDN
                        !error 'Oops! You need to enable the GetFQDN uninstaller function in the global scope using: "${GetFQDN} UNINSTALL"'
                    !endif
                    Call un.GetFQDN
                !else
                    Call GetFQDN
                !endif
                !if ${_RetVar} != s
                    Pop ${_RetVar}
                !endif
            !endif
            !verbose Pop
        !macroend
    !endif
    !verbose Pop
!endif
