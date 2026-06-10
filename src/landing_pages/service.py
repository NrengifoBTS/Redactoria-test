from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy.orm import Session
from typing import Optional, List
from . import models
from src.auth.models import TokenData
from src.entities.landing_page import LandingPage
from src.entities.proyecto import Proyecto
from src.exceptions import LandingPageCreationError, LandingPageNotFoundError
from src.auth import roles
from src.auth.permissions import get_user_role
import logging


def create_landing_page(current_user: TokenData, db: Session, landing_page: models.LandingPageCreate) -> LandingPage:
    try:
        # Solo administradores pueden crear landing pages.
        user_uuid = current_user.get_uuid()
        if not roles.can_create_landing_page(get_user_role(db, user_uuid)):
            raise LandingPageCreationError("Solo administradores pueden crear landing pages")

        # Verificar que el proyecto existe
        proyecto = db.query(Proyecto).filter(Proyecto.id == landing_page.proyecto_id).first()
        if not proyecto:
            raise LandingPageCreationError("Proyecto not found")
        
        # Verificar que no existe ya una LP para este proyecto (relación 1:1)
        existing_lp = db.query(LandingPage).filter(LandingPage.proyecto_id == landing_page.proyecto_id).first()
        if existing_lp:
            raise LandingPageCreationError("Landing page already exists for this proyecto")
        
        new_landing_page = LandingPage(
            proyecto_id=landing_page.proyecto_id,
            url_slug=landing_page.url_slug,
            title=landing_page.title,
            meta_description=landing_page.meta_description,
            is_published=False,
            created_at=datetime.now(timezone.utc)
        )
        
        db.add(new_landing_page)
        db.commit()
        db.refresh(new_landing_page)
        logging.info(f"Created new landing page for proyecto {landing_page.proyecto_id} by user: {current_user.get_uuid()}")
        return new_landing_page
    except Exception as e:
        logging.error(f"Failed to create landing page for user {current_user.get_uuid()}. Error: {str(e)}")
        raise LandingPageCreationError(str(e))

def get_landing_pages(current_user: TokenData, db: Session, is_published: Optional[bool] = None) -> List[LandingPage]:
    query = db.query(LandingPage).join(Proyecto)
    
    user_uuid = current_user.get_uuid()
    
    # Supervisores (admin/editor) pueden ver todas las landing pages
    if not roles.can_view_all_content(get_user_role(db, user_uuid)):
        # Filtrar por permisos: solo LPs de proyectos donde el usuario está involucrado
        query = query.filter(
            (Proyecto.created_by == user_uuid) | (Proyecto.assigned_to == user_uuid)
        )
    
    # Filtrar por estado de publicación si se especifica
    if is_published is not None:
        query = query.filter(LandingPage.is_published == is_published)
    
    landing_pages = query.order_by(LandingPage.created_at.desc()).all()
    logging.info(f"Retrieved {len(landing_pages)} landing pages for user: {current_user.get_uuid()}")
    return landing_pages

def get_landing_page_by_id(current_user: TokenData, db: Session, landing_page_id: UUID) -> LandingPage:
    landing_page = db.query(LandingPage).filter(LandingPage.id == landing_page_id).first()
    if not landing_page:
        logging.warning(f"Landing page {landing_page_id} not found for user {current_user.get_uuid()}")
        raise LandingPageNotFoundError(landing_page_id)
    
    user_uuid = current_user.get_uuid()
    
    # Si no es supervisor, verificar permisos a través del proyecto
    if not roles.can_view_all_content(get_user_role(db, user_uuid)):
        proyecto = db.query(Proyecto).filter(Proyecto.id == landing_page.proyecto_id).first()
        if proyecto and proyecto.created_by != user_uuid and proyecto.assigned_to != user_uuid:
            raise LandingPageNotFoundError("Insufficient permissions to access this landing page")
    
    logging.info(f"Retrieved landing page {landing_page_id} for user {current_user.get_uuid()}")
    return landing_page

