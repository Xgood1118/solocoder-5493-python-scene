from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.services.templates import template_service
from app.schemas.scene import SceneCreate, SceneResponse

router = APIRouter(prefix="/templates", tags=["场景模板"])


@router.get("")
async def list_templates(
    category: Optional[str] = None,
):
    return template_service.list_templates(category)


@router.get("/categories")
async def get_categories():
    return {"categories": template_service.get_categories()}


@router.get("/{template_id}")
async def get_template(template_id: str):
    template = template_service.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"模板不存在: {template_id}")
    return template.to_dict()


class ApplyTemplateRequest(BaseModel):
    custom_name: Optional[str] = None


@router.post("/{template_id}/apply", response_model=dict)
async def apply_template(
    template_id: str,
    request: ApplyTemplateRequest = ApplyTemplateRequest(),
):
    try:
        scene_create = template_service.create_scene_from_template(
            template_id, request.custom_name
        )
        return scene_create.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
