# iPAS AI 中級刷題室

這是一個給 iPAS AI 應用規劃師中級備考用的 GitHub Pages 靜態刷題站。題庫由本資料夾中的公告試題 PDF 抽取，支援快速刷題、錯題複習、模擬考、弱點統計與原始 PDF 頁面連結。

## 本機使用

```bash
npm install
npm run extract
npm run dev
```

## 更新題庫

把新的公告試題 PDF 放在專案根目錄後，先到 `scripts/extract_questions.py` 的 `PDFS` 清單加上檔名與科目資訊，再執行：

```bash
npm run extract
```

抽取結果會寫入 `src/data/questions.json`，原始題本會複製到 `public/question-bank/` 供網站連結使用。

## 發佈到 GitHub Pages

推到 GitHub 後，在 repository 的 Settings > Pages 選擇 GitHub Actions。這個專案已包含 `.github/workflows/pages.yml`，之後 push 到 `main` 會自動 build 並發佈。
