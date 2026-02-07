# GPU 监控脚本（gpu_watch.py）

用于监控服务器 GPU 状态，当发现有空闲 GPU 时进行提醒（终端提示音 + 可选邮箱通知）。

## 功能
- 定时读取 `nvidia-smi` 输出
- 判断空闲 GPU（默认：利用率 <= 5% 且显存占用 <= 500MB）
- 终端报警（蜂鸣）
- 支持邮箱通知（SMTP）

## 依赖
- 需要系统已安装并可执行 `nvidia-smi`
- Python 3.8+

## 快速使用
- 基本监控：
  - `python scripts/gpu_watch.py`
- 每 10 秒检查一次：
  - `python scripts/gpu_watch.py --interval 10`
- 调整空闲阈值：
  - `python scripts/gpu_watch.py --util_th 5 --mem_th 1000`
- 单次检测后退出：
  - `python scripts/gpu_watch.py --once`

## 邮箱通知（推荐用环境变量）
为避免密钥泄露，不要把授权码直接写进命令行。

设置环境变量：
- `SMTP_HOST`：SMTP 服务器地址，例如 `smtp.163.com`
- `SMTP_PORT`：端口，例如 `465`
- `SMTP_USER`：邮箱账号
- `SMTP_PASS`：邮箱授权码/应用密码
- `SMTP_SENDER`：发件人邮箱
- `SMTP_TO`：收件人邮箱（多个用逗号分隔）

运行：
- `python scripts/gpu_watch.py --email --smtp_ssl --interval 10`

如果你的 SMTP 使用 587 端口：
- 用 `--smtp_tls` 替代 `--smtp_ssl`

## 命令行参数说明
- `--interval`：检查间隔（秒）
- `--util_th`：GPU 利用率阈值（<= 视为空闲）
- `--mem_th`：显存占用阈值（MB，<= 视为空闲）
- `--once`：只检测一次然后退出
- `--json`：以 JSON 输出当前状态
- `--email`：开启邮件通知
- `--email_to`：收件人列表（逗号分隔）
- `--smtp_host` / `--smtp_port` / `--smtp_user` / `--smtp_pass` / `--smtp_sender`：SMTP 配置
- `--smtp_ssl`：使用 SSL
- `--smtp_tls`：使用 STARTTLS

## 常见问题
1) 运行报错 “failed to run nvidia-smi”
- 确认 NVIDIA 驱动与 `nvidia-smi` 正常可用。

2) 邮件发送失败
- 检查 SMTP 地址/端口是否正确
- 确认使用的是邮箱授权码（不是登录密码）
- 端口 465 用 `--smtp_ssl`，端口 587 用 `--smtp_tls`

## 安全提示
- 不要在命令行中明文写 SMTP 密码/授权码
- 使用环境变量或其他密钥管理方式
