"""
Servicio de logging RIA-V2.
Registra generaciones IA y guardados reales del redactor en las tablas ria_v2_*.
Logging es POR BLOQUE (block_type), no por celda. Un bloque puede tener N celdas.
No modifica ni depende de las tablas anteriores (ai_generations, user_edits).
"""
from collections import defaultdict
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from ..entities.ria_v2 import RiaV2GenerationLog, RiaV2SaveLog, RiaV2BlockSession
from ..entities.seccion_lp import SeccionLP
from ..utils.text_compare import clean_text, compare_texts, extract_clean_text_from_generation


MODEL_VERSION = "RIA-V2"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─────────────────────────────────────────────
# GENERACIÓN IA
# ─────────────────────────────────────────────

def log_generation(
    db: Session,
    user_id: UUID,
    landing_page_id: UUID,
    proyecto_id: UUID,
    cell_position: str,
    block_type: str,
    processed_output: dict,
    ai_generation_id: UUID | None = None,
) -> None:
    """
    Registra una generación de IA en ria_v2_generation_log.
    Llamar desde el background task de ia/controller.py.
    """
    try:
        raw_ai_text = extract_clean_text_from_generation(processed_output)
        words = clean_text(raw_ai_text)
        if not words:
            print(f"[RIA-V2] Sin texto válido para loguear en {cell_position}")
            return

        # generation_number: cuántas generaciones previas hay para este BLOQUE
        prev_count = (
            db.query(RiaV2GenerationLog)
            .filter(
                RiaV2GenerationLog.landing_page_id == landing_page_id,
                RiaV2GenerationLog.block_type == block_type,
            )
            .count()
        )
        generation_number = prev_count + 1

        # seccion_lp_id puede ser None en primera generación (sección aún no guardada)
        seccion = (
            db.query(SeccionLP)
            .filter(
                SeccionLP.landing_page_id == landing_page_id,
                SeccionLP.cell_position == cell_position,
            )
            .first()
        )

        gen_log = RiaV2GenerationLog(
            landing_page_id   = landing_page_id,
            seccion_lp_id     = seccion.id if seccion else None,
            proyecto_id       = proyecto_id,
            user_id           = user_id,
            cell_position     = cell_position,
            block_type        = block_type,
            ai_generation_id  = ai_generation_id,
            generation_number = generation_number,
            clean_text        = " ".join(words),
            word_count        = len(words),
            was_ultimately_used = None,
            model_version     = MODEL_VERSION,
            created_at        = _now(),
        )
        db.add(gen_log)

        _upsert_block_session_on_generation(
            db=db,
            user_id=user_id,
            landing_page_id=landing_page_id,
            proyecto_id=proyecto_id,
            block_type=block_type,
            generation_number=generation_number,
        )

        db.commit()
        print(f"[RIA-V2] Generación #{generation_number} logueada: {block_type} @ {cell_position}")

    except Exception as e:
        db.rollback()
        print(f"[RIA-V2] Error en log_generation: {e}")


def _upsert_block_session_on_generation(
    db: Session,
    user_id: UUID,
    landing_page_id: UUID,
    proyecto_id: UUID,
    block_type: str,
    generation_number: int,
) -> None:
    session = (
        db.query(RiaV2BlockSession)
        .filter(
            RiaV2BlockSession.landing_page_id == landing_page_id,
            RiaV2BlockSession.block_type == block_type,
        )
        .first()
    )
    now = _now()
    if session:
        session.total_generation_attempts = generation_number
        session.updated_at = now
    else:
        session = RiaV2BlockSession(
            landing_page_id           = landing_page_id,
            proyecto_id               = proyecto_id,
            user_id                   = user_id,
            block_type                = block_type,
            total_generation_attempts = 1,
            first_generation_at       = now,
            model_version             = MODEL_VERSION,
            created_at                = now,
            updated_at                = now,
        )
        db.add(session)


# ─────────────────────────────────────────────
# GUARDADO GENERAL (bulk-update) — POR BLOQUE
# ─────────────────────────────────────────────

