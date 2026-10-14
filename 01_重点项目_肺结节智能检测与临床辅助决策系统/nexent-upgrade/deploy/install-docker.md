# 安装 Docker Desktop（Windows）

Nexent 依赖 Docker 24+ 与 Docker Compose v2+。以下在 Windows 10/11 上安装 Docker Desktop。

## 前置条件
- 开启虚拟化：BIOS 中启用 Intel VT-x / AMD-V。
- 建议使用 WSL2 后端（本机此前已安装过 WSL，`wsl.exe` 存在）。

## 步骤

1. **下载安装器**
   - 官方：https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe
   - 或在 PowerShell 中：
     ```powershell
     Invoke-WebRequest -Uri "https://desktop.docker.com/win/main/amd64/Docker Desktop Installer.exe" -OutFile "$env:USERPROFILE\Downloads\DockerDesktopInstaller.exe"
     ```

2. **以管理员身份运行安装器**（双击，或右键「以管理员身份运行」）。
   - 安装向导勾选「Use WSL 2 instead of Hyper-V」。
   - 完成后按提示**重启电脑**。

3. **启动并验证**
   ```powershell
   docker --version
   docker compose version
   docker run hello-world
   ```
   能跑通 `hello-world` 即表示安装成功。

## 常见问题
- **WSL 未安装/报错**：在管理员 PowerShell 执行
  ```powershell
  wsl --install
  wsl --set-default-version 2
  ```
- **国内镜像加速**：Docker Desktop → Settings → Docker Engine 中把 `registry-mirrors` 加上镜像加速地址（按需配置）。
- **提示需要启用虚拟化**：进 BIOS 开启 VT-x/AMD-V。

## 硬件要求（Nexent 最低）
- CPU：4 核（推荐 8 核）
- 内存：8 GB（推荐 16 GB）
- 磁盘：40 GB 可用（推荐 100 GB）

> 说明：Docker Desktop 安装需要管理员权限并可能要求重启，需由你本人在本机完成（自动化的沙箱环境无法执行 UAC 提权与 WSL 调用）。
