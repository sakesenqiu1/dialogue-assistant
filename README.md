# 暖心对话助手

本地运行的亲友沟通辅助工具：导入聊天记录与 Ta 自述，用 DeepSeek 提炼沟通画像，并在发送前评估措辞风险、生成优化文案。

> 说明：本工具仅作沟通辅助，不替代专业医疗或心理咨询。若对方有自伤等紧急情况，请寻求专业帮助。

## 功能

- 多对话本管理（每人独立画像）
- 批量导入对话 / Ta 自述 / 手动旁白
- AI 生成个性化沟通画像（综合全部材料，非仅最近几条）
- 发送前激怒风险分析与文案优化
- Windows 便携版：可复制文件夹到其它电脑使用（见下方）

## 快速开始（Windows）

### 方式 A：便携版（推荐给非开发者）

1. 若文件夹内**没有** `runtime\python\python.exe`，先双击 `build_portable.bat`（需联网，只需一次）
2. 双击 `配置DeepSeek.bat`，在 `.env` 中填写 [DeepSeek](https://platform.deepseek.com/) API Key
3. 双击 `run.bat`，浏览器打开终端里显示的地址

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

## 开源说明

- 上传 GitHub 时**不要**提交 `.env`、`data/`、`runtime/`（已在 `.gitignore` 中）
- 克隆仓库后需自行配置 API Key；便携用户运行 `build_portable.bat` 生成内置 Python

## 技术栈

Python · FastAPI · SQLite · DeepSeek API

## License

MIT
