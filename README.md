# 暖心对话助手

本地运行的亲友沟通辅助工具：导入聊天记录与 Ta 自述，用 DeepSeek 提炼沟通画像，并在发送前评估措辞风险、生成优化文案。

> 说明：本工具仅作沟通辅助，不替代专业医疗或心理咨询。若对方有自伤等紧急情况，请寻求专业帮助。

## 功能

- 多对话本管理（每人独立画像）
- 批量导入对话 / Ta 自述 / 手动旁白
- AI 生成个性化沟通画像（综合全部材料，非仅最近几条）
- 发送前激怒风险分析与文案优化
- Windows 便携版：可复制文件夹到其它电脑使用（见下方）

## 从 GitHub 克隆后（推荐流程）

只需改配置、再启动，**不必单独安装 Python**：

```bash
git clone https://github.com/sakesenqiu1/dialogue-assistant.git
cd dialogue-assistant
```

仓库地址：[github.com/sakesenqiu1/dialogue-assistant](https://github.com/sakesenqiu1/dialogue-assistant)

1. 复制环境配置并填入密钥（二选一）：
   - 手动：`copy .env.example .env`，编辑 `.env` 中的 `DEEPSEEK_API_KEY`
   - 或双击 `配置DeepSeek.bat` 自动创建并打开 `.env`
2. 双击 **`run.bat`**
   - **首次运行**会自动联网下载内置 Python（约 1～3 分钟，只需一次）
   - 若 `.env` 里仍是占位密钥，会提示用记事本修改

> 密钥获取：[DeepSeek 开放平台](https://platform.deepseek.com/)

仓库已忽略 `.env`、`data/`、`runtime/`，不会把密钥和本地数据推上去。

## 快速开始（Windows）

### 方式 A：便携版（推荐给非开发者）

1. 配置 `.env`（见上方「从 GitHub 克隆后」）
2. 双击 `run.bat`（首次会自动执行 `setup.bat` 准备环境）
3. 浏览器打开终端里显示的地址

可选：提前双击 `build_portable.bat` 只构建环境、不启动服务。

### 方式 B：开发者（Python 3.11+）

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# 编辑 .env 填入 DEEPSEEK_API_KEY
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## 配置

复制 `.env.example` 为 `.env`：

```env
DEEPSEEK_API_KEY=你的密钥
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

## 导入格式示例

```
我：在吗
Ta：嗯
自述：最近总是睡不好…
```

导入顺序**不必按时间**；分析时会均匀综合全部条目。

## 开源 / 上传 GitHub

| 会提交到仓库 | 不会提交（本地生成） |
|-------------|---------------------|
| 源码、`run.bat`、`setup.bat`、`.env.example` | `.env`（你的密钥） |
| `requirements*.txt`、`build_portable.ps1` | `data/`（SQLite 数据库） |
| | `runtime/`（内置 Python，首次 `run.bat` 自动构建） |

## 技术栈

Python · FastAPI · SQLite · DeepSeek API

## License

MIT
