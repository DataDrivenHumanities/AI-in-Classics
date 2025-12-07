from fastapi import APIRouter, HTTPException
from pathlib import Path
from typing import Any, Dict, List
import json

router = APIRouter(prefix="/api/presets", tags=["presets"])

PRESETS_PATH = Path(__file__).resolve().parent.parent / "model_presets.json"

def _load_presets() -> List[Dict[str, Any]]:
    if PRESETS_PATH.exists():
        try:
            data = json.loads(PRESETS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("presets"), list):
                return data["presets"]
        except Exception:
            return []
    return []

def _save_presets(presets: List[Dict[str, Any]]) -> None:
    payload = {"presets": presets}
    PRESETS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

@router.get("/")
async def list_presets() -> Dict[str, Any]:
    return {"presets": _load_presets()}

@router.get("/{name}")
async def get_preset(name: str) -> Dict[str, Any]:
    items = _load_presets()
    for p in items:
        if str(p.get("name", "")).lower() == name.lower():
            return p
    raise HTTPException(status_code=404, detail="Preset not found")

@router.post("/")
async def add_preset(preset: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(preset, dict) or not preset.get("name"):
        raise HTTPException(status_code=400, detail="Preset must include a 'name'")
    items = _load_presets()
    if any(str(p.get("name", "")).lower() == str(preset["name"]).lower() for p in items):
        raise HTTPException(status_code=400, detail="Preset name already exists")
    items.append(preset)
    _save_presets(items)
    return {"ok": True, "presets": items}

@router.put("/{name}")
async def update_preset(name: str, preset: Dict[str, Any]) -> Dict[str, Any]:
    items = _load_presets()
    found = False
    for i, p in enumerate(items):
        if str(p.get("name", "")).lower() == name.lower():
            new_name = preset.get("name", p.get("name"))
            items[i] = {**p, **preset, "name": new_name}
            found = True
            break
    if not found:
        raise HTTPException(status_code=404, detail="Preset not found")
    _save_presets(items)
    return {"ok": True, "presets": items}

@router.delete("/{name}")
async def delete_preset(name: str) -> Dict[str, Any]:
    items = _load_presets()
    new_items = [p for p in items if str(p.get("name", "")).lower() != name.lower()]
    _save_presets(new_items)
    return {"ok": True, "presets": new_items}
