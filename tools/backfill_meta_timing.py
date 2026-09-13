"""
Extrai started_at, finished_at e elapsed_s dos HTMLs estáticos existentes
e salva nos .meta.json correspondentes.

Uso: python scripts/backfill_meta_timing.py [--output-dir ./output]
"""
import argparse
import json
import re
from pathlib import Path

_RE_INICIO  = re.compile(r'Início:</span>\s*([^<]+)</div>')
_RE_FIM     = re.compile(r'Fim:</span>\s*([^<]+)</div>')
_RE_ELAPSED = re.compile(r'font-size:18px;font-weight:700;color:#1e40af">([^<]+)</span>')


def _parse_elapsed_s(fmt: str) -> float | None:
    fmt = fmt.strip()
    m = re.fullmatch(r'(?:(\d+)min\s+)?(\d+)s', fmt)
    if not m:
        return None
    mins = int(m.group(1) or 0)
    secs = int(m.group(2))
    return float(mins * 60 + secs)


def backfill(output_dir: Path) -> None:
    htmls = sorted(output_dir.glob("report_*.html"))
    updated = skipped = 0

    for html_path in htmls:
        stem = html_path.stem
        meta_path = output_dir / f"{stem}.meta.json"

        html = html_path.read_text(encoding="utf-8")

        m_inicio  = _RE_INICIO.search(html)
        m_fim     = _RE_FIM.search(html)
        m_elapsed = _RE_ELAPSED.search(html)

        if not (m_inicio and m_fim and m_elapsed):
            print(f"  SKIP {stem} — campos não encontrados no HTML")
            skipped += 1
            continue

        started_at  = m_inicio.group(1).strip()
        finished_at = m_fim.group(1).strip()
        elapsed_s   = _parse_elapsed_s(m_elapsed.group(1))

        if elapsed_s is None:
            print(f"  SKIP {stem} — não foi possível parsear elapsed '{m_elapsed.group(1)}'")
            skipped += 1
            continue

        meta: dict = {}
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        if "elapsed_s" in meta:
            print(f"  OK   {stem} — já tem timing, pulando")
            skipped += 1
            continue

        meta["started_at"]  = started_at
        meta["finished_at"] = finished_at
        meta["elapsed_s"]   = elapsed_s

        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  ✓    {stem} — {started_at} → {finished_at} ({elapsed_s}s)")
        updated += 1

    print(f"\nConcluído: {updated} atualizados, {skipped} pulados.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="./output")
    args = parser.parse_args()
    backfill(Path(args.output_dir))
