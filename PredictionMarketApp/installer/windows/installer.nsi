!include "MUI2.nsh"

Name "Kalshi Bot Builder"
OutFile "KalshiBotBuilder_Setup.exe"
InstallDir "$PROGRAMFILES\KalshiBotBuilder"
RequestExecutionLevel admin

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_LANGUAGE "English"

Section "Install"
  SetOutPath $INSTDIR
  File /r "..\..\dist\*.*"
  CreateShortcut "$DESKTOP\Kalshi Bot Builder.lnk" "$INSTDIR\KalshiBotBuilder.exe"
  CreateDirectory "$SMPROGRAMS\Kalshi Bot Builder"
  CreateShortcut "$SMPROGRAMS\Kalshi Bot Builder\Kalshi Bot Builder.lnk" "$INSTDIR\KalshiBotBuilder.exe"
  CreateShortcut "$SMPROGRAMS\Kalshi Bot Builder\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
SectionEnd

Section "Uninstall"
  Delete "$INSTDIR\*.*"
  RMDir /r "$INSTDIR"
  Delete "$DESKTOP\Kalshi Bot Builder.lnk"
  RMDir /r "$SMPROGRAMS\Kalshi Bot Builder"
SectionEnd
