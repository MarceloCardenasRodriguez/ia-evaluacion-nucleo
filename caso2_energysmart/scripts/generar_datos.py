"""Genera data/consumo_sensores_sinteticos.csv (determinista)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from energysmart import config, datos  # noqa: E402

if __name__ == "__main__":
    df = datos.generar()
    config.RUTA_DATOS.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(config.RUTA_DATOS, index=False)
    print(f"Dataset sintético generado: {config.RUTA_DATOS} ({len(df)} filas)")
