# BeamNG and Horizon Driver

**Languages:** [English](#english) | [中文](#中文) | [日本語](#日本語)

## English

BeamNG and Horizon Driver is a Windows visual driving assistant for BeamNG.drive,
Forza Horizon style racing games, cloud gaming windows, and local driving
simulators. It reads the game window, identifies the drivable road area, plans a
lookahead point, and sends smooth analog steering, throttle, and brake output
through a virtual Xbox controller.

The v0.6.0 project lives in [`Vision_Control/`](Vision_Control/).

### v0.6.0 Summary

- Multilingual README and control panel: English, Chinese, Japanese.
- Target-window capture mode to reduce interference from windows over the game.
- High-refresh capture and control loop for GeForce NOW, Shadow PC, Xbox Cloud
  Gaming, and local simulator windows.
- Adaptive LAB road segmentation fallback that works without a shipped ONNX
  model.
- Pure Pursuit style steering target and virtual Xbox 360 controller output
  through `vgamepad` / ViGEmBus.

### Quick Start

```bat
cd Vision_Control
install.bat
launch.bat
```

More details: [`Vision_Control/README.md`](Vision_Control/README.md).

## 中文

BeamNG and Horizon Driver 是一个 Windows 视觉驾驶辅助项目，面向
BeamNG.drive、类似 Forza Horizon 的赛车游戏、云游戏窗口和本地驾驶模拟器。
它不调用游戏 API，而是读取游戏窗口画面，识别可行驶路面，计算前视目标点，
再通过虚拟 Xbox 手柄输出平滑的转向、油门和刹车。

v0.6.0 项目位于 [`Vision_Control/`](Vision_Control/)。

### v0.6.0 简介

- README 和控制面板支持英文、中文、日文。
- 支持目标窗口捕获，减少游戏画面上方其他窗口对识别算法的干扰。
- 高刷新捕获和控制循环，适用于 GeForce NOW、Shadow PC、Xbox Cloud Gaming
  以及本地模拟器窗口。
- 自适应 LAB 路面分割兜底方案，即使没有 ONNX 模型也可以运行。
- Pure Pursuit 风格转向目标，通过 `vgamepad` / ViGEmBus 输出虚拟 Xbox 360
  手柄信号。

### 快速开始

```bat
cd Vision_Control
install.bat
launch.bat
```

详细说明请看 [`Vision_Control/README.md`](Vision_Control/README.md)。

## 日本語

BeamNG and Horizon Driver は、BeamNG.drive、Forza Horizon 系のレースゲーム、
クラウドゲーム画面、ローカルのドライビングシミュレーター向けの Windows
ビジュアル運転アシスタントです。ゲーム API は使わず、ゲームウィンドウの映像を
読み取り、走行可能な路面を検出し、前方の目標点を計算して、仮想 Xbox
コントローラーでステアリング、アクセル、ブレーキを出力します。

v0.6.0 プロジェクトは [`Vision_Control/`](Vision_Control/) にあります。

### v0.6.0 概要

- README と操作パネルは英語、中国語、日本語に対応。
- ターゲットウィンドウキャプチャにより、ゲーム上に重なった別ウィンドウの影響を
  減らします。
- GeForce NOW、Shadow PC、Xbox Cloud Gaming、ローカルシミュレーター向けの
  高速キャプチャと制御ループ。
- ONNX モデルなしでも動作する適応型 LAB 路面セグメンテーション。
- Pure Pursuit 風のステアリング目標と、`vgamepad` / ViGEmBus による仮想
  Xbox 360 コントローラー出力。

### クイックスタート

```bat
cd Vision_Control
install.bat
launch.bat
```

詳しくは [`Vision_Control/README.md`](Vision_Control/README.md) を参照してください。
