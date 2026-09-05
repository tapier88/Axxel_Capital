# EXPERIENCE STORE

El Experience Store es el consumidor de gold de Data Engine, no una segunda entrada de mercado. `ParquetExperienceStore` mantiene filtros, similitud y replay, pero exige certificado elegible, registro gold coincidente y SHA256 antes de abrir datos. `allow_locked=True` no concede acceso.

`DataEngine.build_experiences(dataset_id)` reutiliza features y outcomes contrafactuales existentes para M1 certificado DEV. Registra el resultado en el índice de experiencias actual. La versión incorpora la receta Data Engine; los hashes de registro permiten replay. ML consume el mismo store y conserva una decisión por sesión, no tres muestras por WAIT/LONG/SHORT.

El repositorio de evidencia/memoria JSON continúa operativo. El lector de mercado JSON mezclado y los builders brutos V1/V2 se retiraron: sus artefactos históricos se conservan, pero no son certificados. No existe bypass por replay o checksum. No se abren VALIDATION ni LOCKED_OOS.

El piloto actual es EXPLORATORY_ONLY y no publica gold. Los experimentos viejos no se vuelven a ejecutar sobre otra versión sin nuevo pre-registro. Contrato: [Data Engine](DATA_ENGINE.md).
