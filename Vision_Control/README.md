# BeamNG and Horizon Driver

**Languages:** [English](#english) | [中文](#中文) | [日本語](#日本語)

## English

BeamNG and Horizon Driver is a Windows visual driving assistant for BeamNG.drive,
Forza Horizon style racing games, cloud gaming windows, and local driving
simulators. It does not call a game API. Instead, it captures the visible game
client, detects the drivable road area, computes a lookahead target, and sends
analog driving input through a virtual Xbox controller.

### v0.5.0 Description

This release is built for low-latency cloud-computer use: GeForce NOW, Shadow
PC, Xbox Cloud Gaming, or any Windows game window with a stable driving camera.
The UI is English by default and includes Chinese and Japanese language
switching from the control panel.

The driver has three capture modes:

- `Window only`: captures the target window client area with Win32
  `PrintWindow`, so other desktop windows placed over the game are not included
  in the frame sent to perception.
- `DXGI ROI`: uses `dxcam` desktop duplication for maximum speed. This mode is
  faster, but it captures the composed desktop region.
- `Auto`: tries `Window only` first and falls back to `DXGI ROI` if the cloud
  client refuses window capture.

The control panel itself is hidden from screen-capture APIs on supported
Windows builds, so the preview panel does not recursively appear in the game
capture.

### Features

- Multilingual Tk control panel: English, Chinese, Japanese.
- Window selector with refresh for GeForce NOW, BeamNG.drive, Forza Horizon,
  and other visible game windows.
- Capture backend selector: Auto, Window only, DXGI ROI.
- Live preview, telemetry, and log panel.
- Global `E` hotkey for pause/resume.
- Adaptive LAB road segmentation fallback, no model file required.
- Pure Pursuit style lookahead steering.
- Virtual Xbox 360 controller output through `vgamepad` and ViGEmBus.
- Safe drive-output switch: preview can run without sending controls.

### Requirements

- Windows 10 or Windows 11.
- Python 3.10 or newer.
- A cloud game client or local driving simulator window.
- ViGEmBus driver for virtual Xbox controller output:
  <https://github.com/ViGEm/ViGEmBus/releases>

Python dependencies are listed in [`requirements.txt`](requirements.txt).

### Install

```bat
cd Vision_Control
install.bat
```

The installer upgrades `pip`, installs runtime dependencies, installs this
package in editable mode, and runs a basic dependency check.

### Run

```bat
cd Vision_Control
launch.bat
```

Or run it directly:

```bat
python -m vision_control.main
```

Headless mode:

```bat
python -m vision_control.main --headless --window "GeForce NOW" --capture auto
```

Self-test:

```bat
python -m vision_control.main --selftest
```

### Recommended Cloud Setup

1. Open the cloud game client and start the driving game.
2. Use a third-person chase camera with a clear road view.
3. Open `launch.bat`.
4. Select the game window.
5. Keep capture mode on `Auto`; switch to `Window only` if an overlay appears
   over the game; switch to `DXGI ROI` if the cloud client returns black frames.
6. Press `Start` and wait for calibration to reach `ready`.
7. Enable `Drive output` only after the preview road mask looks stable.

### Safety Notes

BeamNG and Horizon Driver sends real controller input to Windows when drive
output is enabled. Keep the game in a safe test area while calibrating, and use
the global `E` hotkey or `Stop` button if the output is not behaving as
expected.

Some games and cloud services may restrict automation. Use this project only
where you are allowed to run visual-assistance tools.

### Project Layout

```text
Vision_Control/
  src/vision_control/
    capture/        window-only and DXGI ROI capture backends
    perception/     road segmentation and optional model hooks
    planning/       drivable-area extraction and steering target
    control/        virtual gamepad and keyboard fallback code
    ui/             multilingual control panel
  tests/            focused geometry unit tests
  docs/             architecture and development notes
```

### License

MIT. See [`../LICENSE`](../LICENSE).

## 中文

BeamNG and Horizon Driver 是一个 Windows 视觉驾驶辅助项目，面向
BeamNG.drive、类似 Forza Horizon 的赛车游戏、云游戏窗口和本地驾驶模拟器。
它不调用游戏 API，而是捕获游戏客户端画面，识别可行驶路面，计算前视目标点，
并通过虚拟 Xbox 手柄输出类比驾驶控制。

### v0.5.0 说明

此版本面向低延迟云电脑和云游戏使用场景，例如 GeForce NOW、Shadow PC、Xbox
Cloud Gaming，或任何带稳定驾驶视角的 Windows 游戏窗口。界面默认英文，并可在
控制面板中切换中文和日文。

驾驶员提供三种捕获模式：

- `Window only`：使用 Win32 `PrintWindow` 捕获目标窗口客户区，因此覆盖在游戏上
  方的其他桌面窗口不会进入感知帧。
- `DXGI ROI`：使用 `dxcam` 桌面复制，速度最快，但会捕获桌面合成后的区域。
- `Auto`：优先尝试 `Window only`，如果云游戏客户端拒绝窗口捕获，则回退到
  `DXGI ROI`。

在支持的 Windows 版本上，控制面板本身会从屏幕捕获 API 中隐藏，避免预览窗口
递归出现在游戏画面里。

### 功能

- Tk 控制面板支持英文、中文、日文。
- 窗口选择器支持刷新，可用于 GeForce NOW、BeamNG.drive、Forza Horizon 和其他
  可见游戏窗口。
- 捕获后端选择：Auto、Window only、DXGI ROI。
- 实时预览、遥测和日志面板。
- 全局 `E` 热键用于暂停和继续。
- 自适应 LAB 路面分割兜底方案，不需要模型文件也能运行。
- Pure Pursuit 风格前视点转向。
- 通过 `vgamepad` 和 ViGEmBus 输出虚拟 Xbox 360 手柄信号。
- 安全的驾驶输出开关：可以先预览和校准，不发送控制。

### 系统要求

- Windows 10 或 Windows 11。
- Python 3.10 或更高版本。
- 云游戏客户端或本地驾驶模拟器窗口。
- 用于虚拟 Xbox 手柄输出的 ViGEmBus 驱动：
  <https://github.com/ViGEm/ViGEmBus/releases>

Python 依赖写在 [`requirements.txt`](requirements.txt)。

### 安装

```bat
cd Vision_Control
install.bat
```

安装脚本会升级 `pip`、安装运行依赖、以 editable 模式安装本包，并运行基础依赖检查。

### 运行

```bat
cd Vision_Control
launch.bat
```

也可以直接运行：

```bat
python -m vision_control.main
```

无界面模式：

```bat
python -m vision_control.main --headless --window "GeForce NOW" --capture auto
```

自检：

```bat
python -m vision_control.main --selftest
```

### 推荐云游戏设置

1. 打开云游戏客户端并启动驾驶游戏。
2. 使用第三人称追尾视角，保证道路清晰可见。
3. 打开 `launch.bat`。
4. 选择游戏窗口。
5. 捕获模式先保持 `Auto`；如果游戏上方有覆盖窗口，切到 `Window only`；如果云客户端
   返回黑屏，切到 `DXGI ROI`。
6. 点击 `Start`，等待校准状态变为 `ready`。
7. 只有在预览中的道路遮罩稳定后，再打开 `Drive output`。

### 安全说明

开启驾驶输出后，BeamNG and Horizon Driver 会向 Windows 发送真实手柄输入。校准时请
在安全测试区域运行；如果输出不符合预期，使用全局 `E` 热键或 `Stop` 按钮停止。

某些游戏或云服务可能限制自动化工具。请只在允许使用视觉辅助工具的场景中使用本项目。

### 项目结构

```text
Vision_Control/
  src/vision_control/
    capture/        window-only 和 DXGI ROI 捕获后端
    perception/     路面分割和可选模型接口
    planning/       可行驶区域提取和转向目标
    control/        虚拟手柄和键盘备援控制
    ui/             多语言控制面板
  tests/            几何逻辑单元测试
  docs/             架构和开发文档
```

### 许可证

MIT。见 [`../LICENSE`](../LICENSE)。

## 日本語

BeamNG and Horizon Driver は、BeamNG.drive、Forza Horizon 系のレースゲーム、
クラウドゲーム画面、ローカルのドライビングシミュレーター向けの Windows
ビジュアル運転アシスタントです。ゲーム API は使わず、ゲームクライアントの映像を
取得し、走行可能な路面を検出し、前方の目標点を計算して、仮想 Xbox
コントローラーからアナログ運転入力を送ります。

### v0.5.0 説明

このリリースは、GeForce NOW、Shadow PC、Xbox Cloud Gaming などの低遅延クラウド
環境、または安定したドライビングカメラを持つ Windows ゲームウィンドウ向けです。
UI は英語が既定で、操作パネルから中国語と日本語に切り替えられます。

キャプチャモードは 3 種類あります。

- `Window only`: Win32 `PrintWindow` で対象ウィンドウのクライアント領域を取得します。
  ゲーム上に重なった別のデスクトップウィンドウは認識フレームに入りません。
- `DXGI ROI`: `dxcam` のデスクトップ複製を使う高速モードです。ただし、合成後の
  デスクトップ領域を取得します。
- `Auto`: まず `Window only` を試し、クラウドクライアントが拒否した場合は
  `DXGI ROI` に戻します。

対応する Windows では、操作パネル自身を画面キャプチャ API から隠すため、プレビューが
再帰的にゲーム画面へ映り込むことを防ぎます。

### 機能

- Tk 操作パネルは英語、中国語、日本語に対応。
- GeForce NOW、BeamNG.drive、Forza Horizon、その他の表示中ゲームウィンドウを
  選択できます。
- キャプチャバックエンド選択: Auto、Window only、DXGI ROI。
- ライブプレビュー、テレメトリ、ログパネル。
- グローバル `E` ホットキーで一時停止と再開。
- モデルファイルなしで動作する適応型 LAB 路面セグメンテーション。
- Pure Pursuit 風の前方目標ステアリング。
- `vgamepad` と ViGEmBus による仮想 Xbox 360 コントローラー出力。
- 安全な運転出力スイッチ。プレビューと校正だけを先に実行できます。

### 要件

- Windows 10 または Windows 11。
- Python 3.10 以上。
- クラウドゲームクライアントまたはローカルのドライビングシミュレーターウィンドウ。
- 仮想 Xbox コントローラー出力用の ViGEmBus ドライバー:
  <https://github.com/ViGEm/ViGEmBus/releases>

Python 依存関係は [`requirements.txt`](requirements.txt) にあります。

### インストール

```bat
cd Vision_Control
install.bat
```

インストーラーは `pip` を更新し、実行時依存関係をインストールし、このパッケージを
editable モードでインストールして、基本的な依存関係チェックを実行します。

### 実行

```bat
cd Vision_Control
launch.bat
```

直接実行する場合:

```bat
python -m vision_control.main
```

ヘッドレスモード:

```bat
python -m vision_control.main --headless --window "GeForce NOW" --capture auto
```

セルフテスト:

```bat
python -m vision_control.main --selftest
```

### 推奨クラウド設定

1. クラウドゲームクライアントを開き、ドライビングゲームを起動します。
2. 道路が見やすい三人称チェイスカメラを使います。
3. `launch.bat` を開きます。
4. ゲームウィンドウを選択します。
5. まず `Auto` のままにします。ゲーム上に別ウィンドウが重なる場合は
   `Window only`、黒画面になる場合は `DXGI ROI` に切り替えます。
6. `Start` を押し、校正が `ready` になるまで待ちます。
7. プレビューの路面マスクが安定してから `Drive output` を有効にします。

### 安全上の注意

運転出力を有効にすると、BeamNG and Horizon Driver は Windows に実際の
コントローラー入力を送ります。校正中は安全なテストエリアで使い、出力が期待通りで
ない場合はグローバル `E` ホットキーまたは `Stop` ボタンで停止してください。

一部のゲームやクラウドサービスでは自動化ツールが制限される場合があります。使用が
許可されている環境でのみ利用してください。

### プロジェクト構成

```text
Vision_Control/
  src/vision_control/
    capture/        Window only と DXGI ROI のキャプチャバックエンド
    perception/     路面セグメンテーションと任意モデル用フック
    planning/       走行可能領域の抽出とステアリング目標
    control/        仮想ゲームパッドとキーボードフォールバック
    ui/             多言語操作パネル
  tests/            幾何ロジックの単体テスト
  docs/             アーキテクチャと開発メモ
```

### ライセンス

MIT。[`../LICENSE`](../LICENSE) を参照してください。