def log_bulk_save(
    db: Session,
    user_id: UUID,
    landing_page_id: UUID,
    proyecto_id: UUID,
    sections_saved: list[dict],
) -> None:
    """
    Registra el estado de cada BLOQUE en el momento del guardado general.
    Crea UN registro por block_type (no por celda).
    Solo loguea bloques que tuvieron generación IA.
    Llamar desde el background task de secciones_lp/controller.py.
    """
    try:
        now = _now()

        # 1. Obtener todos los generation logs de esta LP
        all_gens = (
            db.query(RiaV2GenerationLog)
            .filter(RiaV2GenerationLog.landing_page_id == landing_page_id)
            .order_by(RiaV2GenerationLog.created_at.asc())
            .all()
        )
        if not all_gens:
            print(f"[RIA-V2] No hay generaciones IA para LP={landing_page_id}, skip log_bulk_save")
            return

        # 2. Vincular generaciones huérfanas (seccion_lp_id=None)
        _link_orphan_generations(db, landing_page_id, sections_saved)

        # 3. Agrupar generaciones por block_type
        block_to_gens: dict[str, list] = defaultdict(list)
        for gen in all_gens:
            block_to_gens[gen.block_type].append(gen)

        # 4. Mapear cell_position → saved content para búsqueda rápida
        cell_to_content: dict[str, str] = {
            s.get("cell_position", ""): s.get("content", "") or ""
            for s in sections_saved
            if s.get("cell_position")
        }

        # 5. Por cada bloque con generación IA, agregar texto y comparar
        blocks_logged = 0
        for block_type, gens in block_to_gens.items():
            # Última generación por celda (sobreescribir con la más reciente)
            latest_ai_by_cell: dict[str, str] = {}
            for gen in gens:
                latest_ai_by_cell[gen.cell_position] = gen.clean_text

            # Texto IA agregado del bloque
            all_ai_words: list[str] = []
            for text in latest_ai_by_cell.values():
                all_ai_words.extend(text.split())

            # Texto guardado agregado del bloque (solo celdas con contenido en este save)
            all_saved_words: list[str] = []
            for cell_pos in latest_ai_by_cell:
                saved_content = cell_to_content.get(cell_pos, "")
                if saved_content:
                    all_saved_words.extend(clean_text(saved_content))

            if not all_saved_words:
                continue

            total_gens_count = len(gens)

            prev_saves = (
                db.query(RiaV2SaveLog)
                .filter(
                    RiaV2SaveLog.landing_page_id == landing_page_id,
                    RiaV2SaveLog.block_type == block_type,
                )
                .count()
            )
            save_number = prev_saves + 1

            ai_clean_str    = " ".join(all_ai_words)
            saved_clean_str = " ".join(all_saved_words)
            comparison = compare_texts(ai_clean_str, saved_clean_str)

            last_gen = max(gens, key=lambda g: g.created_at)
            best_gen = _find_best_matching_generation_from_list(gens, saved_clean_str)

            save_log = RiaV2SaveLog(
                landing_page_id             = landing_page_id,
                seccion_lp_id               = None,
                proyecto_id                 = proyecto_id,
                user_id                     = user_id,
                cell_position               = None,
                block_type                  = block_type,
                clean_text_saved            = saved_clean_str,
                word_count_saved            = len(all_saved_words),
                last_generation_id          = last_gen.id,
                generation_number_used      = best_gen.generation_number if best_gen else None,
                total_generations_for_block = total_gens_count,
                words_from_ai               = comparison["words_from_ai"],
                words_added                 = comparison["words_added"],
                words_removed               = comparison["words_removed"],
                pct_ai_kept                 = comparison["pct_ai_kept"],
                acceptance_level            = comparison["acceptance_level"],
                save_number                 = save_number,
                model_version               = MODEL_VERSION,
                created_at                  = now,
            )
            db.add(save_log)

            if best_gen:
                best_gen.was_ultimately_used = True

            _upsert_block_session_on_save(
                db=db,
                user_id=user_id,
                landing_page_id=landing_page_id,
                proyecto_id=proyecto_id,
                block_type=block_type,
                pct_ai_kept=comparison["pct_ai_kept"],
                acceptance_level=comparison["acceptance_level"],
                generation_used_number=best_gen.generation_number if best_gen else None,
                total_gens=total_gens_count,
                now=now,
            )
            blocks_logged += 1

        db.commit()
        print(f"[RIA-V2] Save logueado: {blocks_logged} bloques en LP={landing_page_id}")

    except Exception as e:
        db.rollback()
        print(f"[RIA-V2] Error en log_bulk_save: {e}")


