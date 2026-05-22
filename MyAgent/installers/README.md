# 安装包说明

## Tesseract OCR（扫描件 PDF 必需）

**安装步骤：**
1. 双击运行 `tesseract/tesseract-ocr-w64-setup-5.4.0.20240606.exe`
2. 安装时勾选 **Chinese Simplified** 语言包
3. 安装完成后，将 `tesseract/chi_sim.traineddata` 复制到 Tesseract 安装目录的 `tessdata/` 文件夹下
   - 默认路径：`C:\Program Files\Tesseract-OCR\tessdata\chi_sim.traineddata`

## Python 依赖包（离线安装）

在 Win7 上离线安装这些 wheel 文件：

```bash
pip install installers/python_wheels/Pillow-9.5.0-cp37-cp37m-win32.whl
pip install installers/python_wheels/pdf2image-1.17.0-py3-none-any.whl
pip install installers/python_wheels/PyPDF2-3.0.1-py3-none-any.whl
```

或者：
```bash
pip install installers/python_wheels/*.whl --no-index
```

## 文件清单

| 文件 | 大小 | 说明 |
|------|------|------|
| `tesseract/tesseract-ocr-w64-setup-5.4.0.20240606.exe` | 47.9 MB | Tesseract OCR 安装程序 |
| `tesseract/chi_sim.traineddata` | 20.5 MB | 中文 OCR 语言包 |
| `python_wheels/Pillow-9.5.0-cp37-cp37m-win32.whl` | 2.1 MB | 图像处理库 |
| `python_wheels/pdf2image-1.17.0-py3-none-any.whl` | 11 KB | PDF 转图片（OCR 用）|
| `python_wheels/PyPDF2-3.0.1-py3-none-any.whl` | 0.2 MB | 文字型 PDF 读取 |