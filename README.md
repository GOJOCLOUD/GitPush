gitpush 使用指南（基于当前代码）

适用场景：免 clone，把本地文件/目录/zip 直接推到 GitHub 指定仓库/分支；可选忽略规则、冲突策略，既有 GUI（Tauri 桌面）也有 CLI（Python）。
依赖准备：系统需有 git、python3；GitHub Personal Access Token（推荐 repo 权限）。首次运行会把 token 存在 ~/.gitpush_token，后续复用。
GUI（桌面端 gitpush-bridge）

启动：运行 Tauri 桌面应用（已构建好的二进制，或在 gitpush-bridge 用 pnpm tauri dev 试运行）。
操作流程：5 步向导
Token：粘贴 GitHub Token；可填代理（http/https）。
Repo：选择/输入 owner/repo。
Branch：选择已有分支或输入新分支名。
File：通过文件/目录/zip 选择器选路径；可设置冲突策略（overwrite/skip/rename），编辑忽略列表（行分隔，默认包含 .git, node_modules, dist, .DS_Store, *.log, *.tmp 等）。
Upload：点击上传，完成后显示结果（success/url/统计）。
小贴士：复用上次参数时，只改文件即可快传；上传中可取消/重试（基础逻辑已接好，但取消为模拟，不会中断后端进程）。
CLI（Python 版，文件 gitpush/backend_interface.py）

基本命令（从仓库根运行）：
python3 gitpush/backend_interface.py \
  --action upload \
  --token <YOUR_TOKEN> \
  --repo owner/repo \
  --branch main \
  --path /abs/or/relative/path \
  --conflict-strategy overwrite \
  --ignore .git --ignore node_modules --ignore dist
--path 可多次传入，实现多文件/目录/zip 上传。
--conflict-strategy：overwrite(默认覆盖)、skip(跳过已有)、rename(自动改名)。
--ignore：可多次传入，支持 gitignore 风格，默认内置 .git, .DS_Store, node_modules, dist, build, __pycache__, *.log, *.tmp 等。
限制：默认总大小 200MB、最多 10,000 文件，单文件默认同总上限；可用 --max-total-bytes、--max-files、--max-single-file 覆盖（数值单位为字节）。
代理：CLI 没有显式参数，需自行设环境变量 HTTP_PROXY/HTTPS_PROXY，或在 Tauri 调用时传递。
输出：stdout 为 JSON（包括 success/message/url/statistics/head_sha/remote_sha/pushed_sha），stderr 打印调试信息。
其他动作：
获取分支列表：python3 gitpush/backend_interface.py --action get_branches --token <t> --repo owner/repo
创建分支：python3 gitpush/backend_interface.py --action create_branch --token <t> --repo owner/repo --branch new_branch
Python 主流程（文件 gitpush/main.py，交互版）

运行 python3 gitpush/main.py，按提示依次获取 token → 选仓库 → 选/建分支 → 选路径（系统文件选择器/AppleScript）→ 自动上传。适合命令行交互但不想写参数时使用。
工作机制要点

上传前自动在 git_workspace 下构建临时工作区，初始化 git，设置用户名 gitpush-uploader / 邮箱 gitpush@example.com。
目录上传会打包为 zip 再解压，保证扁平结构；zip 会直接解压；单文件直接拷贝。
远端分支不存在会创建；存在且有差异会尝试 merge/pull（带 Merge remote changes into <branch> 提交），必要时会 force-with-lease。
推送成功后返回 https://github.com/<repo>/tree/<branch>/ 访问链接。
常见问题

没有变化：overwrite 模式下若文件相同会跳过，返回 “No changes to push”。
路径不存在：检查文件/目录/zip 是否存在；GUI 选不到网络路径。
Token 权限：需至少 repo 读写；403/404 多半是权限或 repo 名错误。
忽略规则未生效：确认模式写法，支持目录名（如 node_modules）或通配（*.log）；默认忽略列表始终生效。
