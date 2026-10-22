# Comunicación de resultados (SIMULADA) - 21-10-2026

De: Estudiante (autor del prototipo)
Para: Revisor técnico (simulado); Docente de la asignatura (simulado)
Asunto: Resultados del prototipo v1.0.0 (EnergySmart Analytics)

Estimados:

Informo los resultados reales de la ejecución del prototipo con datos sintéticos.

**Pruebas automáticas:** 22 passed in 5.88s.

**Modelo (conjunto de prueba, recall antes -> después):** global 0.0969 -> 0.7401; grupo urbana 0.1117 -> 0.7513; grupo rural 0.0 -> 0.6667. Brecha de recall entre grupos: 0.1117 -> 0.0846.

**Costo de la mejora:** la precisión global baja de 0.6111 a 0.2523 (más falsas alarmas), efecto esperado al priorizar la detección.

**Pendientes para la revisión:** recall_grupo_rural>=umbral (valor 0.6667, umbral 0.7), precision_grupo_urbana>=umbral (valor 0.2706, umbral 0.3), precision_grupo_rural>=umbral (valor 0.1681, umbral 0.3).

Saludos,
Estudiante (autor del prototipo)
