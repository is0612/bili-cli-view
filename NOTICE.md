# 来源与致谢

这个仓库**不是** bili-cli 的源码副本，也不是 dsh-bili-scroll 的分支。它是一层独立写的壳，
按下面的边界使用第三方成果。

## 自己写的

- `backend/app/` —— FastAPI 封装：把 `bili` 命令包成 HTTP 接口、封面代理、人设/Key 落盘、
  值班调度器（`agent.py`）、判重表解析（`seen.py` 逻辑在 `agent.py` 内）
- `src/` —— Vue 3 + TypeScript 前端全部组件
- `duty/duty.md` —— 本轮值班的**改写版**章程（见下）

## 调用 / 参考（不复制代码）

| 项目 | 许可 | 我们怎么用 |
| --- | --- | --- |
| [kukemc/bili-cli](https://github.com/kukemc/bili-cli)（PyPI `bili-agent`） | MIT | 运行时调用它的 `bili` 命令；`backend/app/catalog.py` 的命令清单是照着它的 `bili schema` **手写**的参数表，不含其源码 |
| [c1overzz/dsh-bili-scroll](https://github.com/c1overzz/dsh-bili-scroll) | MIT | `duty/duty.md` 的**结构**改写自它的 `prompts/duty.md`：判重表 `seen.md`、报告用 `### BV` 计数的约定、私信 500 字上限、跳过理由的写法。文字与流程是按 bili-cli 重写的 |

两个项目都是 MIT，允许修改与再分发；本仓库按 MIT 发布，并在此致谢原作者。

## 运行时依赖

- 后端：FastAPI、uvicorn（MIT / BSD）
- 前端：Vue 3、Vite、Element Plus、@element-plus/icons-vue（MIT）
- 外部命令：`bili`（bili-agent）、可选 `ffmpeg`（抽帧/转码）、可选 Whisper / Qwen3-ASR（本地转写）
