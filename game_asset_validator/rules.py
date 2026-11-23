"""Règles de validation d'assets de jeu 3D, indépendantes de tout logiciel (Blender, Maya, 3ds Max,
ZBrush, Unreal). Chaque outil extrait un « descripteur d'asset » (un simple dict) ; ce module le valide.

Descripteur d'asset attendu :
    {
      "name": "SM_WoodenCrate",
      "kind": "static_mesh",            # static_mesh | skeletal_mesh
      "tri_count": 1240,
      "has_uv": true,
      "materials": 1,
      "scale": [1, 1, 1],               # échelle non appliquée = erreur
      "dimensions": [1.0, 1.0, 1.0],    # en mètres
      "textures": [{"name": "T_WoodenCrate_D", "width": 1024, "height": 1024}]
    }
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

PROFILES: dict[str, dict[str, int]] = {
    "mobile": {"tri_budget": 5_000, "max_texture": 1024, "max_materials": 2},
    "pc": {"tri_budget": 30_000, "max_texture": 2048, "max_materials": 4},
    "hero": {"tri_budget": 100_000, "max_texture": 4096, "max_materials": 8},
}

PREFIXES = {
    "static_mesh": "SM_",
    "skeletal_mesh": "SK_",
    "texture": "T_",
    "material": "M_",
    "material_instance": "MI_",
}

WARN_RATIO = 0.8          # avertissement à 80 % du budget de triangles
MAX_DIMENSION_M = 100.0   # au-delà, l'échelle est probablement fausse
_NAME_BODY = re.compile(r"^[A-Z][A-Za-z0-9]*(_[A-Za-z0-9]+)*$")


@dataclass(frozen=True)
class Issue:
    code: str
    severity: str  # "error" | "warning"
    message: str


@dataclass
class Report:
    asset: str
    profile: str
    issues: list[Issue] = field(default_factory=list)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict:
        return {
            "asset": self.asset,
            "profile": self.profile,
            "ok": self.ok,
            "issues": [i.__dict__ for i in self.issues],
        }


def _is_pow2(n: int) -> bool:
    return n > 0 and (n & (n - 1)) == 0


def check_name(name: str, kind: str) -> list[Issue]:
    prefix = PREFIXES.get(kind)
    if prefix is None:
        return [Issue("NAME_KIND", "error", f"type d'asset inconnu : {kind!r}")]
    if not name.startswith(prefix):
        return [Issue("NAME_PREFIX", "error", f"{name!r} doit commencer par {prefix!r}")]
    if not _NAME_BODY.match(name[len(prefix):]):
        return [Issue("NAME_FORMAT", "error", f"{name!r} : utilisez PascalCase sans espace ni caractère spécial")]
    return []


def validate(asset: dict, profile: str = "pc") -> Report:
    if profile not in PROFILES:
        raise ValueError(f"profil inconnu : {profile!r} (choix : {', '.join(PROFILES)})")
    limits = PROFILES[profile]
    report = Report(asset=asset.get("name", "<sans nom>"), profile=profile)
    add = report.issues.append

    report.issues.extend(check_name(asset.get("name", ""), asset.get("kind", "")))

    tris = asset.get("tri_count", 0)
    if tris > limits["tri_budget"]:
        add(Issue("TRI_BUDGET", "error", f"{tris} triangles > budget {limits['tri_budget']} ({profile})"))
    elif tris > limits["tri_budget"] * WARN_RATIO:
        add(Issue("TRI_NEAR_BUDGET", "warning", f"{tris} triangles : proche du budget {limits['tri_budget']}"))

    if not asset.get("has_uv", False):
        add(Issue("UV_MISSING", "error", "aucun canal UV : les textures ne pourront pas être appliquées"))

    if asset.get("materials", 0) > limits["max_materials"]:
        add(Issue("MATERIAL_COUNT", "error", f"{asset['materials']} matériaux > max {limits['max_materials']} ({profile})"))

    scale = asset.get("scale", [1, 1, 1])
    if any(abs(s - 1.0) > 1e-4 for s in scale):
        add(Issue("SCALE_NOT_APPLIED", "error", f"échelle {scale} non appliquée (attendu [1, 1, 1])"))

    dims = asset.get("dimensions")
    if dims:
        if any(d <= 0 for d in dims):
            add(Issue("DIMENSION_ZERO", "error", f"dimensions invalides : {dims}"))
        elif max(dims) > MAX_DIMENSION_M:
            add(Issue("DIMENSION_HUGE", "warning", f"dimension de {max(dims)} m : unités incorrectes ?"))

    for tex in asset.get("textures", []):
        w, h = tex["width"], tex["height"]
        report.issues.extend(check_name(tex.get("name", ""), "texture"))
        if not (_is_pow2(w) and _is_pow2(h)):
            add(Issue("TEXTURE_POW2", "error", f"{tex.get('name')} : {w}x{h} n'est pas une puissance de 2"))
        if max(w, h) > limits["max_texture"]:
            add(Issue("TEXTURE_SIZE", "error", f"{tex.get('name')} : {w}x{h} > max {limits['max_texture']} ({profile})"))

    return report
