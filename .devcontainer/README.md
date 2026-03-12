# Dev container operációs útmutató

## Melyik konfiguráció mit csinál

- `.devcontainer/devcontainer.json` – alapkörnyezet, **features**-al (azure-cli + docker-outside-of-docker).
- `.devcontainer/devcontainer.fallback.json` – ugyanazon képhez tartozó fallback, a feature pipeline-t kihagyó fallback build.
- `poc-backend/.devcontainer/devcontainer.json` – `poc-backend` mappa megnyitásakor használható ugyanilyen feature-alapú konfiguráció.
- `poc-backend/.devcontainer/devcontainer.fallback.json` – ugyanilyen, feature nélkül, lokális Dockerfile-alapú fallback.

## Hibaelhárítás (`docker buildx` hibára)

1. Jegyezd fel a teljes devcontainer hibaüzenetet (különösen a `failed to solve` részt).
2. Frissítsd a Docker Desktopot és ellenőrizd az alap státuszt:
   - `docker version`
   - `docker buildx version`
   - `docker buildx ls`
   - `wsl --status`
3. Újítsd le a cache-t:
   - `%TEMP%\devcontainercli` mappa törlése
4. Rebuildelj egy új buildx builderrel:
   - `docker buildx rm --all-inactive`
   - `docker buildx create --name cursor-builder --driver docker-container --use`
   - `docker buildx inspect --bootstrap`
5. Ha továbbra is ugyanaz a hiba, használd az egyik fallback fájlt:
   - Root: `devcontainer.fallback.json` a `.devcontainer` mappából
   - Backend: `poc-backend/.devcontainer/devcontainer.fallback.json`

## Smoke ellenőrzések

- Futtasd ezeket a konténerből:
  - `python --version`
  - `pip --version`
  - `az --version`
  - `docker --version`
  - `docker ps`
