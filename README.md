# game-asset-validator

Noyau **commun et testable** de validation d'assets de jeu 3D : nommage (convention Unreal `SM_`, `T_`, `M_`…),
budget de triangles, UV, nombre de matériaux, échelle appliquée, taille et puissance de 2 des textures.

Il ne dépend d'aucun logiciel 3D : Blender, Maya, 3ds Max, ZBrush ou Unreal extraient un petit descripteur JSON,
et ce module le valide. Il est réutilisé par les projets MCP du même écosystème :
`blender-mcp-pipeline`, `unreal-mcp-bridge`, `maya-3dsmax-mcp-bridge`, `zbrush-mcp-bridge`, `ai-gamedev-orchestrator`.

```bash
pip install -e .[dev]
pytest -v
python -m game_asset_validator asset.json --profile mobile   # code 1 si erreurs
```

Profils : `mobile` (5 000 tris, textures 1024), `pc` (30 000, 2048), `hero` (100 000, 4096).
Les règles sont dans `game_asset_validator/rules.py` : ajoutez les vôtres, chacune est un simple test.
