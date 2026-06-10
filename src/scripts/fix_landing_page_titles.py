"""
Normaliza los títulos de las landing pages existentes.

Bug: al crear un proyecto, la LP se guardaba con el título prefijado
     "Landing Page - {nombre}" (ver proyectos/service.py). El nombre simple
     ya vive en proyecto.name, así que el prefijo es redundante.

Este script quita el prefijo "Landing Page - " de los títulos existentes,
dejándolos simples. Es idempotente: si ya está simple, no lo toca.

Uso (con el .env apuntando a la BD correcta):
    python -m src.scripts.fix_landing_page_titles            # dry-run (solo muestra)
    python -m src.scripts.fix_landing_page_titles --apply    # aplica los cambios
"""
import sys

from src.database.core import SessionLocal
from src.entities.landing_page import LandingPage

PREFIX = "Landing Page - "


def fix_landing_page_titles(apply: bool = False) -> None:
    db = SessionLocal()
    try:
        lps = (
            db.query(LandingPage)
            .filter(LandingPage.title.like(f"{PREFIX}%"))
            .all()
        )

        if not lps:
            print("No hay landing pages con el prefijo 'Landing Page - '. Nada que hacer.")
            return

        print(f"Encontradas {len(lps)} landing pages con prefijo:\n")
        changed = 0
        for lp in lps:
            old_title = lp.title or ""
            new_title = old_title[len(PREFIX):].strip()
            if not new_title:
                print(f"  [SKIP] LP {lp.id}: el título quedaría vacío ('{old_title}'). Se omite.")
                continue
            print(f"  LP {lp.id}: '{old_title}'  ->  '{new_title}'")
            if apply:
                lp.title = new_title
            changed += 1

        if apply:
            db.commit()
            print(f"\n✓ Actualizadas {changed} landing pages.")
        else:
            print(
                f"\n(dry-run) {changed} landing pages se actualizarían. "
                f"Ejecuta con --apply para guardar los cambios."
            )
    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    fix_landing_page_titles(apply="--apply" in sys.argv)
