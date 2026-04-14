# zip_context

`zip_context` is a small skill repository for quickly preparing clean project code archives for model handoff, especially for GPT-5.4 Pro style workflows. By default it packages the full project, and for subsystem-specific requests it can package only the relevant files.

## RU

Репозиторий нужен, чтобы быстро собирать компактные архивы кода проекта для передачи в модель Pro, не таща в архив кеши, сборку, бинарные файлы и прочий шум. По умолчанию скилл пакует весь проект, а для запросов по конкретной подсистеме умеет собирать только релевантные файлы.

### Промпт для Codex

```text
Скачай скилл из репозитория https://github.com/glebkudr/zip_context.git и установи его глобально.
После установки используй его так:
- если я прошу запаковать проект целиком, команда zip должна собрать полный архив проекта
- если я прошу запаковать файлы конкретной подсистемы или задачи, сначала найди релевантные файлы, собери их список и только потом запускай архиватор в focused-режиме
- команда update должна обновлять список исключений в zip_context_ignore.md
```

### Установка вручную

```bash
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
git clone https://github.com/glebkudr/zip_context.git /tmp/zip_context
mkdir -p "$CODEX_HOME/skills"
rm -rf "$CODEX_HOME/skills/zip-context"
cp -R /tmp/zip_context/zip-context "$CODEX_HOME/skills/zip-context"
```

### Использование

```bash
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
export ZIP_CONTEXT="$CODEX_HOME/skills/zip-context/scripts/zip_context.py"

python3 "$ZIP_CONTEXT" zip
python3 "$ZIP_CONTEXT" update
```

Focused-режим по списку путей:

```bash
cat >/tmp/billing-paths.txt <<'EOF'
billing/
apps/api/routes/billing.py
README.md
EOF

python3 "$ZIP_CONTEXT" zip --paths-file /tmp/billing-paths.txt
```

## EN

This repository exists to quickly prepare compact project code archives for a Pro model handoff without dragging in caches, build output, binaries, and other project noise. By default the skill packages the whole project, and for scoped requests it can package only the relevant files.

### Prompt for Codex

```text
Download the skill from https://github.com/glebkudr/zip_context.git and install it globally.
After installation use it like this:
- if I ask to package the whole project, zip should produce a full project archive
- if I ask to package files for a specific subsystem or task, first identify the relevant files, write the selection list, and only then run the archiver in focused mode
- update should refresh the exclusion list in zip_context_ignore.md
```

### Manual install

```bash
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
git clone https://github.com/glebkudr/zip_context.git /tmp/zip_context
mkdir -p "$CODEX_HOME/skills"
rm -rf "$CODEX_HOME/skills/zip-context"
cp -R /tmp/zip_context/zip-context "$CODEX_HOME/skills/zip-context"
```

### Usage

```bash
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
export ZIP_CONTEXT="$CODEX_HOME/skills/zip-context/scripts/zip_context.py"

python3 "$ZIP_CONTEXT" zip
python3 "$ZIP_CONTEXT" update
```

Focused mode with a paths manifest:

```bash
cat >/tmp/billing-paths.txt <<'EOF'
billing/
apps/api/routes/billing.py
README.md
EOF

python3 "$ZIP_CONTEXT" zip --paths-file /tmp/billing-paths.txt
```
