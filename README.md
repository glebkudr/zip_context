# zip_archive

`zip_archive` is a small skill repository for quickly preparing clean project code archives for model handoff, especially for GPT-5.4 Pro style workflows.

## RU

Репозиторий нужен, чтобы быстро собирать компактные архивы кода проекта для передачи в модель Pro, не таща в архив кеши, сборку, бинарные файлы и прочий шум.

### Промпт для Codex

```text
Скачай скилл из репозитория https://github.com/glebkudr/zip_archive.git и установи его глобально.
После установки должны быть доступны две команды:
- zip — готовит архив файлов проекта для передачи в модель Pro
- update — обновляет список исключений в zip_context_ignore.md
```

### Установка вручную

```bash
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
git clone https://github.com/glebkudr/zip_archive.git /tmp/zip_archive
mkdir -p "$CODEX_HOME/skills"
rm -rf "$CODEX_HOME/skills/zip-context"
cp -R /tmp/zip_archive/zip-context "$CODEX_HOME/skills/zip-context"
```

### Использование

```bash
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
export ZIP_CONTEXT="$CODEX_HOME/skills/zip-context/scripts/zip_context.py"

python3 "$ZIP_CONTEXT" zip
python3 "$ZIP_CONTEXT" update
```

## EN

This repository exists to quickly prepare compact project code archives for a Pro model handoff without dragging in caches, build output, binaries, and other project noise.

### Prompt for Codex

```text
Download the skill from https://github.com/glebkudr/zip_archive.git and install it globally.
After installation it should expose two commands:
- zip — prepares a project file archive for a Pro model handoff
- update — refreshes the exclusion list in zip_context_ignore.md
```

### Manual install

```bash
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
git clone https://github.com/glebkudr/zip_archive.git /tmp/zip_archive
mkdir -p "$CODEX_HOME/skills"
rm -rf "$CODEX_HOME/skills/zip-context"
cp -R /tmp/zip_archive/zip-context "$CODEX_HOME/skills/zip-context"
```

### Usage

```bash
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
export ZIP_CONTEXT="$CODEX_HOME/skills/zip-context/scripts/zip_context.py"

python3 "$ZIP_CONTEXT" zip
python3 "$ZIP_CONTEXT" update
```
