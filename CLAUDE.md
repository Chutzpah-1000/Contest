# CLAUDE.md

이 프로젝트의 정본 컨텍스트는 **`AGENTS.md`** 입니다.

Claude Code 는 현재 (2026-05) AGENTS.md 를 native 로 읽지 못하므로, 본 파일을 stub 으로 두고 실제 규칙은 AGENTS.md 에 작성합니다. 실제 작업 지침은 모두 거기를 참조하십시오.

## 빠른 참조

- 정본 지침: `AGENTS.md`
- 제품 요구사항: `docs/PRD.md`
- 기술 설계: `docs/TSD.md`
- 데이터베이스 스키마: `docs/Database.md`
- 테스트 케이스: `docs/TEST_CASE.md`

## 작업 전 반드시 통과해야 하는 명령

```bash
uv run ruff check --fix .
uv run ruff format .
uv run pyright
uv run pytest
```

## 정책

규칙·코드 스타일·금지 행위는 모두 `AGENTS.md §4~9` 를 따른다. 차이가 발견되면 AGENTS.md 가 우선이며, 본 파일을 동기화한다.
