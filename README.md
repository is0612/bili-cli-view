# bili-cli-view

bili-cli 的图形控制台：**Vite + Vue 3 + TypeScript + Element Plus** 前端，**FastAPI** 后端。

后端不做业务逻辑，只把 `bili <命令>` 包成一组 HTTP 接口；前端用 Element Plus 的表单、弹窗、消息、
折叠面板把返回的 JSON 渲染成卡片和图谱。

![首页](docs/screenshot-home.png)

![分区排行](docs/screenshot-list.png)

![看懂视频](docs/screenshot-watch.png)

> 截图里的账号信息已隐去（`?demo=1` 会隐藏顶栏的版本/账号/主人三个 chip）。

## 自动值班（bili-cli 版）

面板里有一组「刷B站」：

| 页面 | 干什么 |
| --- | --- |
| **值班设置** | 每天几条、谷时窗口、热榜分区、抽帧数、关键词、评论开关、私信/评论投递、**现在跑一轮**、重置今日额度 |
| **发动态** | 写正文 / 配图 / @ 人，默认 `--dry-run` 预览，确认了才真发 |
| **她看过什么** | 读 `runtime/duty/seen.md`：收了几条、跳过几条、跳过理由 |

原理很简单：**bili-cli 是手，headless 会话是脑子，面板后端是闹钟**。

```
APScheduler（谷时窗口，每 30 秒看一眼）
  └─ 起一个 headless dsh 会话（cwd=仓库，自动带上 AGENTS.md 人设）
       └─ 交给它 duty/duty.md 的章程 + 本轮设置
            └─ 它用 `bili feed recommend` / `bili video watch` / `bili comment post` / `bili dm send` 干活
                 └─ 写 runtime/duty/out/<日期>.md 和 seen.md
```

- 只有一套工具（`bili`）、一份凭证（`%APPDATA%\bili-cli\`）；
- 每次跑的日志在 `runtime/duty/logs/round-*.log`，面板能看到报告原文；
- headless 会话用 `DSH_PERMISSION_MODE=danger-full-access` 起 —— 因为 `workspace-write` 沙箱里
  pwsh 会以 `0xC0000142` 退出，跑不了 `bili`。这是本机实测出来的硬限制。

![值班设置](docs/screenshot-duty.png)

![她看过什么](docs/screenshot-seen.png)

## 换个人用 / 多台机器

**登录态不跟着代码走**，每个机器各自扫码：

- 凭证存在本机 `%APPDATA%\bili-cli\credential.json`（macOS/Linux 是 `~/.config/bili-cli/`），
  `.gitignore` 已经把它排除在外，仓库里没有任何 token；
- 别人 clone 下来跑 `yarn dev`，顶栏会显示「未登录」→ 点「扫码登录」，用**自己的** B站 App 扫；
- 扫完所有数据（推荐流、收件箱、我的稿件、主人）都来自**他自己的账号**，和作者无关；
- 「主人」是「AI 要 @ 谁 / 私信给谁」，要改成自己的 UID：命令面板里跑
  `owner.set`，或者命令行 `bili owner set <你的UID>`；
- 想彻底换人：删掉 `credential.json` 再扫码即可（不用重装）。

唯一需要作者自己处理的是**截图和占位符**：README 里的图用 `?demo=1` 拍，代码里的示例 UID 是
`12345678` 这种假号。

## 为什么要有后端

浏览器里起不了进程、也读不到 `%APPDATA%` 下的登录凭证，所以「点按钮 → 跑 bili 命令」这一步
必须有个本地进程代劳。FastAPI 就干这件事，顺带解决两件小事：

- **封面防盗链**：B站图片要带 `Referer` 才给，`/api/cover` 代取 + 内存缓存；
- **人设 / API Key 落盘**：写到插件配置、`AGENTS.md`、`.credentials.yaml` 和用户环境变量。

## 跑起来

```bash
# 1) 依赖（首次）
uv venv .venv
uv pip install --python .venv\Scripts\python.exe -r backend/requirements.txt
npm install        # 或者 yarn

# 2) 一条命令起全套：后端 8811 + 前端 5199 + 自动开浏览器
yarn dev           # 等同 npm run dev
```

`yarn dev` 实际跑的是 `scripts/dev.mjs`：

- 先探活 `http://127.0.0.1:8811/api/ping`，没有后端就起一个（带 `--reload`）；
- 再起 Vite（`--open`，起来就弹浏览器）；
- Ctrl+C 会把两个进程一起收掉。

只想跑前端、后端自己另开：`yarn dev:web`。
改完代码 `yarn build` 后，`dist/` 会由 FastAPI 直接托管（单端口 8811，适合当成品用）。

## 目录

```
backend/app/
  main.py      FastAPI 路由
  runner.py    调 bili 子进程（异步、带超时）
  catalog.py   面板里暴露的命令清单（80+ 里的常用集）
  settings.py  人设 / 工作区 / API Key 的读写
  media.py     封面代理 + 本地图片白名单
  paths.py     路径与 bili 可执行文件定位
src/
  App.vue              壳：顶栏 + 侧栏 + 结果区（ElContainer/ElHeader/ElMain）
  components/
    SidebarNav.vue     ElMenu + 搜索过滤
    CommandRunner.vue  ElForm/ElInput/ElSelect/ElCheckbox + 命令行预览 + dry-run
    ResultCard.vue     ElCard + ElTag + ElCollapse（原始 JSON）
    NodeView.vue       递归渲染器（对象/数组/图片/长文本）
    VideoCard.vue      ElCard 封面卡（封面走 /api/cover）
    WatchView.vue      ElCollapse/ElImage，看懂视频专用排版
    SettingsModal.vue  ElDialog + ElForm（人设 / 工作区 / Key）
    LoginModal.vue     ElDialog + ElImage（扫码登录）
    ErrorBoundary.vue  渲染兜底，出错不白屏
  composables/useToast.ts   ElMessage 封装
  utils/format.ts           取值与格式化
```

## 接口

| 方法 | 路径 | 作用 |
| --- | --- | --- |
| GET | `/api/catalog` | 命令清单（前端侧栏） |
| GET | `/api/meta` | 版本 / 登录态 / 主人 |
| POST | `/api/run` | `{ argv: string[] }` → 执行一条 bili 命令 |
| POST | `/api/login` | 出二维码 |
| GET | `/api/qr.png` | 二维码图片 |
| POST | `/api/cancel-login` | 撤销待扫码状态 |
| GET/POST | `/api/settings` | 人设 / 工作区 / API Key |
| GET | `/api/cover?bvid=` | 封面（带 Referer 代取） |
| GET | `/api/proxy?u=` | 任意图片代理 |
| GET | `/api/img?p=` | 本地图片（白名单目录内） |

## 深链

- `?cmd=video.watch&video_id=BV181Hh6bE27&run=1` —— 直接选中命令并执行
- `?settings=1` / `?login=1` —— 打开对应弹层

## 注意

- 写操作（点赞/收藏/投币/评论/私信/动态）默认自动加 `--dry-run`，要真发得手动取消勾选。
- `bili` 的位置按 `BILI_BIN` → `PATH` → `~/.local/bin/bili.exe` 依次找，换机器不用改代码。
- 凭证、二维码这些运行时文件都在 `runtime/` 和 DSH 自己的目录里，**不要提交到仓库**。
- Element Plus 整站暗色：`main.ts` 里挂了 `html.dark` + `theme-chalk/dark/css-vars.css`，
  主色在 `style.css` 里按 B站粉重排了 `--el-color-primary` 系列变量。
