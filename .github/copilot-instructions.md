# Copilot Instructions (Submodule: sck-core-invoker)

- Tech: Python package.
- Precedence: Local first; root `../../.github/...` next.
- Conventions: See `../sck-core-ui/docs/backend-code-style.md`.

## Google Docstring Requirements
**MANDATORY**: All docstrings must use Google-style format for Sphinx documentation generation:
- Use Google-style docstrings with proper Args/Returns/Example sections
- Napoleon extension will convert Google format to RST for Sphinx processing
- Avoid direct RST syntax (`::`, `:param:`, etc.) in docstrings - use Google format instead
- Example sections should use `>>>` for doctests or simple code examples
- This ensures proper IDE interpretation while maintaining clean Sphinx documentation

## Contradiction Detection
- Validate proposals against backend conventions and root precedence.
- If conflict, warn and offer alignment options.
- Example: "Direct network calls from UI-triggered invocations without auth headers conflict with auth/session rules; use envelope + auth headers."

## Standalone clone note
If cloned standalone, see:
- UI/backend conventions: https://github.com/eitssg/simple-cloud-kit/tree/develop/sck-core-ui/docs
- Root Copilot guidance: https://github.com/eitssg/simple-cloud-kit/blob/develop/.github/copilot-instructions.md
 
