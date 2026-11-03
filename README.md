# Papelito en la Puerta (skill de Alexa)

Los pósits de la puerta de casa, por voz. Apunta lo que no quieres olvidar y, cuando salgas, Alexa te lo recuerda.

- **Invocación:** «papelito en la puerta»
- **Idioma:** español (España)
- **Tienda:** busca «Papelito en la Puerta» en la app de Alexa

## Guía de uso

Hay dos formas de hablar con la skill:

- **En una sola frase:** «Alexa, dile a papelito en la puerta que…» o «Alexa, pregúntale a papelito en la puerta…».
- **Abriéndola primero:** «Alexa, abre papelito en la puerta». Después hablas sin repetir el nombre, por ejemplo «recuérdame comprar pan» o «qué tareas tengo».

### Apuntar una tarea puntual

Se borra cuando confirmas que la has hecho.

- «Alexa, dile a papelito en la puerta que me recuerde poner la lavadora»
- «Alexa, dile a papelito en la puerta que apunte devolver el paquete»
- «Alexa, dile a papelito en la puerta que me avise de coger el paraguas»
- Con la skill abierta: «recuérdame…», «apunta…», «añade…», «no me dejes olvidar…»

### Apuntar una tarea que se repite

Pon los días al principio o al final de la tarea. Solo te la recordará los días que toque.

- «Alexa, dile a papelito en la puerta que me recuerde **los martes y jueves** bajar la basura»
- «Alexa, dile a papelito en la puerta que me recuerde **todos los días** coger las llaves»
- «Alexa, dile a papelito en la puerta que me recuerde sacar el reciclaje **cada lunes**»
- «Alexa, dile a papelito en la puerta que me recuerde **entre semana** coger la fiambrera»
- «Alexa, dile a papelito en la puerta que me recuerde regar las plantas **los fines de semana**»

Expresiones de días que entiende:

| Expresión | Días |
|---|---|
| los lunes, cada miércoles, los sábados… | Esos días |
| los lunes, miércoles y viernes | Varios días sueltos |
| todos los días, cada día, a diario | Toda la semana |
| entre semana, de lunes a viernes, los días laborables | De lunes a viernes |
| los fines de semana | Sábado y domingo |

Si vuelves a apuntar una tarea que ya existe con otros días, se suman. Por ejemplo, con «bajar la basura los martes» ya apuntada, decir «…los jueves bajar la basura» la deja en martes y jueves.

### Al salir de casa

Te dice las tareas puntuales y las que se repiten y tocan hoy. Si hay puntuales, te pregunta si las borra: responde **«sí»** o **«no»**.

- «Alexa, dile a papelito en la puerta que **me voy**»
- «Alexa, dile a papelito en la puerta que salgo»
- «Alexa, pregúntale a papelito en la puerta **qué tengo que hacer hoy**»
- «Alexa, pregúntale a papelito en la puerta qué me toca hoy»
- «Alexa, pregúntale a papelito en la puerta qué tengo pendiente»
- «Alexa, pregúntale a papelito en la puerta de qué me tengo que acordar»

Si solo dices «Alexa, abre papelito en la puerta», también te dice lo de hoy y luego te pregunta si quieres apuntar algo más.

### Ver todas las tareas apuntadas

Te dice todas las tareas, toquen hoy o no, y los días de las que se repiten.

- «Alexa, pregúntale a papelito en la puerta **qué tareas tengo**»
- «Alexa, pregúntale a papelito en la puerta qué tengo apuntado»
- «Alexa, dile a papelito en la puerta que me lea la lista»
- Con la skill abierta: «qué tareas tengo», «lee la lista», «léeme todo», «qué hay apuntado»

### Borrar una tarea

No hace falta decir el texto exacto. Busca la tarea que más se parezca.

- «Alexa, dile a papelito en la puerta que **borre** poner la lavadora»
- «Alexa, dile a papelito en la puerta que quite la basura»
- Con la skill abierta: «ya he hecho la lavadora», «tacha comprar pan», «quita el reciclaje»

### Borrar todo

Pide confirmación antes de borrar.

- «Alexa, dile a papelito en la puerta que **borre todas las tareas**»
- Con la skill abierta: «borra todo», «vacía la lista», «empieza de cero»

### Durante la conversación

- **«sí» / «no»**: responde a las preguntas de la skill
- **«ayuda»**: explica qué puedes decir
- **«para»** o **«cancela»**: cierra la skill

### Truco: decir solo «Alexa, me voy»

En la app de Alexa, crea una **Rutina** nueva. Los nombres de los menús pueden variar según la versión de la app y si usas Alexa+.

1. **Cuando esto ocurra:** Voz → «me voy»
2. **Añadir acción:** Skills → Papelito en la Puerta

A partir de entonces, «Alexa, me voy» abre la skill y te dice lo de hoy. Si tu app no ofrece la acción «Skills», usa la frase completa: «Alexa, dile a papelito en la puerta que me voy».

### Límites y consejos

- Caben hasta 40 tareas por usuario.
- La skill usa la zona horaria de tu Echo para saber qué día es.
- Con **Alexa+**, si alguna frase no abre la skill, prueba «Alexa, abre **la skill** papelito en la puerta».
- Todavía no entiende la palabra «notas». Di «tareas» o «lista», por ejemplo «qué tareas tengo» y no «qué notas tengo».

## Desarrollo

### Estructura

- `lambda/`: código (Python 3.8, ASK SDK, DynamoDB). `tareas.py` contiene la lógica pura, sin dependencias de Alexa.
- `skill-package/`: manifiesto e interaction model. **Se despliega con el `git push`**, así que `skill.json` debe mantener el `endpoint` de Alexa-Hosted.
- `docs/`: GitHub Pages con privacidad, términos e iconos.
- `tests/`: se ejecutan con `pytest tests`. `test_skill` necesita `ask-sdk-core` instalado.

### Despliegue

Skill Alexa-Hosted `amzn1.ask.skill.a949c707-1156-42bc-bb5f-0e2f7a6a1048` (eu-west-1).

```bash
git push alexa main:master   # despliega código + skill-package en development
git push origin main         # GitHub (y Pages)
```

El remoto `alexa` usa `ask util git-credentials-helper`, que requiere `ask` con perfil `default`. Después de cada despliegue, Alexa tarda unos 3-5 minutos en propagar los cambios.

### Nombre de invocación

Antes se probaron otros nombres:

- **«mis posits»**: Alexa transcribe «pósits» con tilde y Amazon no admite tildes en el nombre de invocación.
- **«notas de salida»**: Alexa+ lo desvía a su función propia de notas.

Hay que evitar palabras de funciones nativas de Alexa: *notas*, *lista*, *recordatorio*, *alarma*.