def update_landing_page(current_user: TokenData, db: Session, landing_page_id: UUID, 
                       landing_page_update: models.LandingPageUpdate) -> LandingPage:
    landing_page = get_landing_page_by_id(current_user, db, landing_page_id)
    
    # Actualizar campos si se proporcionan
    update_data = landing_page_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(landing_page, field, value)
    
    landing_page.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(landing_page)
    logging.info(f"Successfully updated landing page {landing_page_id} for user {current_user.get_uuid()}")
    return landing_page

def delete_landing_page(current_user: TokenData, db: Session, landing_page_id: UUID) -> None:
    landing_page = get_landing_page_by_id(current_user, db, landing_page_id)
    
    user_uuid = current_user.get_uuid()
    
    # Verificar permisos adicionales para eliminar (solo creador del proyecto o admin)
    if not roles.is_admin(get_user_role(db, user_uuid)):
        proyecto = db.query(Proyecto).filter(Proyecto.id == landing_page.proyecto_id).first()
        if proyecto and proyecto.created_by != user_uuid:
            raise LandingPageNotFoundError("Insufficient permissions to delete this landing page")
    
    db.delete(landing_page)
    db.commit()
    logging.info(f"Landing page {landing_page_id} deleted by user {current_user.get_uuid()}")

def publish_landing_page(current_user: TokenData, db: Session, landing_page_id: UUID, is_published: bool) -> LandingPage:
    landing_page = get_landing_page_by_id(current_user, db, landing_page_id)
    
    landing_page.is_published = is_published
    if is_published:
        landing_page.published_at = datetime.now(timezone.utc)
    else:
        landing_page.published_at = None
    
    landing_page.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(landing_page)
    
    action = "published" if is_published else "unpublished"
    logging.info(f"Landing page {landing_page_id} {action} by user {current_user.get_uuid()}")
    return landing_page

def get_landing_page_by_proyecto(current_user: TokenData, db: Session, proyecto_id: UUID) -> LandingPage:
    user_uuid = current_user.get_uuid()
    # Verificar que el proyecto existe
    proyecto = db.query(Proyecto).filter(Proyecto.id == proyecto_id).first()
    if not proyecto:
        raise LandingPageNotFoundError("Associated proyecto not found")
    
    user_uuid = current_user.get_uuid()
    
    # Supervisores (admin/editor) acceden a todos los proyectos
    can_see_all = roles.can_view_all_content(get_user_role(db, user_uuid))

    if can_see_all:
        logging.info(f"✅ DEBUG: Supervisor user has access to all proyectos")
    else:
        
        # Comparar UUIDs
        created_by_match = proyecto.created_by == user_uuid
        assigned_to_match = proyecto.assigned_to == user_uuid
        
        if not (created_by_match or assigned_to_match):
            logging.warning(f"⚠️ DEBUG: User {user_uuid} doesn't have access to proyecto {proyecto_id}")
            raise LandingPageNotFoundError("Insufficient permissions to access this proyecto")
        else:
            logging.info(f"✅ DEBUG: User has specific permissions to proyecto")
    
    landing_page = db.query(LandingPage).filter(LandingPage.proyecto_id == proyecto_id).first()
    
    if not landing_page:
        
        # ✅ AGREGAR: Ver qué landing pages existen
        all_lps = db.query(LandingPage).all()
        for lp in all_lps:
            logging.info(f"🔍 DEBUG: LP {lp.id} -> proyecto_id: {lp.proyecto_id}")
        
        raise LandingPageNotFoundError("Landing page not found for this proyecto")
    return landing_page

def get_landing_page_public(db: Session, url_slug: str) -> LandingPage:
    """Obtener landing page pública por URL slug (sin autenticación)"""
    landing_page = db.query(LandingPage).filter(
        LandingPage.url_slug == url_slug,
        LandingPage.is_published == True
    ).first()
    
    if not landing_page:
        raise LandingPageNotFoundError("Published landing page not found")
    
    logging.info(f"Retrieved public landing page with slug: {url_slug}")
    return landing_page

def preview_landing_page(current_user: TokenData, db: Session, landing_page_id: UUID) -> LandingPage:
    """Preview de landing page para desarrollo/testing"""
    landing_page = get_landing_page_by_id(current_user, db, landing_page_id)
    
    # Convertir a formato público para preview
    logging.info(f"Preview landing page {landing_page_id} by user {current_user.get_uuid()}")
    return landing_page