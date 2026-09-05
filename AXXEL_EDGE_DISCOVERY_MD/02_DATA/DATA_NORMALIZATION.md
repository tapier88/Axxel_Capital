# DATA NORMALIZATION

RAW conserva la fuente recibida sin modificar. Bronze añade identidad de fila fuente, conversión numérica explícita y UTC. Silver ordena establemente y retira únicamente duplicados exactos de origen, conservados en RAW/bronze.

No se rellenan gaps, no se recortan mechas/saltos y no se inventa spread. El contrato exige símbolo, broker, point, timeframe y semántica BAR_OPEN. Toda derivación se versiona con hashes de código, dependencias y política.

Las features se calculan únicamente después de certificar la partición. Una ventana nominal de N minutos requiere continuidad temporal; los labels futuros no cruzan la frontera de los datos DEV disponibles. Véase [Data Engine](DATA_ENGINE.md).
