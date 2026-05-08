<div align="center">

# 🚗 BeamNG.drive AI Auto Driver

**[中文](#-中文说明) · [English](#-english) · [日本語](#-日本語)**

![Version](https://img.shields.io/badge/version-1.0-blue)
![Python](https://img.shields.io/badge/python-3.8%2B-yellow)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

A lightweight AI auto-driver control panel for **BeamNG.drive**, powered by the official [BeamNGpy](https://github.com/BeamNG/BeamNGpy) API.  
Supports Chinese / English UI · Hotkey · Stuck auto-recovery · Damage detection

</div>

---

## 📖 中文说明

### 简介

这是一个基于 [BeamNGpy](https://github.com/BeamNG/BeamNGpy) 官方 API 的 BeamNG.drive AI 自动驾驶控制面板。程序使用游戏内置的 `span` 模式 AI，让车辆在整张地图上自动沿道路行驶，并提供一个小巧的置顶控制面板。

### ✨ 功能特性

- 🗺 自动加载地图、生成车辆、启动 AI 驾驶
- 🤖 使用 BeamNG 内置 AI (`span` 模式)，覆盖整张地图所有道路
- 🖥 小巧的置顶控制面板，不遮挡游戏画面
- ⏸ 一键暂停 / 继续（或按 **E 键**全局热键）
- 🔄 车辆卡死自动检测 + 手动一键恢复
- 💥 车辆损坏自动停车 + 双闪灯提示
- 🌍 中 / 英文界面一键切换
- ⚙ 设置自动保存（路径、地图、车辆、速度）

### 🖥 系统要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows 10 / 11 |
| Python | 3.8 或更高版本 |
| 游戏 | BeamNG.drive（正版，支持 Steam 版） |
| 依赖库 | beamngpy、pynput（自动安装） |

> ⚠ **BeamMP 用户注意**：BeamMP 多人 MOD 的网络初始化会阻塞加载信号，可能导致加载界面卡住约 180 秒后才继续。建议测试时禁用 BeamMP。

### 📦 支持的地图与车辆

**地图**

| 显示名 | 内部名 |
|--------|--------|
| 意大利乡村 (Italy) | `italy` |
| 美国西海岸 (West Coast USA) | `west_coast_usa` |
| 美国东海岸 (East Coast USA) | `east_coast_usa` |
| 网格测试场 (Grid Map) | `gridmap_v2` |
| 丛林岛屿 (Jungle Island) | `jungle_rock_island` |
| 小型测试场 (Small Grid) | `smallgrid` |

**车辆**

| 显示名 | 内部名 |
|--------|--------|
| ETK 800 系列（类奥迪轿车） | `etk800` |
| 皮卡车 (D-series Pickup) | `pickup` |
| 小型轿车 (Ibishu Covet) | `covet` |
| 面包车 (H-series Van) | `van` |
| 复古美国车 (Burnside Special) | `midsize` |

### 🚀 快速开始

**1. 安装 Python 3.8+**

前往 [python.org](https://www.python.org/downloads/) 下载，安装时勾选 **"Add Python to PATH"**。

**2. 安装依赖**

双击 `install.bat`，等待安装完成（需要联网）。

**3. 启动程序**

双击 `launch.bat`，打开控制面板。

**4. 配置并启动**

1. 点击「浏览」选择 BeamNG.drive 安装路径  
   （例如：`C:\Program Files (x86)\Steam\steamapps\common\BeamNG.drive`）
2. 选择地图和车辆
3. 用滑块设置目标速度（建议 40–80 km/h）
4. 点击「🚀 启动游戏并开始自动驾驶」

程序会自动打开游戏、加载地图、生成车辆，并启动 AI 驾驶！

### ⌨ 控制说明

| 操作 | 说明 |
|------|------|
| **E 键**（全局热键） | 暂停 / 继续 驾驶 |
| 🚀 启动 | 启动游戏并开始 AI 驾驶 |
| ⏸ 暂停 / ▶ 继续 | 随时暂停和恢复，车辆原地刹停等待 |
| 🔄 恢复车辆 | 车辆翻车/卡死时手动传送回道路 |
| ⏹ 停止 | 停止 AI 驾驶并断开连接 |
| ✕ 退出 | 退出面板（游戏也会关闭） |

### 📁 文件说明

```
ai_driver.py      主程序（核心代码）
installer.py      依赖安装脚本
launcher.py       启动器
install.bat       一键安装依赖
launch.bat        一键启动程序
reinstall.bat     清理并重新安装依赖
requirements.txt  依赖列表
config.json       配置文件（自动生成，保存设置）
README.txt        简易说明文档
```

### ❓ 常见问题

**Q: 点击启动后很久没反应？**  
A: BeamNG 加载地图需要 30–90 秒，请耐心等待。

**Q: 出现"连接失败"？**  
A: 检查游戏安装路径是否正确，重新点击启动。

**Q: 车辆一直不动？**  
A: 点击「🔄 恢复车辆」，或等待自动恢复（约 15 秒触发）。

**Q: 想换地图/车辆？**  
A: 先点「⏹ 停止」，修改设置后重新启动。

**Q: 为什么加载出来车辆生成在海里？**  
A: 这是目前还未修复的 bug。解决方法：直接按 **ESC**，然后选择地图，找一个位置，点击「Quick Travel」传送过去即可。

---

## 📖 English

### Introduction

A BeamNG.drive AI auto-driver control panel built on the official [BeamNGpy](https://github.com/BeamNG/BeamNGpy) API. It uses BeamNG's built-in `span` AI mode to drive a vehicle across the entire map road network, with a compact always-on-top control panel.

### ✨ Features

- 🗺 Auto-loads map, spawns vehicle, and starts AI driving
- 🤖 Uses BeamNG's built-in AI (`span` mode) covering all roads on the map
- 🖥 Compact always-on-top panel that doesn't block the game
- ⏸ One-click Pause / Resume (or press **E key** as a global hotkey)
- 🔄 Automatic stuck detection + one-click manual recovery
- 💥 Auto-stop on vehicle damage with hazard light indicator
- 🌍 Chinese / English UI toggle
- ⚙ Settings auto-saved (path, map, vehicle, speed)

### 🖥 Requirements

| Item | Requirement |
|------|-------------|
| OS | Windows 10 / 11 |
| Python | 3.8 or higher |
| Game | BeamNG.drive (licensed copy, Steam supported) |
| Dependencies | beamngpy, pynput (auto-installed) |

> ⚠ **BeamMP users**: BeamMP's network initialization can block BeamNG's load signal, causing the loading screen to hang for up to ~180 seconds before continuing. It is recommended to disable BeamMP for testing.

### 📦 Supported Maps & Vehicles

**Maps**

| Display Name | Internal Name |
|--------------|---------------|
| Italy (Rural) | `italy` |
| West Coast USA | `west_coast_usa` |
| East Coast USA | `east_coast_usa` |
| Grid Map | `gridmap_v2` |
| Jungle Rock Island | `jungle_rock_island` |
| Small Grid | `smallgrid` |

**Vehicles**

| Display Name | Internal Name |
|--------------|---------------|
| ETK 800 (Sedan) | `etk800` |
| D-series Pickup | `pickup` |
| Ibishu Covet | `covet` |
| H-series Van | `van` |
| Burnside Special | `midsize` |

### 🚀 Quick Start

**1. Install Python 3.8+**

Download from [python.org](https://www.python.org/downloads/). During installation, check **"Add Python to PATH"**.

**2. Install dependencies**

Double-click `install.bat` and wait for it to finish (internet required).

**3. Launch the program**

Double-click `launch.bat` to open the control panel.

**4. Configure and start**

1. Click **Browse** and select your BeamNG.drive install folder  
   (e.g. `C:\Program Files (x86)\Steam\steamapps\common\BeamNG.drive`)
2. Choose a map and vehicle
3. Set the target speed with the slider (40–80 km/h recommended)
4. Click **🚀 Launch & Start Auto Driving**

The program will automatically open the game, load the map, spawn the vehicle, and start AI driving!

### ⌨ Controls

| Action | Description |
|--------|-------------|
| **E key** (global hotkey) | Pause / Resume driving |
| 🚀 Launch | Start game and begin AI driving |
| ⏸ Pause / ▶ Resume | Pause and resume; vehicle brakes and waits |
| 🔄 Recover | Teleport vehicle back to road if stuck/flipped |
| ⏹ Stop | Stop AI driving and disconnect |
| ✕ Quit | Exit the panel (game window also closes) |

### 📁 File Overview

```
ai_driver.py      Main program (core logic)
installer.py      Dependency installer script
launcher.py       Launcher
install.bat       One-click dependency installer
launch.bat        One-click launcher
reinstall.bat     Clean reinstall of dependencies
requirements.txt  Dependency list
config.json       Config file (auto-generated, saves settings)
README.txt        Quick-start guide
```

### ❓ FAQ

**Q: Nothing happens after clicking Launch?**  
A: BeamNG takes 30–90 seconds to load a map. Please wait patiently.

**Q: "Connection failed" error?**  
A: Double-check your BeamNG.drive install path and try again.

**Q: Vehicle won't move?**  
A: Click **🔄 Recover**, or wait for auto-recovery to trigger (~15 seconds).

**Q: Want to change map/vehicle?**  
A: Click **⏹ Stop** first, change settings, then relaunch.

**Q: Why does the vehicle spawn in the ocean?**  
A: This is a known bug that hasn't been fixed yet. Workaround: press **ESC**, go to the map, select a location, and click **Quick Travel** to teleport there.

---

## 📖 日本語

### 概要

公式 [BeamNGpy](https://github.com/BeamNG/BeamNGpy) API を使用した BeamNG.drive 向け AI 自動運転コントロールパネルです。ゲーム内蔵の `span` モード AI を活用し、マップ全体の道路を車両が自動走行します。コンパクトな常時最前面表示パネルで操作できます。

### ✨ 機能

- 🗺 マップの自動ロード・車両スポーン・AI 走行の自動開始
- 🤖 BeamNG 内蔵 AI（`span` モード）によるマップ全路線カバー
- 🖥 ゲーム画面を遮らないコンパクトな常時最前面パネル
- ⏸ ワンクリックで一時停止 / 再開（**E キー**グローバルホットキー対応）
- 🔄 スタック自動検出 + ワンクリック手動回復
- 💥 車両ダメージ検出時の自動停車＋ハザードランプ表示
- 🌍 中国語 / 英語 UI 切り替え
- ⚙ 設定の自動保存（パス・マップ・車両・速度）

### 🖥 動作環境

| 項目 | 要件 |
|------|------|
| OS | Windows 10 / 11 |
| Python | 3.8 以上 |
| ゲーム | BeamNG.drive（正規ライセンス、Steam 版対応） |
| 依存ライブラリ | beamngpy、pynput（自動インストール） |

> ⚠ **BeamMP ユーザーへ**：BeamMP のネットワーク初期化がロード完了シグナルをブロックし、ローディング画面が最大約 180 秒間停止する場合があります。テスト時は BeamMP を無効化することをお勧めします。

### 📦 対応マップ・車両

**マップ**

| 表示名 | 内部名 |
|--------|--------|
| イタリア田園 (Italy) | `italy` |
| アメリカ西海岸 (West Coast USA) | `west_coast_usa` |
| アメリカ東海岸 (East Coast USA) | `east_coast_usa` |
| グリッドマップ (Grid Map) | `gridmap_v2` |
| ジャングルアイランド (Jungle Island) | `jungle_rock_island` |
| スモールグリッド (Small Grid) | `smallgrid` |

**車両**

| 表示名 | 内部名 |
|--------|--------|
| ETK 800（セダン） | `etk800` |
| D シリーズ ピックアップ | `pickup` |
| Ibishu Covet | `covet` |
| H シリーズ バン | `van` |
| Burnside Special | `midsize` |

### 🚀 クイックスタート

**1. Python 3.8 以上をインストール**

[python.org](https://www.python.org/downloads/) からダウンロードし、インストール時に **"Add Python to PATH"** にチェックを入れてください。

**2. 依存ライブラリのインストール**

`install.bat` をダブルクリックし、完了まで待ちます（インターネット接続が必要）。

**3. プログラムの起動**

`launch.bat` をダブルクリックしてコントロールパネルを開きます。

**4. 設定して開始**

1. **参照** をクリックし、BeamNG.drive のインストールフォルダを選択  
   （例：`C:\Program Files (x86)\Steam\steamapps\common\BeamNG.drive`）
2. マップと車両を選択
3. スライダーで目標速度を設定（40–80 km/h 推奨）
4. **🚀 Launch & Start Auto Driving** をクリック

プログラムが自動的にゲームを起動し、マップを読み込み、車両をスポーンして AI 走行を開始します！

### ⌨ 操作方法

| 操作 | 説明 |
|------|------|
| **E キー**（グローバルホットキー） | 走行の一時停止 / 再開 |
| 🚀 Launch | ゲームを起動して AI 走行を開始 |
| ⏸ Pause / ▶ Resume | 一時停止・再開（車両はその場でブレーキ停車） |
| 🔄 Recover | スタック・横転時に道路上へテレポート回復 |
| ⏹ Stop | AI 走行を停止してゲームとの接続を切断 |
| ✕ Quit | パネルを終了（ゲームウィンドウも閉じる） |

### 📁 ファイル構成

```
ai_driver.py      メインプログラム（コアロジック）
installer.py      依存ライブラリインストールスクリプト
launcher.py       ランチャー
install.bat       依存ライブラリ一括インストール
launch.bat        プログラム一括起動
reinstall.bat     依存ライブラリのクリーン再インストール
requirements.txt  依存ライブラリリスト
config.json       設定ファイル（自動生成・設定保存）
README.txt        簡易ガイド
```

### ❓ よくある質問

**Q: 起動後しばらく何も起きない？**  
A: BeamNG はマップ読み込みに 30〜90 秒かかります。しばらくお待ちください。

**Q: 「接続失敗」エラーが出る？**  
A: BeamNG.drive のインストールパスを確認し、再度起動してください。

**Q: 車両が動かない？**  
A: **🔄 Recover** をクリックするか、自動回復を待ちます（約 15 秒後に発動）。

**Q: マップや車両を変更したい？**  
A: まず **⏹ Stop** をクリックし、設定を変更してから再起動してください。

**Q: 車両が海の中にスポーンするのはなぜ？**  
A: 現在未修正の既知バグです。対処法：**ESC** を押してマップを開き、任意の場所を選んで **Quick Travel** をクリックするとテレポートできます。

---

<div align="center">

MIT License · Made with ❤️ using [BeamNGpy](https://github.com/BeamNG/BeamNGpy)

</div>
