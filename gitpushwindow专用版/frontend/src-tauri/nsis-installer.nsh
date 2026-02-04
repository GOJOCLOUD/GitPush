; NSIS 自定义安装脚本
; 用于增强 GitPush Windows 安装程序的功能

!macro customInstall
  ; 创建开始菜单文件夹
  CreateDirectory "$SMPROGRAMS\GitPush"
  
  ; 创建开始菜单快捷方式
  CreateShortCut "$SMPROGRAMS\GitPush\GitPush.lnk" "$INSTDIR\GitPush.exe" "" "$INSTDIR\GitPush.exe" 0
  CreateShortCut "$SMPROGRAMS\GitPush\卸载.lnk" "$INSTDIR\UninstallGitPush.exe"
  
  ; 创建网站快捷方式
  CreateShortCut "$SMPROGRAMS\GitPush\访问官网.lnk" "https://github.com/gojo-jzjk/GitPush"
  
  ; 注册文件关联
  WriteRegStr HKCR ".gitpush" "" "GitPush.Project"
  WriteRegStr HKCR "GitPush.Project" "" "GitPush Project File"
  WriteRegStr HKCR "GitPush.Project\DefaultIcon" "" "$INSTDIR\GitPush.exe,0"
  WriteRegStr HKCR "GitPush.Project\shell\open\command" "" '"$INSTDIR\GitPush.exe" "%1"'
  
  ; 注册协议
  WriteRegStr HKCR "gitpush" "" "URL:GitPush Protocol"
  WriteRegStr HKCR "gitpush" "URL Protocol" ""
  WriteRegStr HKCR "gitpush\DefaultIcon" "" "$INSTDIR\GitPush.exe,0"
  WriteRegStr HKCR "gitpush\shell\open\command" "" '"$INSTDIR\GitPush.exe" "%1"'
  
  ; 添加到系统PATH（可选）
  ; ${EnvVarUpdate} $0 "PATH" "A" "HKLM" "$INSTDIR"
  
  ; 创建卸载信息
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\GitPush" "DisplayName" "GitPush"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\GitPush" "UninstallString" "$INSTDIR\UninstallGitPush.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\GitPush" "QuietUninstallString" "$INSTDIR\UninstallGitPush.exe /S"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\GitPush" "DisplayIcon" "$INSTDIR\GitPush.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\GitPush" "Publisher" "Gojo"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\GitPush" "HelpLink" "https://github.com/gojo-jzjk/GitPush/issues"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\GitPush" "URLInfoAbout" "https://github.com/gojo-jzjk/GitPush"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\GitPush" "DisplayVersion" "0.1.0"
  
  ; 设置自动更新任务
  CreateShortCut "$SMSTARTUP\GitPushUpdater.lnk" "$INSTDIR\GitPush.exe" "--check-updates"
  
  ; 创建配置目录
  CreateDirectory "$APPDATA\GitPush"
  
  ; 复制默认配置文件（如果存在）
  ; IfFileExists "$INSTDIR\default-config.json" 0 +2
  ; CopyFiles "$INSTDIR\default-config.json" "$APPDATA\GitPush\config.json"
!macroend

!macro customUnInstall
  ; 删除开始菜单快捷方式
  RMDir /r "$SMPROGRAMS\GitPush"
  
  ; 删除桌面快捷方式
  Delete "$DESKTOP\GitPush.lnk"
  
  ; 删除启动项
  Delete "$SMSTARTUP\GitPushUpdater.lnk"
  
  ; 删除文件关联
  DeleteRegKey HKCR ".gitpush"
  DeleteRegKey HKCR "GitPush.Project"
  
  ; 删除协议
  DeleteRegKey HKCR "gitpush"
  
  ; 删除卸载信息
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\GitPush"
  
  ; 从系统PATH中移除（如果之前添加了）
  ; ${un.EnvVarUpdate} $0 "PATH" "R" "HKLM" "$INSTDIR"
  
  ; 询问是否删除用户数据
  MessageBox MB_YESNO "是否删除用户配置和数据？" IDNO skipUserData
    RMDir /r "$APPDATA\GitPush"
  skipUserData:
!macroend

; 安装页面自定义
!macro customWelcomePage
  !insertmacro MUI_PAGE_WELCOME
  !insertmacro MUI_PAGE_LICENSE "LICENSE.txt"
  !insertmacro MUI_PAGE_COMPONENTS
  !insertmacro MUI_PAGE_DIRECTORY
  !insertmacro MUI_PAGE_INSTFILES
  !insertmacro MUI_PAGE_FINISH
!macroend

; 安装组件
LangString DESC_SecMain ${LANG_SIMPCHINESE} "GitPush 主程序"
LangString DESC_SecDesktop ${LANG_SIMPCHINESE} "创建桌面快捷方式"
LangString DESC_SecStartMenu ${LANG_SIMPCHINESE} "创建开始菜单快捷方式"
LangString DESC_SecAutoStart ${LANG_SIMPCHINESE} "开机自动启动"
LangString DESC_SecFileAssoc ${LANG_SIMPCHINESE} "关联 .gitpush 文件"

Section "主程序" SecMain
  SectionIn RO
  ; 主程序文件由 Tauri 自动安装
SectionEnd

Section "桌面快捷方式" SecDesktop
  CreateShortCut "$DESKTOP\GitPush.lnk" "$INSTDIR\GitPush.exe"
SectionEnd

Section "开始菜单快捷方式" SecStartMenu
  CreateDirectory "$SMPROGRAMS\GitPush"
  CreateShortCut "$SMPROGRAMS\GitPush\GitPush.lnk" "$INSTDIR\GitPush.exe"
SectionEnd

Section "开机自动启动" SecAutoStart
  CreateShortCut "$SMSTARTUP\GitPush.lnk" "$INSTDIR\GitPush.exe"
SectionEnd

Section "文件关联" SecFileAssoc
  WriteRegStr HKCR ".gitpush" "" "GitPush.Project"
  WriteRegStr HKCR "GitPush.Project" "" "GitPush Project File"
  WriteRegStr HKCR "GitPush.Project\DefaultIcon" "" "$INSTDIR\GitPush.exe,0"
  WriteRegStr HKCR "GitPush.Project\shell\open\command" "" '"$INSTDIR\GitPush.exe" "%1"'
SectionEnd

; 分配描述字符串
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SecMain} $(DESC_SecMain)
  !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop} $(DESC_SecDesktop)
  !insertmacro MUI_DESCRIPTION_TEXT ${SecStartMenu} $(DESC_SecStartMenu)
  !insertmacro MUI_DESCRIPTION_TEXT ${SecAutoStart} $(DESC_SecAutoStart)
  !insertmacro MUI_DESCRIPTION_TEXT ${SecFileAssoc} $(DESC_SecFileAssoc)
!insertmacro MUI_FUNCTION_DESCRIPTION_END