def _link_orphan_generations(
    db: Session,
    landing_page_id: UUID,
    sections_saved: list[dict],
) -> None:
    """Vincula generaciones con seccion_lp_id=None a sus secciones ya creadas."""
    for section in sections_saved:
        cell_pos = section.get("cell_position", "")
        if not cell_pos:
            continue
        seccion = (
            db.query(SeccionLP)
            .filter(
                SeccionLP.landing_page_id == landing_page_id,
                SeccionLP.cell_position == cell_pos,
            )
            .first()
        )
        if seccion:
            db.query(RiaV2GenerationLog).filter(
                RiaV2GenerationLog.landing_page_id == landing_page_id,
                RiaV2GenerationLog.cell_position == cell_pos,
                RiaV2GenerationLog.seccion_lp_id.is_(None),
            ).update({"seccion_lp_id": seccion.id})


def _find_best_matching_generation_from_list(
    gens: list,
    clean_saved: str,
) -> RiaV2GenerationLog | None:
    """Encuentra el intento más parecido al texto guardado (comparación sobre el bloque completo)."""
    if not gens:
        return None

    saved_words = set(clean_saved.split())
    best, best_score = None, -1

    for gen in gens:
        gen_words = set(gen.clean_text.split())
        if not gen_words:
            continue
        score = len(gen_words & saved_words) / len(gen_words)
        if score > best_score:
            best_score = score
            best = gen

    return best


def _upsert_block_session_on_save(
    db: Session,
    user_id: UUID,
    landing_page_id: UUID,
    proyecto_id: UUID,
    block_type: str,
    pct_ai_kept: float | None,
    acceptance_level: str,
    generation_used_number: int | None,
    total_gens: int,
    now: str,
) -> None:
    session = (
        db.query(RiaV2BlockSession)
        .filter(
            RiaV2BlockSession.landing_page_id == landing_page_id,
            RiaV2BlockSession.block_type == block_type,
        )
        .first()
    )

    if session:
        session.total_generation_attempts = total_gens
        session.total_saves += 1
        session.last_saved_at = now
        session.final_pct_ai_kept = pct_ai_kept
        session.final_acceptance_level = acceptance_level
        session.generation_used_number = generation_used_number
        session.went_to_manual = (acceptance_level == "manual")
        evolution = session.acceptance_evolution or []
        evolution.append(round(pct_ai_kept, 4) if pct_ai_kept is not None else None)
        session.acceptance_evolution = evolution
        session.updated_at = now
    else:
        # Buscar el timestamp de la primera generación para este bloque
        first_gen = (
            db.query(RiaV2GenerationLog)
            .filter(
                RiaV2GenerationLog.landing_page_id == landing_page_id,
                RiaV2GenerationLog.block_type == block_type,
            )
            .order_by(RiaV2GenerationLog.created_at.asc())
            .first()
        )
        session = RiaV2BlockSession(
            landing_page_id           = landing_page_id,
            proyecto_id               = proyecto_id,
            user_id                   = user_id,
            block_type                = block_type,
            total_generation_attempts = total_gens,
            generation_used_number    = generation_used_number,
            total_saves               = 1,
            first_generation_at       = first_gen.created_at if first_gen else now,
            last_saved_at             = now,
            final_pct_ai_kept         = pct_ai_kept,
            final_acceptance_level    = acceptance_level,
            acceptance_evolution      = [round(pct_ai_kept, 4) if pct_ai_kept is not None else None],
            went_to_manual            = (acceptance_level == "manual"),
            model_version             = MODEL_VERSION,
            created_at                = now,
            updated_at                = now,
        )
        db.add(session)
