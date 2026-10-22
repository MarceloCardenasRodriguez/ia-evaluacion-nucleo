# Comunicación de resultados (SIMULADA) - 21-10-2026

De: Estudiante (autor del prototipo)
Para: Revisor técnico (simulado); Docente de la asignatura (simulado)
Asunto: Resultados del prototipo v1.0.0 (MedPredict Solutions)

Estimados:

Informo los resultados reales de la ejecución del prototipo con datos sintéticos.

**Pruebas automáticas:** 22 passed in 5.68s.

**Modelo (conjunto de prueba, recall antes -> después):** global 0.3421 -> 0.8224; grupo A 0.3477 -> 0.8242; grupo B 0.3125 -> 0.8125. Brecha de recall entre grupos: 0.0352 -> 0.0117.

**Costo de la mejora:** la precisión global baja de 0.7273 a 0.3582 (más falsas alarmas), efecto esperado al priorizar la detección.

**Pendientes para la revisión:** precision_grupo_B>=umbral (valor 0.2617, umbral 0.3), faltantes_maximos<=umbral (valor 0.372, umbral 0.25).

Saludos,
Estudiante (autor del prototipo)
