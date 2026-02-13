# PaperBot 部署指南（Vercel + Supabase）

本方案用于快速给外部用户体验：

- 前端：Vercel（`web/` Next.js）
- 数据库：Supabase Postgres
- 后端 API：FastAPI（建议 Render/Railway/Fly.io，最后把 URL 配给 Vercel）

> 说明：PaperBot 有 SSE/长请求与定时任务能力，生产上不建议把 FastAPI 直接跑在 Vercel Serverless。

---

## 1. Supabase 准备

1. 创建 Supabase Project。
2. 打开 **Project Settings → Database → Connection string**。
3. 选择 **Transaction pooler**（推荐），拿到连接串。
4. 转换为 SQLAlchemy URL（`psycopg` 驱动）：

```bash
PAPERBOT_DB_URL="postgresql+psycopg://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres?sslmode=require"
```

---

## 2. 后端 API 部署（FastAPI）

以 Render 为例（Railway/Fly.io 同理）：

1. 新建 Web Service，连接仓库。
2. Build Command:

```bash
pip install -r requirements.txt
```

3. Start Command:

```bash
alembic upgrade head && python -m uvicorn src.paperbot.api.main:app --host 0.0.0.0 --port $PORT
```

4. 至少配置这些环境变量：

```bash
PAPERBOT_DB_URL=<supabase_sqlalchemy_url>
OPENAI_API_KEY=<optional>
ANTHROPIC_API_KEY=<optional>
SEMANTIC_SCHOLAR_API_KEY=<optional>
PAPERBOT_MODE=production
```

5. 记录后端公网地址，例如：

```text
https://paperbot-api.onrender.com
```

---

## 3. 前端部署到 Vercel（`web/`）

1. 在 Vercel 导入同一个仓库。
2. 配置：
   - **Root Directory**: `web`
   - Framework: Next.js（自动识别）
3. Environment Variables：

```bash
PAPERBOT_API_BASE_URL=https://paperbot-api.onrender.com
NEXT_PUBLIC_DEMO_URL=https://paperbot-web.vercel.app
```

4. Deploy。

---

## 4. 在项目里放「体验链接」

本仓库已经支持通过环境变量展示侧边栏「Live Demo」按钮：

```bash
NEXT_PUBLIC_DEMO_URL=https://paperbot-web.vercel.app
```

设置后，所有页面左侧栏底部会出现体验入口。

---

## 5. 验收清单

1. 前端可打开：`https://<your-web>.vercel.app`
2. 后端健康检查：`https://<your-api>/health`
3. 前端请求正常（无 5xx）：
   - `/api/research/tracks?user_id=default`
   - `/api/research/scholars?limit=20`
4. 数据写入成功（Supabase 表有新增记录）
5. `alembic upgrade head` 在部署日志中执行成功

---

## 6. 推荐发布方式（给大家体验）

- 公开地址：`https://<your-web>.vercel.app`
- README 或项目公告里放：
  - Web Demo
  - API Health
  - 已知限制（例如：部分 LLM 功能需 API Key）

