# iaa_flutter_client

Flutter 界面用于对接新提供的 Flask API，优化 PC 端体验并兼顾移动端。

> 环境提示：当前工作流未预装 Flutter SDK，首次运行前需要在本地安装 Flutter 并执行 `flutter pub get`。

## 运行

```bash
cd flutter_client
flutter pub get
flutter run -d chrome --dart-define=IAA_API_BASE=http://localhost:5000/api
```

`IAA_API_BASE` 可根据部署的 Flask API 地址调整。
