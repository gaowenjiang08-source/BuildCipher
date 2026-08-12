# Skill: Streamlit 兼容入口

## When To Use

- 你要维护 Streamlit v3 入口或 UI 页面
- 你要清理/隔离 legacy Streamlit v2 代码

## Key Files

- Streamlit v3 入口：
  - `streamlit/web_app_v3.py`
- 兼容 wrapper（保留旧文件名入口）：
  - `streamlit/web_app.py`
  - `streamlit/web_app_v3_beautiful.py`
- Streamlit UI 实现：
  - `src/cipher_genius/ui/web_v3/pages.py`
  - `src/cipher_genius/ui/web_v3/state.py`
  - `src/cipher_genius/ui/web_v3/styles.py`
- Legacy（历史版本，非维护路径）：
  - `streamlit/legacy/web_app_enhanced_v2.py`

## Invariants

- `streamlit/web_app_v3.py` 是单一维护入口（文档与提示语保持一致）
- wrapper 只做重定向，不引入业务逻辑

## Verification

- `streamlit run streamlit/web_app_v3.py`

