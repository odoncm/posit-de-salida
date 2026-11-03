# Notas de Salida (skill de Alexa)

Los pósits de la puerta de casa, por voz. Invocación: **«notas de salida»** (es-ES).

- «Alexa, dile a notas de salida que me recuerde poner la lavadora» → tarea puntual
- «Alexa, dile a notas de salida que me recuerde los martes y jueves bajar la basura» → recurrente
- «Alexa, dile a notas de salida que me voy» → lee las tareas de hoy y ofrece borrar las puntuales
- «qué tareas tengo», «borra …», «borra todas las tareas»

## Estructura
- `lambda/` — código (Python 3.8, ASK SDK, DynamoDB). `tareas.py` es la lógica pura.
- `skill-package/` — manifiesto e interaction model. **Se despliega con el `git push`**, así que `skill.json` debe mantener el `endpoint` de Alexa-Hosted.
- `docs/` — GitHub Pages: privacidad, términos e iconos.
- `tests/` — `pytest tests` (test_skill necesita `ask-sdk-core` instalado).

## Despliegue
Skill Alexa-Hosted `amzn1.ask.skill.a949c707-1156-42bc-bb5f-0e2f7a6a1048` (eu-west-1).

```bash
git push alexa main:master   # despliega código + skill-package en development
git push origin main         # GitHub (y Pages)
```
El remoto `alexa` usa `ask util git-credentials-helper` (requiere `ask` con perfil `default`).
