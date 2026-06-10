import re
import logging
import random
from typing import List, Optional

from src.api_llm.llm_client import LLMClient, TEMP_CREATIVE, TEMP_BALANCED, TEMP_PRECISE
from src.api_llm.supervisors import parse_fields, supervisor_seo, supervisor_structure

log = logging.getLogger("content_generator")

# ── System message blocks ──────────────────────────────────────────────────────

_RESTRICCIONES = (
    "Restricciones de estructura:\n"
    "- Nunca usarás emojis.\n"
    "- Evita repetir la ciudad/estado constantemente.\n"
    "- PROHIBIDO empezar con 'Descubre' o 'Descubrir'.\n"
    "- PALABRAS SOBREUSADAS (máximo 1 vez por texto): 'Descubre', 'Encuentra', "
    "'Disfruta', 'Aprovecha'. Varía con: 'Explora', 'Vive', 'Reserva', 'Conoce', "
    "'Siente', 'Accede', 'Recorre', preguntas directas, etc.\n"
    "- Nunca usarás doble ** para negrita.\n"
    "- PROHIBIDO usar guiones largos: ni em-dash (—) ni en-dash (–). "
    "Usa siempre el guion corto normal (-) o reescribe la frase con comas.\n"
    "- Mantén el número de palabras indicado.\n"
    "- Solo usa | al inicio y final de cada bloque, NUNCA dentro del contenido.\n\n"
    "ORTOGRAFÍA ESTRICTA:\n"
    "- TODAS las tildes: vehículo, económico, kilómetro, también, más, además, "
    "fácil, aquí, así, tendrás, podrás, selección, información.\n"
    "- Concordancia género/número correcta.\n"
    "- Sin espacios antes de signos de puntuación.\n"
    "- Porcentajes SIN espacio: '35%' nunca '35 %'.\n"
    "- Capitalización normal (no ALL CAPS excepto siglas).\n"
)

_SEMANTICA = (
    "\nDISTRIBUCIÓN DE SINÓNIMOS (obligatoria en TODO el texto):\n"
    "- 'auto/autos': 70% de las menciones (keyword principal).\n"
    "- 'carro/carros': 29% de las menciones.\n"
    "- 'vehículo/vehículos': máximo 1 vez por texto.\n"
    "Verbos: Alquiler / Renta (alternar libremente).\n\n"
    "Palabras y frases ABSOLUTAMENTE PROHIBIDAS:\n"
    "- Automóvil, Flota.\n"
    "- 'cargos ocultos', 'gastos ocultos', 'pagos ocultos', 'costos ocultos', 'sin sorpresas'.\n"
    "- 'Descuentos relámpago'.\n"
    "- 'furgonetas' (usa 'vans').\n"
    "- 'SUVs' (con s) → siempre 'SUV' sin s.\n"
    "- 'autos tipo SUV', 'autos tipo Van' (suena artificial).\n\n"
    "DENSIDAD DE KW:\n"
    "No pueden aparecer 2 keywords principales (alquiler de autos, renta de carros, etc.) "
    "en menos de 50 palabras de distancia dentro del mismo párrafo.\n\n"
    "FORMATO: porcentajes SIN espacio: '35%' nunca '35 %'.\n"
)

_ESTILO_MCR = (
    "\nESTILO DE MARCA - Miles Car Rental:\n"
    "- Miles Car Rental es un COMPARADOR de tarifas de renta de autos que trabaja con "
    "múltiples agencias aliadas (Alamo, Avis, Hertz, Budget, Dollar, Enterprise, etc.). "
    "Conecta al usuario con las mejores tarifas.\n"
    "- Tono: SERIO, profesional, confiable. Enfatiza trayectoria ('más de 15 años'), "
    "alianzas con agencias prestigiosas y beneficios incluidos.\n"
    "- Público: viajeros adultos/corporativos que buscan confiabilidad.\n"
    "- Frases cortas y directas. Sin rodeos. Datos concretos.\n"
    "- Máximo 1 exclamación por párrafo.\n"
    "- Sin preguntas retóricas en el cuerpo (solo en títulos FAQ).\n"
    "- Usa: 'Miles Car Rental te conecta con las mejores agencias', "
    "'compara y reserva', 'reserva online', 'más de 15 años'.\n"
    "- BENEFICIOS EXACTOS (SOLO estos, no inventar):\n"
    "   * LATAM: Seguro de Viaje Gratis (para extranjeros), Kilómetros Ilimitados, "
    "Asistencia Básica en Carretera, Modificaciones Flexibles.\n"
    "   * IP USA: Kilómetros Ilimitados, Asistencia Básica en Carretera, "
    "Modificaciones sin cargos administrativos.\n"
    "   * IP BRA: Seguro de Viaje Gratis, Kilómetros Ilimitados, "
    "Modificaciones Flexibles, Beneficio en Cobertura del IOF.\n"
)

_ESTILO_VJM = (
    "\nESTILO DE MARCA - Viajemos:\n"
    "- Viajemos es un COMPARADOR de tarifas de renta de autos que trabaja con "
    "múltiples agencias aliadas (Alamo, Avis, Hertz, Budget, Dollar, Enterprise, etc.). "
    "Conecta al usuario con las mejores tarifas.\n"
    "- Tono: JOVIAL, fresco, cercano, entusiasta. Vocabulario dinámico, "
    "exclamaciones, apelación directa al viajero.\n"
    "- Público: viajeros jóvenes, turistas, grupos de amigos/familia.\n"
    "- Usa '¡Compara ahora!', '¡Encuentra la mejor tarifa!', '¡Anímate!', "
    "'¡Listo para tu próxima aventura!', 'Con Viajemos'.\n"
    "- Enfatiza: variedad de agencias, ahorro al comparar, libertad de viaje, diversión.\n"
    "- NO uses 'nuestra flota', 'nuestros autos' (Viajemos no tiene autos propios). "
    "SÍ usa 'los mejores precios', 'las mejores agencias'.\n"
)

_BASE_INTRO = (
    "Vas a pensar en español, recibirás instrucciones en español y deberás "
    "responder en español (español neutro latinoamericano).\n"
    "Eres un redactor experto en marketing digital SEO, especializado en "
    "contenidos para una agencia comparadora de renta de autos.\n\n"
)

SYSTEM_MCR = _BASE_INTRO + _RESTRICCIONES + _SEMANTICA + _ESTILO_MCR
SYSTEM_VJM = _BASE_INTRO + _RESTRICCIONES + _SEMANTICA + _ESTILO_VJM

_BRAND_SYSTEMS = {
    "mcr": SYSTEM_MCR,
    "viajemos": SYSTEM_VJM,
    "vjm": SYSTEM_VJM,
}

# ── Beneficios estándar por audiencia ──────────────────────────────────────────

_BENEFICIOS_LATAM = (
    "Seguro de Viaje Gratis para extranjeros, Kilómetros Ilimitados, "
    "Asistencia Básica en Carretera, Modificaciones Flexibles"
)
_BENEFICIOS_USA = (
    "Kilómetros Ilimitados, Conductor Adicional sin Costo extra, "
    "Asistencia Básica en Carretera, Modificaciones Flexibles"
)
# MCR IP USA: sin "Conductor Adicional" — igual que colorUtils.js BENEFICIOS_USA_MCR
_BENEFICIOS_USA_MCR = (
    "Kilómetros Ilimitados, Asistencia Básica en Carretera, "
    "Modificaciones sin cargos administrativos"
)
_BENEFICIOS_BRA = (
    "Seguro de Viaje Gratis para extranjeros, Kilómetros Ilimitados, "
    "Asistencia Básica en Carretera, Modificaciones Flexibles, "
    "Beneficio en Cobertura del IOF"
)

# Beneficios exclusivos Viajemos (incluyen Salas VIP y Promociones Exclusivas)
_BENEFICIOS_LATAM_VJM = (
    "Seguro de Viaje Gratis para extranjeros, Kilómetros Ilimitados, "
    "Asistencia Básica en Carretera, Modificaciones Flexibles, "
    "Acceso a Salas VIP, Reservas con Promociones Exclusivas hasta el 35%"
)
_BENEFICIOS_USA_VJM = (
    "Kilómetros Ilimitados, Conductor Adicional sin Costo extra, "
    "Asistencia Básica en Carretera, Modificaciones Flexibles, "
    "Acceso a Salas VIP, Reservas con Promociones Exclusivas hasta el 35%"
)
_BENEFICIOS_BRA_VJM = (
    "Seguro de Viaje Gratis para extranjeros, Kilómetros Ilimitados, "
    "Asistencia Básica en Carretera, Modificaciones Flexibles, "
    "Beneficio en Cobertura del IOF, "
    "Acceso a Salas VIP, Reservas con Promociones Exclusivas hasta el 35%"
)

# Favorite Cities: fallback determinista para evitar celdas vacias cuando el LLM no
# respeta el formato pipe en bloques largos.
_FAV_CITY_DEFAULTS = [
    ("Miami", "Alquiler de autos en Miami", "¡Miami te espera! Recorre South Beach, Wynwood y Downtown con total libertad al volante. Compara tarifas y reserva en minutos."),
    ("Orlando", "Renta de autos en Orlando", "Parques tematicos, compras y escapadas cercanas. Con renta de autos en Orlando viajas a tu ritmo y sin depender de horarios."),
    ("Las Vegas", "Alquiler de autos en Las Vegas", "Del Strip al desierto, cada ruta se disfruta mejor con auto propio. Encuentra ofertas y reserva tu carro ideal en segundos."),
    ("Nueva York", "Renta de autos en Nueva York", "Aprovecha tu viaje para explorar mas alla de Manhattan. Renta un auto y conecta barrios, outlets y rutas panoramicas con comodidad."),
    ("Los Angeles", "Alquiler de autos en Los Angeles", "Playas, estudios y carreteras iconicas te esperan. Compara precios de alquiler de autos y elige la opcion ideal para tu aventura."),
    ("Houston", "Renta de autos en Houston", "Recorre Houston con libertad total: museos, gastronomia y zonas comerciales. Reserva con tarifa competitiva y disponibilidad inmediata."),
    ("Chicago", "Alquiler de autos en Chicago", "Explora arquitectura, parques y barrios emblematicos sin limites. Alquila un auto y organiza tu itinerario con total autonomia."),
    ("Fort Lauderdale", "Renta de autos en Fort Lauderdale", "Sol, canales y playas inolvidables. Con renta de autos en Fort Lauderdale disfrutas cada trayecto con mayor comodidad."),
    ("San Diego", "Alquiler de autos en San Diego", "Disfruta la costa, La Jolla y Gaslamp Quarter a tu propio ritmo. Compara tarifas y reserva tu auto con facilidad."),
    ("Dallas", "Renta de autos en Dallas", "Negocios, cultura y entretenimiento en una sola ciudad. Renta un auto en Dallas y mueve tu viaje con eficiencia."),
    ("Phoenix", "Alquiler de autos en Phoenix", "Ideal para rutas por el desierto y escapadas cercanas. Alquila un auto en Phoenix y viaja con independencia total."),
    ("Tampa", "Renta de autos en Tampa", "Desde Tampa Bay hasta Clearwater, cada plan mejora con movilidad propia. Encuentra la mejor tarifa y reserva hoy."),
    ("San Francisco", "Alquiler de autos en San Francisco", "Golden Gate, miradores y escapadas a Napa. Con alquiler de autos en San Francisco llegas a todo sin complicaciones."),
    ("Atlanta", "Renta de autos en Atlanta", "Historia, negocios y vida urbana en movimiento. Renta un auto en Atlanta y optimiza cada trayecto de tu viaje."),
    ("Denver", "Alquiler de autos en Denver", "Montanas, naturaleza y ciudad en un mismo destino. Alquila un auto en Denver y disfruta rutas panoramicas inolvidables."),
    ("Austin", "Renta de autos en Austin", "Musica en vivo, gastronomia y plan al aire libre. Renta de autos en Austin para descubrir la ciudad sin limites."),
    ("CBX", "Alquiler de autos en CBX", "Cruza con facilidad y continua tu viaje en carretera. Compara opciones de alquiler de autos en CBX y reserva al mejor precio."),
]

class ContentGenerator:

    @staticmethod
    def _normalize_brand(brand: str) -> str:
        b = (brand or "mcr").strip().lower()
        if b in {"mcr", "miles", "miles car rental", "milescarrental", "miles_car_rental"}:
            return "mcr"
        if b in {"vjm", "viajemos", "viajemos.com", "viajemos autos"}:
            return "vjm"
        return b

    def __init__(self, llm_client: Optional[LLMClient] = None, brand: str = "mcr", fast_mode: bool = False):
        self.brand = self._normalize_brand(brand)
        self.llm = llm_client or LLMClient()
        self.system_message = _BRAND_SYSTEMS.get(self.brand, SYSTEM_MCR)
        # fast_mode: omite el paso de supervisión SEO por LLM (más rápido, menos pulido).
        self.fast_mode = fast_mode

    @property
    def brand_name(self) -> str:
        return "Viajemos" if self.brand in ("vjm", "viajemos") else "Miles Car Rental"

    def sanitize_city_name(self, raw_city: str) -> str:
        """Normaliza etiquetas de ciudad para evitar frases SEO largas como títulos H3."""
        c = (raw_city or "").strip()
        if not c:
            return ""

        known_city_names = [item[0] for item in _FAV_CITY_DEFAULTS]
        for kc in sorted(known_city_names, key=len, reverse=True):
            if re.search(rf"\b{re.escape(kc)}\b", c, flags=re.IGNORECASE):
                return kc

        c = re.sub(
            r"(?i)^(alquiler de autos en|renta de autos en|renta de carros en|"
            r"alquiler de carros en|rentar un auto en|reservar un auto en|"
            r"mejores ciudades para renta de autos(?: de lujo)? en|"
            r"destinos imperdibles para alquilar un auto desde|"
            r"ciudades populares para rentar un auto cerca de)\s*",
            "",
            c,
        ).strip(" .,-:;")

        c = re.split(r"(?i)\b(y|con|para|sin|desde)\b", c)[0].strip(" .,-:;")
        c = re.sub(r"[^A-Za-zÁÉÍÓÚáéíóúÑñ\s-]", "", c)
        c = re.sub(r"\s+", " ", c).strip()

        token_count = len(c.split())
        if token_count == 0 or token_count > 4:
            return ""

        bad_terms = {
            "alquiler", "renta", "autos", "carros", "carro", "auto", "lujo",
            "recorre", "costa", "limites", "mejores", "ciudades", "destinos",
        }
        if any(tok.lower() in bad_terms for tok in c.split()):
            return ""

        return c

    # ── Utilidades internas ────────────────────────────────────────────────────

    def _call(self, prompt: str, temperature: float = TEMP_BALANCED,
              retries: int = 2) -> str:
        """Llama al modelo con reintentos. Devuelve raw para parseo posterior."""
        for attempt in range(retries + 1):
            raw = self.llm.generate(prompt, self.system_message, temperature=temperature)
            if raw and raw.strip():
                return raw
            if attempt < retries:
                log.warning("Respuesta vacía, intento %d/%d...", attempt + 1, retries + 1)
        log.error("El modelo devolvió vacío tras %d intentos", retries + 1)
        return ""

    def _parse_and_supervise(self, raw: str, tit_default: str = "") -> str:
        """
        Pipeline 3-pass adaptado del Cargue Masivo (supervise_fields):
          1. Parsea campos |key: value| del raw LLM
          2. Fallback: si falta 'tit', usa tit_default
          3. supervisor_seo   → corrige KWs, homologaciones, ortografía (LLM)
          4. supervisor_structure → limpia formato (regex)
          5. Reconstruye y devuelve formato pipe

        El campo 'tit' no se supervisa (demasiado corto para el supervisor SEO).
        Si el parseo no produce campos, devuelve raw intacto.
        """
        fields = parse_fields(raw)

        if tit_default and not fields.get("tit"):
            fields["tit"] = tit_default

        if not fields:
            clean = re.sub(r"<think>.*?</think>", "", raw or "", flags=re.DOTALL).strip()
            clean = re.sub(r"^\|\s*\w+\s*:\s*", "", clean)
            clean = clean.replace("|", " ").strip()
            clean = re.sub(r"\s+", " ", clean)
            if tit_default and clean:
                return f"|tit: {tit_default}|\n|desc: {clean}|"
            if tit_default:
                return f"|tit: {tit_default}|"
            return raw

        supervised = {}
        for key, value in fields.items():
            if not value or key == "tit" or len(value.split()) < 5:
                supervised[key] = value
                continue
            if not self.fast_mode:
                value = supervisor_seo(value, self.llm, key) or value
            value = supervisor_structure(value) or value
            supervised[key] = value

        return "\n".join(f"|{k}: {v}|" for k, v in supervised.items())

    # ── Bloques de generación ──────────────────────────────────────────────────

    def generate_quicksearch(self, tit_seo: str, nuevo_tema: str) -> str:
        """B1 — Hero: título H1 + descripción corta (15-20 palabras)."""
        if self.brand == "mcr":
            examples = (
                "Ejemplos de referencia:\n"
                "Ejemplo 1: tit: Alquiler de Autos en Miami, FL, "
                "desc: Tu próximo viaje por Miami empieza con la flota correcta. Miles Car Rental, más de 15 años conectando viajeros.\n"
                "Ejemplo 2: tit: Renta de Autos en Orlando, FL, "
                "desc: En Orlando cada destino está más cerca con un auto rentado. Elige tu categoría y reserva en minutos con Miles Car Rental.\n"
                "Ejemplo 3: tit: Alquiler de Autos en Las Vegas, NV, "
                "desc: Recorre Las Vegas y sus alrededores a tu ritmo. Miles Car Rental te ofrece las mejores opciones con respaldo garantizado.\n\n"
            )
        else:
            examples = (
                "Ejemplos de referencia:\n"
                "Ejemplo 1: tit: Alquiler de Autos en Miami, FL, "
                "desc: ¡Priorizamos tu ahorro y garantizamos más beneficios! "
                "Encuentra aquí el mejor precio en renta de carros en Miami, Florida.\n"
                "Ejemplo 2: tit: Renta de Autos en Orlando, FL, "
                "desc: Compara tarifas, elige tu auto y reserva en minutos. "
                "Los mejores precios en alquiler de carros en Orlando te esperan.\n\n"
            )
        if self.brand == "mcr":
            rules = (
                "REGLAS:\n"
                "- El H1 puede ser el título base o una variante SEO levemente mejorada.\n"
                "- La descripción: EXACTAMENTE 15 a 20 palabras.\n"
                "- Tono profesional y confiable, sin exclamaciones.\n"
                "- La descripción habla del destino o de la experiencia de viaje, NO de agencias específicas ni beneficios técnicos.\n"
                "- PROHIBIDO en la descripción: nombres de agencias (Alamo, Dollar, Avis, Budget, etc.), "
                "kilómetros ilimitados, asistencia en carretera, depósito, o cualquier beneficio técnico.\n"
            )
        else:
            rules = (
                "REGLAS:\n"
                "- El H1 puede ser el título base o una variante SEO levemente mejorada.\n"
                "- La descripción: EXACTAMENTE 15 a 20 palabras.\n"
                "- Tono cercano y dinámico.\n"
            )
        prompt = (
            f"{examples}"
            f"Nuevo tema: {nuevo_tema}, TÍTULO SEO base: {tit_seo}\n"
            f"{rules}"
            "Genera con un ángulo diferente a los ejemplos:\n"
            "|tit: H1 SEO|\n"
            "|desc: redacción de 15 a 20 palabras|"
        )
        raw = self._call(prompt, temperature=TEMP_CREATIVE)
        result = self._parse_and_supervise(raw, tit_default=tit_seo)
        fields = parse_fields(result)
        if not fields.get("desc"):
            location = self._extract_location_from_title(nuevo_tema)
            if self.brand == "mcr":
                _qs_fallbacks = [
                    f"Tu próximo viaje por {location} empieza con la flota correcta. {self.brand_name}, más de 15 años conectando viajeros.",
                    f"En {location} cada destino está más cerca con un auto rentado. Elige tu categoría y reserva con {self.brand_name}.",
                    f"Recorre {location} y sus alrededores a tu ritmo. {self.brand_name} te ofrece las mejores opciones con respaldo garantizado.",
                ]
                import hashlib as _hqs
                _fi = int(_hqs.md5(nuevo_tema.encode()).hexdigest(), 16) % len(_qs_fallbacks)
                fields["desc"] = _qs_fallbacks[_fi]
            else:
                _qs_fallbacks_vjm = [
                    f"Mueve tu plan por {location} con más libertad. Compara opciones y elige la tarifa que mejor se ajusta a tu viaje.",
                    f"¿Listo para recorrer {location} a tu ritmo? Compara precios de alquiler y encuentra una opción ideal para tu aventura.",
                    f"En {location}, tu viaje mejora cuando decides tus horarios. Revisa tarifas, elige categoría y comienza a disfrutar el camino.",
                    f"Explorar {location} es más fácil con movilidad propia. Compara alternativas y encuentra un auto que encaje con tu itinerario.",
                ]
                fields["desc"] = random.choice(_qs_fallbacks_vjm)
        return "\n".join(f"|{k}: {v}|" for k, v in fields.items())

    def generate_fleet(self, tit_seo: str, nuevo_tema: str) -> str:
        """B2 — Fleet: descripción principal + variantes ip_usa e ip_bra (80-130 palabras)."""
        location = self._extract_location_from_title(nuevo_tema)
        import hashlib as _hfleet_tit
        _fleet_tit_variants = [
            f"Alquiler de autos en {location}: opciones para cada viajero",
            f"Renta de autos en {location}: elige tu categoría ideal",
            f"Variedad de autos en alquiler en {location}",
            f"Opciones de renta de autos en {location}",
        ]
        _tit_idx = int(_hfleet_tit.md5(nuevo_tema.encode()).hexdigest(), 16) % len(_fleet_tit_variants)
        tit = _fleet_tit_variants[_tit_idx]
        import hashlib as _hfleet
        _fleet_angles = [
            "prioriza practicidad para viajes con agenda intensa",
            "enfatiza comodidad para recorridos largos y rutas mixtas",
            "resalta equilibrio entre presupuesto y categoria",
            "destaca libertad para combinar ciudad y alrededores",
        ]
        _angle_idx = int(_hfleet.md5(nuevo_tema.encode()).hexdigest(), 16) % len(_fleet_angles)
        angle = _fleet_angles[_angle_idx]

        # Selección de beneficios según marca
        is_vjm = self.brand in ("vjm", "viajemos")
        _ben_latam = _BENEFICIOS_LATAM_VJM if is_vjm else _BENEFICIOS_LATAM
        _ben_bra = _BENEFICIOS_BRA_VJM if is_vjm else _BENEFICIOS_BRA
        ip_usa_benefits = (
            _BENEFICIOS_USA_VJM if is_vjm else (
                _BENEFICIOS_USA_MCR if self.brand == "mcr" else _BENEFICIOS_USA
            )
        )

        prompt = (
            "Redacta un texto de 125 a 130 palabras para la sección fleet de una landing SEO.\n"
            f"Contexto: {nuevo_tema}.\n"
            f"Titulo de sección: {tit}.\n\n"
            "Reglas:\n"
            "- Tono comercial, claro y confiable.\n"
            "- Menciona variedad de autos: compactos, SUV, vans, convertibles y lujo.\n"
            f"- Angulo de redaccion: {angle}.\n"
            "- Cierre con llamado a comparar y reservar.\n"
            f"- Debe incluir EXACTAMENTE esta frase de beneficios: {_ben_latam} y mucho más.\n"
            "- Devuelve SOLO: |desc: ...|"
        )

        raw = self._call(prompt, temperature=TEMP_PRECISE)
        fields = parse_fields(raw)
        desc = (fields.get("desc") or "").strip()

        if not desc or len(desc.split()) < 40:
            _fleet_desc_templates = [
                (
                    f"Compara tarifas de alquiler de autos en {location} y elige entre compactos, SUV, "
                    "vans, convertibles y autos de lujo para cada tipo de viaje. "
                    f"Incluye: {_ben_latam} y mucho más. "
                    "Con opciones flexibles, proceso de reserva simple y aliados reconocidos, "
                    "puedes asegurar la mejor alternativa para tu itinerario. "
                    "Reserva online y recorre tu destino con comodidad y respaldo."
                ),
                (
                    f"Si tu plan en {location} combina traslados urbanos y rutas mas largas, "
                    "te conviene revisar categorias con distintos niveles de espacio y confort. "
                    f"Incluye: {_ben_latam} y mucho más. "
                    "Compara opciones, valida condiciones y reserva una alternativa alineada "
                    "con tu agenda para viajar con mayor eficiencia y tranquilidad."
                ),
                (
                    f"Para moverte por {location} con mejor control del tiempo, "
                    "elige entre autos compactos, SUV, vans, convertibles y lujo segun tu itinerario. "
                    f"Incluye: {_ben_latam} y mucho más. "
                    "Con una reserva clara y categorias bien definidas, encuentras una opcion "
                    "equilibrada entre presupuesto, comodidad y funcionalidad."
                ),
                (
                    f"En {location} puedes ajustar tu experiencia de viaje con categorias para distintos escenarios: "
                    "trayectos cortos, planes familiares o rutas de mayor distancia. "
                    f"Incluye: {_ben_latam} y mucho más. "
                    "Compara alternativas, confirma disponibilidad y reserva online con una propuesta "
                    "practica para viajar con respaldo y flexibilidad."
                ),
            ]
            desc = _fleet_desc_templates[_angle_idx % len(_fleet_desc_templates)]

        if _ben_latam not in desc:
            desc = (
                f"{desc.strip()} Incluye: {_ben_latam} y mucho más."
            )

        ip_usa = desc.replace(_ben_latam, ip_usa_benefits)
        ip_bra = desc.replace(_ben_latam, _ben_bra)

        if ip_usa == desc:
            _ip_usa_templates = [
                (
                    f"Compara tarifas de alquiler de autos en {location} y elige entre compactos, SUV, "
                    "vans, convertibles y autos de lujo para cada plan de viaje. "
                    f"Incluye: {ip_usa_benefits} y mucho más. "
                    "Con reserva simple y opciones flexibles, encuentras una alternativa ideal "
                    "para moverte con comodidad y buen precio."
                ),
                (
                    f"Organiza mejor tus traslados en {location} comparando categorias segun tipo de ruta y cantidad de pasajeros. "
                    f"Incluye: {ip_usa_benefits} y mucho más. "
                    "Con un proceso claro de seleccion y reserva, puedes asegurar una opcion funcional "
                    "para tu agenda de viaje."
                ),
            ]
            ip_usa = _ip_usa_templates[_angle_idx % len(_ip_usa_templates)]

        if ip_bra == desc:
            _ip_bra_templates = [
                (
                    f"Compara tarifas de alquiler de autos en {location} y elige entre compactos, SUV, "
                    "vans, convertibles y autos de lujo para cada tipo de itinerario. "
                    f"Incluye: {_ben_bra} y mucho más. "
                    "Con proceso de reserva rápido y respaldo de agencias reconocidas, "
                    "puedes asegurar una experiencia cómoda y eficiente."
                ),
                (
                    f"Para viajes en {location} con diferentes ritmos de movilidad, conviene evaluar categorias por espacio, confort y uso previsto. "
                    f"Incluye: {_ben_bra} y mucho más. "
                    "Compara alternativas disponibles y confirma una reserva acorde a tu plan "
                    "con mayor flexibilidad operativa."
                ),
            ]
            ip_bra = _ip_bra_templates[_angle_idx % len(_ip_bra_templates)]

        desc = supervisor_structure(supervisor_seo(desc, self.llm, "desc") or desc) or desc
        ip_usa = supervisor_structure(supervisor_seo(ip_usa, self.llm, "ip_usa") or ip_usa) or ip_usa
        ip_bra = supervisor_structure(supervisor_seo(ip_bra, self.llm, "ip_bra") or ip_bra) or ip_bra

        return "\n".join([
            f"|tit: {tit}|",
            f"|desc: {desc}|",
            f"|ip_usa: {ip_usa}|",
            f"|ip_bra: {ip_bra}|",
        ])

    def generate_deals(self, tit_seo: str, nuevo_tema: str) -> str:
        """Deals — sección de ofertas: descripción H2 + variantes ip_usa e ip_bra (80-85 palabras)."""
        location = self._extract_location_from_title(nuevo_tema)
        tit = f"Ofertas de alquiler de autos en {location}"
        import hashlib as _hdeals
        _deals_angles = [
            "resalta el ahorro y las tarifas competitivas para distintas categorías",
            "enfatiza la variedad de ofertas según duración del alquiler",
            "destaca las promociones y beneficios exclusivos para viajeros",
            "resalta la flexibilidad de precios y opciones para cada presupuesto",
        ]
        _angle_idx = int(_hdeals.md5(nuevo_tema.encode()).hexdigest(), 16) % len(_deals_angles)
        angle = _deals_angles[_angle_idx]

        prompt = (
            "Redacta un texto de 80 a 85 palabras para la sección de ofertas de una landing SEO.\n"
            f"Contexto: {nuevo_tema}.\n"
            f"Titulo de sección: {tit}.\n\n"
            "Reglas:\n"
            "- Tono comercial, claro y confiable. PROHIBIDO usar exclamaciones.\n"
            "- Menciona que hay ofertas para distintas categorías de autos.\n"
            f"- Angulo de redaccion: {angle}.\n"
            "- Cierre con llamado a comparar tarifas y reservar.\n"
            f"- Debe incluir EXACTAMENTE esta frase de beneficios: {_BENEFICIOS_LATAM} y mucho más.\n"
            "- Devuelve SOLO: |desc: ...|"
        )

        raw = self._call(prompt, temperature=TEMP_PRECISE)
        fields = parse_fields(raw)
        desc = (fields.get("desc") or "").strip()

        if not desc or len(desc.split()) < 40:
            _deals_desc_templates = [
                (
                    f"Compara tarifas de alquiler de autos en {location} y aprovecha las mejores ofertas "
                    "en economicos, SUV, vans, convertibles y autos de lujo para cada plan de viaje. "
                    f"Incluye: {_BENEFICIOS_LATAM} y mucho más. "
                    "Con descuentos por temporada y tarifas semanales competitivas, "
                    "puedes reservar online y asegurar la mejor alternativa para tu itinerario."
                ),
                (
                    f"Encuentra las mejores ofertas en renta de autos en {location} y elige entre "
                    "distintas categorias segun tu presupuesto y necesidades de viaje. "
                    f"Incluye: {_BENEFICIOS_LATAM} y mucho más. "
                    "Compara tarifas actualizadas, valida condiciones y reserva la opcion "
                    "que mejor se adapte a tu agenda con respaldo garantizado."
                ),
                (
                    f"Para moverte por {location} con mejor relacion calidad-precio, "
                    "revisa las ofertas disponibles en compactos, SUV, vans y autos de lujo. "
                    f"Incluye: {_BENEFICIOS_LATAM} y mucho más. "
                    "Con tarifas competitivas y proceso de reserva simple, "
                    "encontrar la mejor oferta para tu viaje nunca fue tan facil."
                ),
                (
                    f"Accede a las ofertas de alquiler de autos en {location} y elige entre "
                    "categorias para cada tipo de viaje: desde economicos hasta lujo y vans familiares. "
                    f"Incluye: {_BENEFICIOS_LATAM} y mucho más. "
                    "Compara alternativas, confirma disponibilidad y reserva online con "
                    "tarifas transparentes y respaldo de agencias reconocidas."
                ),
            ]
            desc = _deals_desc_templates[_angle_idx % len(_deals_desc_templates)]

        if _BENEFICIOS_LATAM not in desc:
            desc = f"{desc.strip()} Incluye: {_BENEFICIOS_LATAM} y mucho más."

        ip_usa_benefits = _BENEFICIOS_USA_MCR if self.brand == "mcr" else _BENEFICIOS_USA
        ip_usa = desc.replace(_BENEFICIOS_LATAM, ip_usa_benefits)
        ip_bra = desc.replace(_BENEFICIOS_LATAM, _BENEFICIOS_BRA)

        if ip_usa == desc:
            ip_usa = (
                f"Compara tarifas de ofertas de alquiler de autos en {location} y elige entre "
                "economicos, SUV, vans, convertibles y autos de lujo para cada plan de viaje. "
                f"Incluye: {ip_usa_benefits} y mucho más. "
                "Con reserva simple y tarifas competitivas, aseguras la mejor oferta "
                "para moverte con comodidad y buen precio."
            )

        if ip_bra == desc:
            ip_bra = (
                f"Compara tarifas de ofertas de alquiler de autos en {location} y elige entre "
                "economicos, SUV, vans, convertibles y autos de lujo para cada itinerario. "
                f"Incluye: {_BENEFICIOS_BRA} y mucho más. "
                "Con proceso de reserva rapido y respaldo de agencias reconocidas, "
                "puedes asegurar la mejor oferta con comodidad y eficiencia."
            )

        desc = supervisor_structure(supervisor_seo(desc, self.llm, "desc") or desc) or desc
        ip_usa = supervisor_structure(supervisor_seo(ip_usa, self.llm, "ip_usa") or ip_usa) or ip_usa
        ip_bra = supervisor_structure(supervisor_seo(ip_bra, self.llm, "ip_bra") or ip_bra) or ip_bra

        return "\n".join([
            f"|tit: {tit}|",
            f"|desc: {desc}|",
            f"|ip_usa: {ip_usa}|",
            f"|ip_bra: {ip_bra}|",
        ])
        """Reviews / Rent companies — H2 propio + descripción (35-40 palabras)."""
        brand_name = self.brand_name
        if self.brand == "mcr":
            example = (
                "tit: Reseñas de renta de autos en Miami, "
                "desc_h2: Más de 15 años conectando viajeros con las mejores tarifas. "
                "Nuestros clientes destacan la facilidad del proceso, el respaldo de las agencias aliadas "
                "y la atención recibida antes y después de cada reserva."
            )
            tono = f"tono confiable y profesional, menciona {brand_name} o la trayectoria de 15 años"
        else:
            example = (
                "tit: Reseñas de renta de autos en Miami, "
                "desc_h2: ¡Miles de viajeros ya eligieron sus autos con nosotros! "
                "Compara, reserva y viaja con la confianza de quienes ya conocen la mejor forma "
                "de alquilar un auto al mejor precio."
            )
            tono = "tono cercano y entusiasta, menciona la comunidad de viajeros satisfechos"
        prompt = (
            f"Ejemplo de referencia:\n{example}\n\n"
            f"Nuevo tema: {nuevo_tema}, contexto LP: {tit_seo}\n"
            "REGLAS:\n"
            "- tit: H2 específico para la sección de reseñas/opiniones de clientes. "
            "Ejemplos válidos: 'Opiniones sobre alquiler de autos en Miami' / "
            "'Reseñas de clientes que rentaron en Orlando, FL'.\n"
            f"- desc_h2: 35 a 40 palabras. {tono.capitalize()}.\n"
            "Genera:\n"
            "<think>aquí tus pensamientos</think>\n"
            "|tit: H2 para sección de reseñas|\n"
            "|desc_h2: redacción|"
        )
        raw = self._call(prompt, temperature=TEMP_BALANCED)
        tit_default = f"Opiniones sobre alquiler de autos — {nuevo_tema}"
        return self._parse_and_supervise(raw, tit_default=tit_default)

    def generate_agencies(self, tit_seo: str, nuevo_tema: str) -> str:
        """B3 — Agencias: H2 propio (50-65 palabras) + H3 (20-35 palabras)."""
        brand_name = self.brand_name
        location = self._extract_location_from_title(nuevo_tema)

        if self.brand == "mcr":
            examples = (
                "Ejemplos de referencia (desc_h2: Miles Car Rental como plataforma que conecta al viajero con agencias líderes):\n\n"
                "Ejemplo 1:\n"
                "tit: Agencias de alquiler de autos en Miami\n"
                "desc_h2: Con Miles Car Rental tienes acceso directo a las mejores agencias de renta en Miami: Avis, Alamo, Hertz, Budget y más. "
                "Más de 15 años conectando viajeros con tarifas competitivas y el respaldo de marcas reconocidas. "
                "Compara, elige y reserva con total confianza.\n"
                "desc_h3: Reserva con Seguro de Viaje Gratis para extranjeros, kilómetros ilimitados y asistencia en carretera incluida.\n\n"
                "Ejemplo 2:\n"
                "tit: Las mejores compañías de alquiler de autos en Orlando\n"
                "desc_h2: Miles Car Rental conecta tu reserva con Hertz, Enterprise, National, Alamo y otras agencias líderes en Orlando. "
                "Compara precios, categorías y coberturas en un solo lugar, con tarifas reales y sin sorpresas. "
                "15 años de experiencia respaldan cada reserva.\n"
                "desc_h3: Cada reserva incluye kilómetros ilimitados, asistencia básica en carretera y modificaciones flexibles sin cargo.\n\n"
                "Ejemplo 3:\n"
                "tit: Compañías de renta de carros en Colombia\n"
                "desc_h2: A través de Miles Car Rental accedes a las agencias de alquiler más importantes de Colombia: Avis, Hertz, Budget y más. "
                "Compara tarifas y coberturas desde un solo sitio, elige el vehículo ideal para tu ruta y reserva con total seguridad.\n"
                "desc_h3: Cobertura básica incluida, kilometraje ilimitado y atención especializada en cada punto de entrega.\n\n"
            )
            rules = (
                "REGLAS ESTRICTAS:\n"
                "- tit: H2 específico para sección de agencias. Varía entre: "
                "'Agencias de alquiler de autos en X' / 'Las mejores compañías de renta en X' / "
                "'Compañías de renta de carros en X' / 'Agencias líderes de alquiler de autos en X'.\n"
                f"- desc_h2: 50 a 65 palabras. Posiciona {brand_name} como plataforma con más de 15 años que conecta al viajero "
                "con múltiples agencias (Avis, Budget, Hertz, Alamo, Enterprise, National, etc.). "
                f"Máximo 1 mención de {brand_name} en el texto. "
                "Tono serio y confiable. Evitar exclamaciones y frases genéricas.\n"
                "- desc_h3: 20 a 35 palabras. Resalta 1 o 2 beneficios concretos del servicio. Tono profesional.\n"
            )
        else:
            examples = (
                "Ejemplos de referencia (desc_h2: propuesta de valor de Viajemos como plataforma que da acceso a las mejores agencias):\n\n"
                "Ejemplo 1:\n"
                "tit: Agencias de renta de autos en Miami\n"
                "desc_h2: En Viajemos comparas en segundos las tarifas de Avis, Budget, Hertz, Alamo y más agencias líderes. "
                "Sin comisiones ocultas, con disponibilidad en tiempo real y el respaldo de las marcas más confiables del mercado. "
                "Más opciones, mejores precios, un solo lugar para decidir.\n"
                "desc_h3: Viaja tranquilo con Seguro de Viaje Gratis para extranjeros, kilómetros ilimitados y asistencia en carretera incluida.\n\n"
                "Ejemplo 2:\n"
                "tit: Las mejores compañías de alquiler de autos en Orlando\n"
                "desc_h2: Viajemos te conecta con las agencias de alquiler más reconocidas de Orlando: Hertz, Enterprise, National y Alamo, entre otras. "
                "Compara precios, tipos de vehículo y coberturas desde un mismo sitio, elige con confianza y reserva en minutos. "
                "Tu viaje empieza con la mejor decisión.\n"
                "desc_h3: Reserva con conductor adicional sin costo extra y modificaciones flexibles para que tu itinerario siempre esté bajo control.\n\n"
                "Ejemplo 3:\n"
                "tit: Compañías de renta de carros en Colombia\n"
                "desc_h2: Con Viajemos tienes acceso directo a las agencias de alquiler más importantes del país. "
                "Compara tarifas de Avis, Hertz, Budget y más en un solo clic, sin sorpresas ni costos adicionales. "
                "Elige el vehículo ideal para tu destino y reserva con total seguridad.\n"
                "desc_h3: Disfruta de beneficios exclusivos: cobertura básica incluida, kilometraje ilimitado y atención al viajero en todo momento.\n\n"
            )
            rules = (
                "REGLAS ESTRICTAS:\n"
                "- tit: H2 específico para sección de agencias. Varía entre: "
                "'Agencias de renta de autos en X' / 'Las mejores compañías de alquiler en X' / "
                "'Compañías de renta de carros en X' / 'Agencias líderes de alquiler de autos en X'.\n"
                f"- desc_h2: 50 a 65 palabras. Posiciona {brand_name} como plataforma que conecta al viajero con múltiples agencias "
                "(Avis, Budget, Hertz, Alamo, Enterprise, National, etc.). "
                f"Máximo 1 mención de {brand_name} en el texto. "
                "Tono propuesta de valor, congruente con el tit. Evitar frases genéricas como 'te ofrecemos'.\n"
                "- desc_h3: 20 a 35 palabras. Resalta 1 o 2 beneficios concretos del servicio.\n"
            )

        prompt = (
            f"{examples}"
            f"Nuevo tema: {nuevo_tema}, contexto LP: {tit_seo}\n\n"
            f"{rules}"
            "- PROHIBIDO repetir literalmente los ejemplos.\n"
            "Genera OBLIGATORIAMENTE los tres campos:\n"
            "<think>aquí tus pensamientos</think>\n"
            "|tit: H2 para sección de agencias|\n"
            "|desc_h2: redacción|\n"
            "|desc_h3: redacción|"
        )
        raw = self._call(prompt, temperature=TEMP_CREATIVE)
        tit_default = f"Agencias de renta de autos — {nuevo_tema}"
        result = self._parse_and_supervise(raw, tit_default=tit_default)
        fields = parse_fields(result)
        if not fields.get("desc_h2"):
            if self.brand == "mcr":
                fields["desc_h2"] = (
                    f"Con {brand_name} tienes acceso a las mejores agencias de renta en {location}: "
                    "Avis, Alamo, Hertz, Budget y más. "
                    "Más de 15 años conectando viajeros con tarifas competitivas y el respaldo de marcas reconocidas. "
                    "Compara y reserva con total confianza."
                )
            else:
                fields["desc_h2"] = (
                    f"En {brand_name} comparas las tarifas de Avis, Budget, Hertz, Alamo y más agencias en {location}. "
                    "Sin comisiones ocultas, con disponibilidad en tiempo real y el respaldo de las marcas más confiables. "
                    "Más opciones, mejores precios, un solo lugar para decidir."
                )
        if not fields.get("desc_h3"):
            if self.brand == "mcr":
                fields["desc_h3"] = (
                    "Cada reserva incluye kilómetros ilimitados, Seguro de Viaje Gratis para extranjeros "
                    "y asistencia básica en carretera."
                )
            else:
                fields["desc_h3"] = (
                    "Viaja tranquilo con Seguro de Viaje Gratis para extranjeros, "
                    "kilómetros ilimitados y asistencia en carretera incluida."
                )
        return "\n".join(f"|{k}: {v}|" for k, v in fields.items())

    def generate_rentcompanies(self, tit_seo: str, nuevo_tema: str) -> str:
        """MCR rentcompanies — H2 de agencias de alquiler + descripción (80-85 palabras)."""
        brand_name = self.brand_name
        location = self._extract_location_from_title(nuevo_tema)
        if self.brand == "mcr":
            example = (
                "tit: Agencias de renta de autos en Miami, FL, "
                "desc: Con Miles Car Rental compara en segundos las tarifas de Alamo, Budget, "
                "Hertz, Dollar y más agencias líderes en Miami. "
                "Más de 15 años conectando viajeros con las mejores ofertas y el respaldo "
                "de las marcas más reconocidas del mercado."
            )
            tono = f"posicionar {brand_name} como comparador con más de 15 años; mencionar agencias aliadas (Alamo, Budget, Hertz, Dollar, etc.)"
        else:
            example = (
                "tit: Agencias de alquiler de autos en Miami, FL, "
                "desc: En Viajemos comparas en segundos tarifas de Alamo, Budget, Hertz y más. "
                "Elige la mejor agencia para tu viaje a Miami y reserva al instante "
                "con el respaldo de las marcas más confiables del mercado."
            )
            tono = f"posicionar {brand_name} como la mejor plataforma de comparación; mencionar agencias aliadas"
        prompt = (
            f"Ejemplo de referencia:\n{example}\n\n"
            f"Nuevo tema: {nuevo_tema}, contexto LP: {tit_seo}\n"
            "REGLAS:\n"
            "- tit: H2 específico para sección de agencias de renta. "
            "Ejemplos: 'Agencias de renta de autos en X' / 'Compañías de alquiler de autos en X'.\n"
            f"- desc: 80 a 85 palabras. {tono.capitalize()}.\n"
            "Genera:\n"
            "<think>aquí tus pensamientos</think>\n"
            "|tit: H2 para sección de agencias|\n"
            "|desc: redacción|"
        )
        raw = self._call(prompt, temperature=TEMP_BALANCED)
        tit_default = f"Agencias de alquiler de autos — {nuevo_tema}"
        result = self._parse_and_supervise(raw, tit_default=tit_default)
        fields = parse_fields(result)
        if not fields.get("desc"):
            if self.brand == "mcr":
                fields["desc"] = (
                    f"Con {brand_name} comparas en segundos las tarifas de Alamo, Budget, Hertz, Dollar "
                    f"y más agencias líderes en {location}. Más de 15 años conectando viajeros "
                    "con las mejores ofertas y el respaldo de las marcas más reconocidas."
                )
            else:
                fields["desc"] = (
                    f"En {brand_name} comparas en segundos las tarifas de Alamo, Budget, Hertz "
                    f"y más agencias líderes en {location}. Elige la mejor opción y reserva "
                    "al instante con el respaldo de las marcas más confiables."
                )
        return "\n".join(f"|{k}: {v}|" for k, v in fields.items())

    def generate_faq(self, tit_seo: str, nuevo_tema: str) -> str:
        """B4 — FAQs header: descripción introductoria H2 (40-60 palabras)."""
        location = self._extract_location_from_title(nuevo_tema)
        tit_default = f"Preguntas frecuentes sobre renta de autos en {location}"
        _tit_variants_faq = [
            f"Preguntas frecuentes sobre renta de autos en {location}",
            f"Todo lo que debes saber sobre el alquiler de autos en {location}",
            f"Resolvemos tus dudas sobre rentar un auto en {location}",
        ]
        import hashlib as _hs
        tit_seo_clean = _hs.md5(nuevo_tema.encode()).hexdigest()
        tit_suggested = _tit_variants_faq[int(tit_seo_clean, 16) % len(_tit_variants_faq)]
        prompt = (
            "Ejemplo de referencia:\n"
            "tit: Preguntas frecuentes sobre renta de autos en Orlando, "
            "desc: ¿Tienes dudas sobre el alquiler de autos en este destino? "
            "Aquí respondemos las preguntas más frecuentes para que llegues preparado: "
            "desde requisitos y costos hasta las mejores agencias disponibles.\n\n"
            f"Nuevo tema: {nuevo_tema}\n"
            "REGLA: genera tit + desc. El tit debe ser claro y orientado al usuario, NO incluir 'Landing Page' ni guiones. desc de 40 a 45 palabras.\n"
            f"Título sugerido para tit: {tit_suggested}\n"
            "Genera:\n"
            "<think>aquí tus pensamientos</think>\n"
            "|tit: título H2|\n"
            "|desc: redacción|"
        )
        raw = self._call(prompt, temperature=TEMP_BALANCED)
        return self._parse_and_supervise(raw, tit_default=tit_default)

    RESPUESTA_REQUISITOS_RENTA = (
        "Los requisitos generales para alquilar un auto son: "
        "** "
        "- Ser mayor de 25 años.* "
        "- Licencia de conducción de tu país de origen vigente, con antigüedad mayor a un año y fecha de vencimiento impresa. "
        "- Tarjeta de crédito a nombre del titular de la reserva con cupo disponible para cubrir el depósito de alquiler. "
        "- Depósito de Garantía. "
        "- Pasaporte vigente. "
        "- Tiquetes aéreos (ida y vuelta). "
        "** "
        "*Algunas agencias permiten que el titular de la reserva tenga entre 21 y 24 años, por un pequeño precio adicional. "
        "Es necesario que los documentos se presenten en formato físico al momento de retirar el auto de la agencia. "
        "Además, ten presente que los requisitos pueden cambiar de acuerdo con tu país de origen, "
        "te invitamos a consultar todos los detalles con nuestro Chatbot."
    )

    def _es_pregunta_requisitos_renta(self, pregunta: str) -> bool:
        p = pregunta.lower()
        return "qué se necesita para rentar" in p or "que se necesita para rentar" in p

    def generate_faq_respuesta(self, nuevo_tema: str, preguntas: List[str]) -> str:
        """B4 — FAQs respuestas individuales (estilo lm_client: template robusto)."""
        if not preguntas:
            preguntas = self.generate_faq_questions_from_title(nuevo_tema)

        location = self._extract_location_from_title(nuevo_tema)
        precio_dia = "9"
        precio_semana = "63"

        agencias_precios = [
            ("Alamo", precio_dia),
            ("Dollar", str(int(precio_dia) + 1)),
            ("Avis", str(int(precio_dia) + 2)),
        ]
        agencias_lines = "\n".join(f"- {ag}, desde USD ${pr}/día" for ag, pr in agencias_precios)

        import hashlib as _hfaq
        faq_responses = {}
        for i, pregunta in enumerate(preguntas, start=1):
            p = (pregunta or "").lower()
            _seed = int(_hfaq.md5(f"{nuevo_tema}|{pregunta}|{i}".encode()).hexdigest(), 16)

            if self._es_pregunta_requisitos_renta(pregunta):
                faq_responses[f"faq_{i}"] = self.RESPUESTA_REQUISITOS_RENTA
                continue

            if "semana" in p:
                _semana_templates = [
                    (
                        f"Alquilar un carro durante una semana en {location} tiene un costo "
                        f"desde los USD ${precio_semana}.\n\n"
                        "Recuerda que este precio puede cambiar según la temporada, la "
                        "agencia elegida, el tipo de vehículo y los servicios adicionales "
                        "incluidos en la reserva."
                    ),
                    (
                        f"Para una renta semanal en {location}, las tarifas suelen iniciar "
                        f"desde USD ${precio_semana}.\n\n"
                        "El valor final depende de la fecha del viaje, la categoría del auto, "
                        "la disponibilidad y las coberturas que agregues a la reserva."
                    ),
                    (
                        f"Si planeas rentar por siete días en {location}, puedes encontrar "
                        f"opciones desde USD ${precio_semana}.\n\n"
                        "Ese monto puede variar por temporada, políticas de la agencia, tipo "
                        "de carro seleccionado y servicios adicionales contratados."
                    ),
                ]
                faq_responses[f"faq_{i}"] = _semana_templates[_seed % len(_semana_templates)]
                continue

            if "agencia" in p or "barat" in p:
                _agencia_templates = [
                    (
                        f"Las compañías de renta de vehículos con las tarifas más económicas "
                        f"en {location} son:\n"
                        "**\n"
                        f"{agencias_lines}\n"
                        "**\n"
                        "En nuestro portal puedes comparar los precios de estas y otras "
                        "agencias para elegir la opción que mejor se ajuste a tu viaje. "
                        "No olvides que el precio puede cambiar según temporada, categoría del auto "
                        "y servicios adicionales."
                    ),
                    (
                        f"Entre las alternativas con mejor precio en {location} se encuentran:\n"
                        "**\n"
                        f"{agencias_lines}\n"
                        "**\n"
                        "Te recomendamos comparar condiciones, horarios de retiro y coberturas, "
                        "porque las tarifas pueden variar de acuerdo con la temporada y la "
                        "categoría elegida."
                    ),
                    (
                        f"Si buscas opciones económicas de alquiler en {location}, revisa primero:\n"
                        "**\n"
                        f"{agencias_lines}\n"
                        "**\n"
                        "La mejor decisión sale de comparar precio total, tipo de auto y servicios "
                        "incluidos antes de confirmar la reserva."
                    ),
                ]
                faq_responses[f"faq_{i}"] = _agencia_templates[_seed % len(_agencia_templates)]
                continue

            if "zona" in p or "recoger" in p:
                _zona_templates = [
                    (
                        f"En {location}, suele convenir recoger el auto en el aeropuerto o en zonas "
                        "centrales con mayor disponibilidad. La mejor opción depende de tu itinerario, "
                        "horario de llegada y presupuesto. Compara ubicación, tarifa y condiciones "
                        "antes de confirmar la reserva."
                    ),
                    (
                        f"Para {location}, los puntos de retiro más prácticos suelen ser el aeropuerto "
                        "y áreas céntricas. El lugar ideal cambia según tu ruta, hora de llegada y "
                        "costos asociados. Revisa distancia, tarifa y políticas antes de reservar."
                    ),
                    (
                        f"La mejor zona para recoger el carro en {location} depende de dónde iniciarás "
                        "tu recorrido. Aeropuerto y centro suelen ofrecer más disponibilidad, pero conviene "
                        "comparar precio final, tiempos de traslado y condiciones de entrega."
                    ),
                ]
                faq_responses[f"faq_{i}"] = _zona_templates[_seed % len(_zona_templates)]
                continue

            if "anticipaci" in p or "reserva" in p:
                _anticipacion_templates = [
                    (
                        "Sí, reservar con anticipación suele ayudarte a conseguir mejores tarifas y "
                        "más categorías disponibles. En temporadas altas, la diferencia de precio puede "
                        "ser mayor, por eso recomendamos comparar opciones y confirmar tu reserva cuanto antes."
                    ),
                    (
                        "Reservar con tiempo casi siempre mejora tu margen de elección y precio. "
                        "Cuando hay alta demanda, las categorías más buscadas se agotan rápido, "
                        "así que comparar y confirmar antes suele ser una mejor estrategia."
                    ),
                    (
                        "Sí conviene reservar anticipadamente, sobre todo si viajas en fechas de alta "
                        "ocupación. Así puedes acceder a más disponibilidad, revisar condiciones con calma "
                        "y asegurar una tarifa más competitiva."
                    ),
                ]
                faq_responses[f"faq_{i}"] = _anticipacion_templates[_seed % len(_anticipacion_templates)]
                continue

            # Default: costo diario
            _diario_templates = [
                (
                    f"Alquilar un auto en {location} tiene un costo que va desde los "
                    f"USD ${precio_dia} al día, a través de {self.brand_name}.\n\n"
                    "Ten en cuenta que la tarifa puede variar según la categoría del vehículo, "
                    "la agencia de alquiler, la temporada y los servicios adicionales de la reserva."
                ),
                (
                    f"En {location}, el precio diario de renta puede comenzar desde USD ${precio_dia}.\n\n"
                    "El total final depende de la categoría elegida, la fecha de viaje, la agencia "
                    "seleccionada y las coberturas añadidas en la reserva."
                ),
                (
                    f"Puedes encontrar alquiler de autos en {location} desde USD ${precio_dia} por día.\n\n"
                    "Para una referencia más precisa, conviene comparar según temporada, tipo de carro "
                    "y condiciones incluidas en cada opción disponible."
                ),
            ]
            faq_responses[f"faq_{i}"] = _diario_templates[_seed % len(_diario_templates)]

        return "\n".join(f"|{k}: {v}|" for k, v in faq_responses.items())

    _CAR_RENTAL_TITULOS = [
        "Elige el auto ideal para tu alquiler en {loc}",
        "Categorías de autos para rentar en {loc}",
        "Encuentra tu vehículo en renta para {loc}",
        "Tipos de autos en alquiler para recorrer {loc}",
        "El auto correcto para rentar en {loc}",
        "Opciones de vehículos en alquiler para tu estancia en {loc}",
    ]

    def generate_car_rental(self, tit_seo: str, nuevo_tema: str) -> str:
        """B5 — Car Rental header: descripción introductoria (60-85 palabras)."""
        location = self._extract_location_from_title(nuevo_tema)
        idx = sum(ord(c) for c in location) % len(self._CAR_RENTAL_TITULOS)
        tit_sugerido = self._CAR_RENTAL_TITULOS[idx].format(loc=location)

        if self.brand == "mcr":
            example = ""
            tone_rule = (
                "Tono profesional y confiable. Sin exclamaciones ni lenguaje informal. "
                "PROHIBIDO: referencias a la empresa, años de experiencia o premios."
            )
            desc_rule = (
                "- desc: 80 a 85 palabras. Es una introducción breve a la sección de vehículos. "
                "NO menciones tipos de autos, NO los enumeres, NO los describas. "
                "Solo contextualiza al usuario sobre la variedad disponible en el destino "
                "e invítalo a explorar. PROHIBIDO: mencionar precios, marcas o llamados a reservar.\n"
            )
        else:
            example = (
                "Ejemplo de referencia:\n"
                "tit: Elige el auto ideal para tu viaje por Miami, "
                "desc: En Miami hay categorías para todos: autos compactos para moverse rápido, "
                "SUVs para la familia, vans para grupos y opciones de lujo para quienes quieren "
                "más confort. Mira las opciones disponibles y escoge la que mejor se adapte "
                "a tu itinerario y presupuesto.\n\n"
            )
            tone_rule = (
                "Tono cercano y dinámico, propio de Viajemos. Puede ser directo y entusiasta."
            )
            desc_rule = (
                "- desc: 80 a 85 palabras. Es una introducción a la sección de autos. "
                "NO definas ni describas categorías específicas aquí, NO enumere tipos de autos. "
                "Debe preparar al usuario para explorar las opciones en los bloques siguientes. "
                "PROHIBIDO: mencionar precios, marcas o llamados directos a reservar.\n"
            )

        prompt = (
            f"{example}"
            f"Destino: {location}\n"
            "REGLAS:\n"
            f"- Tono: {tone_rule}\n"
            "- tit: título H2 concreto. OBLIGATORIO incluir 'alquila' o 'renta' de forma orgánica y creativa. Máximo 10 palabras.\n"
            f"{desc_rule}"
            "Genera:\n"
            "<think>aquí tus pensamientos</think>\n"
            f"|tit: {tit_sugerido}|\n"
            "|desc: redacción|\n"
            "IMPORTANTE: Solo usa | al inicio y final, NUNCA dentro del contenido."
        )
        raw = self._call(prompt, temperature=TEMP_CREATIVE)
        return self._parse_and_supervise(raw, tit_default=tit_sugerido)

    def generate_car_type(self, titulos_autos: List[str], nuevo_tema: str) -> str:
        """B5 — Car Rental descripciones individuales por tipo de auto (15-20 palabras c/u)."""
        if not titulos_autos:
            titulos_autos = [
                "Auto Económico", "Auto Compacto", "Auto Intermedio",
                "SUV", "Van", "Auto de Lujo",
            ]

        location = self._extract_location_from_title(nuevo_tema)
        if self.brand in ("vjm", "viajemos"):
            rango = "19 a 29 palabras"
        else:
            rango = "15 a 20 palabras"

        titulos_texto = "\n".join(
            [f"Tipo {i+1}: {t}" for i, t in enumerate(titulos_autos)]
        )
        pipe_example = "\n".join(
            [f"|tit_{i+1}: {t}|\n|desc_{i+1}: descripción de {rango}|"
             for i, t in enumerate(titulos_autos)]
        )

        exclamaciones = (
            "- PROHIBIDO usar exclamaciones.\n"
            if self.brand == "mcr" else ""
        )

        _opening_bank = [
            "Para viajes cortos por la ciudad,",
            "Cuando necesitas moverte sin complicaciones,",
            "Si el plan incluye varias paradas,",
            "Para recorridos donde el tiempo importa,",
            "Cuando priorizas espacio y comodidad,",
            "Si viajas en grupo o con equipaje extra,",
            "Para quienes buscan conducir con estilo,",
            "Cuando el destino exige versatilidad,",
            "Si tu ruta mezcla ciudad y carretera,",
            "Para aprovechar al máximo cada kilómetro,",
        ]
        openings_ejemplo = " / ".join(_opening_bank[:6])

        prompt = (
            f"Destino: {location}\n"
            f"Genera una descripción ({rango}) para cada tipo de auto. "
            "Cada descripción debe sonar completamente diferente a las demás.\n\n"
            "REGLAS OBLIGATORIAS:\n"
            f"- Entre {rango} exactas. La oración debe terminar con sentido completo.\n"
            "- PROHIBIDO ESTRICTO: que dos descripciones empiecen con la misma palabra o frase. "
            "Cada apertura debe ser estructuralmente diferente (condicional, imperativo, pregunta, afirmación, etc.).\n"
            "- PROHIBIDO: repetir cierres o remates entre descripciones.\n"
            "- Menciona el destino dentro de la descripción de forma natural.\n"
            "- La descripción habla de algo concreto y exclusivo de ese tipo de auto, no intercambiable con otro.\n"
            "- El nombre del tipo integrado en medio de la oración, NUNCA como primera palabra.\n"
            "- PROHIBIDO frases que suenen a plantilla (ej: 'y aprovechar mejor cada tramo' repetido).\n"
            "- PROHIBIDO mencionar marcas o comparadores.\n"
            f"{exclamaciones}"
            f"Ejemplos de aperturas variadas (úsalas como inspiración, no literalmente): {openings_ejemplo}\n\n"
            f"{titulos_texto}\n\n"
            "Genera:\n"
            "<think>aquí tus pensamientos</think>\n"
            f"{pipe_example}\n"
            "IMPORTANTE: Solo usa | al inicio y final de cada campo, NUNCA dentro del contenido."
        )
        raw = self._call(prompt, temperature=TEMP_CREATIVE)
        parsed = parse_fields(raw)
        out = {}

        # Fallbacks con apertura y cierre únicos por posición (round-robin garantizado)
        _fallback_openings = [
            "Para viajes cortos por la ciudad,",
            "Cuando necesitas moverte sin restricciones,",
            "Si el plan incluye varias paradas,",
            "Para recorridos donde el tiempo importa,",
            "Cuando priorizas espacio y comodidad,",
            "Si viajas en grupo o con equipaje extra,",
            "Para quienes buscan conducir con estilo,",
            "Cuando el destino exige versatilidad,",
            "Si tu ruta combina ciudad y carretera,",
            "Para aprovechar cada kilómetro al máximo,",
        ]
        _fallback_closings = [
            "con un ritmo de viaje más eficiente.",
            "y mayor control sobre tus tiempos.",
            "sin sacrificar comodidad en el camino.",
            "sacando el máximo partido a cada tramo.",
            "con la flexibilidad que tu itinerario necesita.",
            "y una experiencia de conducción equilibrada.",
            "adaptándose a cualquier plan del viaje.",
            "con más tranquilidad desde el primer día.",
            "sin preocuparte por el espacio disponible.",
            "y un nivel de confort acorde a tu ruta.",
        ]

        def _mid_for_tipo(tipo: str, city: str) -> str:
            t = (tipo or "").lower()
            if "econ" in t:
                return f"un {tipo} recorre {city} con consumo eficiente"
            if "compact" in t:
                return f"un {tipo} circula por {city} y estaciona con facilidad"
            if "intermedio" in t:
                return f"un {tipo} ofrece equilibrio entre espacio y maniobrabilidad en {city}"
            if "suv" in t:
                return f"un {tipo} da altura y amplitud para trayectos variados en {city}"
            if "van" in t:
                return f"una {tipo} organiza mejor pasajeros y equipaje en rutas por {city}"
            if "lujo" in t:
                return f"un {tipo} eleva la experiencia de conducción en {city}"
            if "eléctric" in t or "electric" in t:
                return f"un {tipo} recorre {city} de forma silenciosa y sostenible"
            return f"un {tipo} se adapta a distintos recorridos dentro de {city}"

        used_openings: set = set()
        used_closings: set = set()
        fallback_open_idx = 0
        fallback_close_idx = 0

        def _pick_unique_opening() -> str:
            nonlocal fallback_open_idx
            while fallback_open_idx < len(_fallback_openings):
                candidate = _fallback_openings[fallback_open_idx]
                fallback_open_idx += 1
                key = candidate.split()[0].lower()
                if key not in used_openings:
                    used_openings.add(key)
                    return candidate
            # Si se agotaron, devuelve el siguiente en ciclo
            candidate = _fallback_openings[fallback_open_idx % len(_fallback_openings)]
            fallback_open_idx += 1
            return candidate

        def _pick_unique_closing() -> str:
            nonlocal fallback_close_idx
            while fallback_close_idx < len(_fallback_closings):
                candidate = _fallback_closings[fallback_close_idx]
                fallback_close_idx += 1
                key = " ".join(candidate.split()[:3]).lower()
                if key not in used_closings:
                    used_closings.add(key)
                    return candidate
            candidate = _fallback_closings[fallback_close_idx % len(_fallback_closings)]
            fallback_close_idx += 1
            return candidate

        for i, tipo in enumerate(titulos_autos, start=1):
            tit_k = f"tit_{i}"
            desc_k = f"desc_{i}"
            out[tit_k] = tipo
            desc_v = (parsed.get(desc_k) or "").strip()

            # Detectar apertura repetida en resultado del LLM
            if desc_v:
                first_word = desc_v.split()[0].lower() if desc_v.split() else ""
                if first_word in used_openings:
                    desc_v = ""  # forzar fallback para esta entrada
                else:
                    used_openings.add(first_word)

            if not desc_v:
                op = _pick_unique_opening()
                cl = _pick_unique_closing()
                mid = _mid_for_tipo(tipo, location)
                desc_v = re.sub(r"\s+", " ", f"{op} {mid}, {cl}").strip()

            out[desc_k] = desc_v
        return "\n".join(f"|{k}: {v}|" for k, v in out.items())

    def generate_fav_city(self, tit_seo: str, nuevo_tema: str) -> str:
        """B6 — Favorite Cities/Locations header: título + descripción (55-65 palabras)."""
        brand_name = self.brand_name
        location = self._extract_location_from_title(nuevo_tema)

        if self.brand == "mcr":
            examples = (
                "Ejemplos de referencia:\n"
                f"Ejemplo 1: tit: Ciudades populares para rentar un auto en EE. UU., "
                "desc: Recorre los principales destinos de Estados Unidos al volante de un auto rentado. "
                "Compara tarifas en tu ciudad de destino y reserva con Miles Car Rental. "
                "Cada ciudad tiene sus rutas y atracciones: elige la mejor opción para tu viaje.\n"
                f"Ejemplo 2: tit: Las mejores ciudades para alquilar un auto cerca de Miami, "
                "desc: Desde Miami puedes llegar a docenas de destinos en pocas horas. "
                "Renta un auto con Miles Car Rental y explora ciudades cercanas, playas y parques "
                "nacionales con total libertad y al mejor precio del mercado.\n\n"
            )
        else:
            examples = (
                "Ejemplos de referencia:\n"
                "Ejemplo 1: tit: Destinos populares para rentar un auto, "
                "desc: Recorre los destinos más visitados de Estados Unidos al volante. "
                "Con Viajemos compara tarifas entre las mejores agencias y reserva tu auto ideal "
                "para explorar cada ciudad con libertad total.\n"
                "Ejemplo 2: tit: Renta un auto y descubre nuevas ciudades, "
                "desc: Cada destino tiene su encanto y sus rutas imperdibles. "
                "Con Viajemos encuentras la mejor tarifa de alquiler para moverte con comodidad, "
                "sin depender de horarios ni transporte público.\n\n"
            )

        _tit_variants = [
            f"Ciudades populares para rentar un auto cerca de {location}",
            f"Destinos imperdibles para alquilar un auto desde {location}",
            f"Las mejores ciudades para renta de autos en la zona de {location}",
        ]
        import hashlib
        idx = int(hashlib.md5(nuevo_tema.encode()).hexdigest(), 16) % len(_tit_variants)
        tit_default = _tit_variants[idx]
        desc_default = (
            f"Explora los destinos más populares con un auto rentado a través de {brand_name}. "
            "Compara tarifas entre agencias reconocidas y elige la opción ideal "
            "para viajar con libertad, comodidad y al mejor precio."
        )

        prompt = (
            f"{examples}"
            f"Nuevo tema: {nuevo_tema}, contexto LP: {tit_seo}\n"
            "REGLAS:\n"
            "- tit: H2 específico para esta LP. OBLIGATORIO mencionar el destino o zona. "
            "NO usar 'Destinos populares' genérico. Varía: 'Ciudades para rentar un auto cerca de X' / "
            "'Destinos imperdibles para alquilar un auto desde X' / 'Mejores ciudades para renta de autos en X'.\n"
            f"- desc: {'75 a 80' if self.brand == 'mcr' else '55 a 60'} palabras. Enfatiza libertad de movimiento y variedad de destinos.{' Máximo 1 mención de la marca.' if self.brand == 'mcr' else ' Menciona la marca.'}\n"
            "Genera:\n"
            "<think>aquí tus pensamientos</think>\n"
            "|tit: título específico para esta LP|\n"
            "|desc: redacción|"
        )
        raw = self._call(prompt, temperature=TEMP_CREATIVE)
        fields = parse_fields(raw)

        # Normaliza aliases frecuentes para garantizar salida H2 + descripción.
        tit = (
            (fields.get("tit") or "").strip()
            or (fields.get("h2") or "").strip()
            or (fields.get("titulo") or "").strip()
            or tit_default
        )
        desc = (
            (fields.get("desc") or "").strip()
            or (fields.get("h2_desc") or "").strip()
            or (fields.get("descripcion") or "").strip()
            or desc_default
        )

        safe = f"|tit: {tit}|\n|desc: {desc}|"
        return self._parse_and_supervise(safe, tit_default=tit_default)

    def generate_fav_city_respuesta(self, nuevo_tema: str, ciudades: List[str]) -> str:
        """B6 — Favorite Cities descripciones individuales por ciudad (25-30 palabras c/u)."""
        # Normalizar ciudades y fallback defensivo
        incoming = [c.strip() for c in (ciudades or []) if c and c.strip()]
        if not incoming:
            incoming = [c[0] for c in _FAV_CITY_DEFAULTS[:10]]

        # Limpiar prefijos de keyword que a veces vienen en la lista de ciudades
        _city_prefixes = re.compile(
            r"(?i)^(alquiler de autos en|renta de autos en|renta de carros en|"
            r"alquiler de carros en|rentar un auto en|reservar un auto en)\s*"
        )

        # Evitar duplicados manteniendo orden
        normalized = []
        seen = set()
        for c in incoming:
            c = _city_prefixes.sub("", c).strip()
            c = self.sanitize_city_name(c)
            if not c:
                continue
            ck = c.lower()
            if ck in seen:
                continue
            seen.add(ck)
            normalized.append(c)

        # No autocompletar con ciudades por defecto cuando el usuario ya provee lista.
        # Si la lista llega corta, se respeta tal cual para evitar "inventar" localidades.

        ciudades_texto = "\n".join([f"Ciudad {i+1}: {c}" for i, c in enumerate(normalized)])
        _tit_examples = [
            "{city}",
            "{city}",
            "{city}",
            "{city}",
            "{city}",
        ]
        expected_pipe = "\n".join([
            f"|tit_{i+1}: {_tit_examples[i % len(_tit_examples)].format(city=c)}|\n|desc_{i+1}: texto de 25 a 30 palabras sobre rentar en {c}|"
            for i, c in enumerate(normalized)
        ])
        _openings = [
            "Si piensas moverte sin depender de horarios,",
            "Para aprovechar mejor cada tramo del viaje,",
            "Cuando el plan incluye varias paradas,",
            "Si quieres recorrer mas en menos tiempo,",
            "Para combinar ciudad y alrededores,",
            "Si buscas un viaje mas flexible,",
            "Con un itinerario activo durante el dia,",
            "Para un recorrido comodo de principio a fin,",
        ]
        openings_ref = " / ".join(_openings)
        n_cities = len(normalized)
        prompt = (
            f"Tema: {nuevo_tema}\n"
            f"Genera TITULO y DESCRIPCION para las {n_cities} ciudades en formato pipe exacto. DEBES generar los {n_cities} bloques completos.\n"
            "Regla de TITULO (obligatoria): cada tit_i debe ser SOLO el nombre de la ciudad/localidad, sin prefijos comerciales.\n"
            "Cada desc: EXACTAMENTE 25 a 30 palabras. Tono comercial. Ciudad mencionada una sola vez.\n\n"
            "VARIEDAD DE ESTRUCTURA (obligatoria):\n"
            "- PROHIBIDO que 2 o más descripciones empiecen con la misma palabra.\n"
            "- PROHIBIDO iniciar con 'Alquila un auto en', 'Renta un auto en', "
            "'Alquiler de autos en', 'Descubre' o 'Descubrir'.\n"
            "- Alterna aperturas estructuralmente diferentes. "
            f"Referencia (adapta al destino): {openings_ref}\n\n"
            "VARIACIÓN DE KEYWORDS (obligatoria en el conjunto):\n"
            "- Servicio: alterna 'alquiler de autos', 'renta de carros', 'rentar un auto', "
            "'reservar un carro', 'renta de autos'. Máximo 2 descripciones seguidas con el mismo término.\n"
            "- Vehículo: usa 'auto/autos' la mayoría; 'carro/carros' como variante frecuente; "
            "'vehículo' máximo 1 vez en todo el conjunto.\n"
            "- Títulos: NO usar frases como 'Alquiler de autos en...'; solo ciudad/localidad.\n\n"
            f"{ciudades_texto}\n\n"
            "Salida OBLIGATORIA (sin texto extra):\n"
            f"{expected_pipe}"
        )

        parsed = {}
        try:
            raw = self._call(prompt, temperature=TEMP_CREATIVE)
            parsed = parse_fields(raw) or {}
        except Exception as e:
            log.warning("Favorite Cities: fallo llamada LLM, usando fallback. Error: %s", e)

        # Completar siempre tit_i y desc_i con fallback deterministico
        defaults_map = {name.lower(): (title, desc) for name, title, desc in _FAV_CITY_DEFAULTS}

        # Variantes de keyword para fallback — rotación por índice garantiza variedad
        _fallback_tit_templates = [
            "{city}",
            "{city}",
            "{city}",
            "{city}",
            "{city}",
            "{city}",
            "{city}",
            "{city}",
        ]
        _fallback_desc_templates = [
            "Compara opciones y reserva tu alquiler de autos en {city}. Disfruta libertad de movimiento, mejores tarifas y una experiencia de viaje mas flexible y comoda.",
            "Encuentra la mejor tarifa para renta de carros en {city}. Viaja a tu ritmo, sin depender de horarios y con acceso a multiples destinos.",
            "Rentar un auto en {city} te da la flexibilidad para explorar cada rincon sin restricciones. Elige el vehiculo ideal y reserva en minutos.",
            "Reservar un carro en {city} es facil y rapido. Compara precios entre agencias reconocidas y disfruta tu viaje con total comodidad.",
            "Con renta de autos en {city} puedes recorrer atracciones locales, playas y rutas panoramicas sin depender de transporte publico.",
            "El alquiler de carros en {city} te permite organizar tu itinerario con autonomia total. Tarifas competitivas y amplia disponibilidad.",
            "Rentar un carro en {city} es la opcion mas flexible para viajeros activos. Reserva con anticipacion y obtiene las mejores tarifas.",
            "Reservar un auto en {city} te asegura movilidad total desde el primer dia. Compara agencias y elige la opcion que mejor se ajusta a tu viaje.",
        ]

        out = {}
        for i, city in enumerate(normalized, start=1):
            tit_k = f"tit_{i}"
            desc_k = f"desc_{i}"

            idx = (i - 1) % len(_fallback_tit_templates)
            fallback_tit = _fallback_tit_templates[idx].format(city=city)
            fallback_desc = _fallback_desc_templates[idx].format(city=city)

            default_title, default_desc = defaults_map.get(city.lower(), (fallback_tit, fallback_desc))

            tit_v = (parsed.get(tit_k) or "").strip()
            desc_v = (parsed.get(desc_k) or "").strip()

            if not tit_v:
                tit_v = default_title
            if not desc_v or len(desc_v.split()) < 12:
                desc_v = default_desc

            out[tit_k] = tit_v
            out[desc_k] = desc_v

        return "\n".join(f"|{k}: {v}|" for k, v in out.items())

    def generate_rentacar(self, tit_seo: str, nuevo_tema: str) -> str:
        """Rentacar — mini-blogs: H2 intro + 2 H3 (actividades y agencias/autos)."""
        location = self._extract_location_from_title(nuevo_tema)
        tit_default = f"Qué hacer en {location} con un auto rentado"

        # ── Llamada 1: tit + desc (H2 intro, 70-90 palabras) ──
        p1 = (
            f"Destino: {location}\n"
            f"Tema: {nuevo_tema}, contexto: {tit_seo}\n"
            "Eres un redactor de guías de viaje. Escribe contenido informativo y turístico.\n"
            "REGLAS:\n"
            "- tit: H2 específico sobre actividades en el destino con auto rentado. "
            "Ejemplos: 'Qué hacer en Miami con un auto rentado' / "
            "'Los mejores planes en Los Ángeles con un carro de alquiler'.\n"
            "- desc: 70 a 90 palabras. Introducción sobre lo que permite explorar un auto rentado "
            "en el destino. Menciona brevemente tipos de autos y agencias disponibles.\n"
            "- Tono profesional. PROHIBIDO usar exclamaciones.\n"
            "Genera:\n"
            "<think>aquí tus pensamientos</think>\n"
            "|tit: H2 mini-blog|\n"
            "|desc: redacción|\n"
            "IMPORTANTE: Solo usa | al inicio y final, NUNCA dentro del contenido."
        )
        raw1 = self._call(p1, temperature=TEMP_CREATIVE)
        fields = parse_fields(raw1)
        if not fields.get("tit"):
            fields["tit"] = tit_default
        if not fields.get("desc"):
            clean = re.sub(r"<think>.*?</think>", "", raw1, flags=re.DOTALL)
            clean = re.sub(r"\|[^|]+:", "", clean).replace("|", "").strip()
            if clean:
                fields["desc"] = clean

        # ── Llamada 2: tit_1 + desc_1 (mini-blog #1: actividades y rutas) ──
        p2 = (
            f"Destino: {location}\n"
            "Redacta un mini-blog de 220 a 250 palabras sobre qué hacer y visitar en este destino "
            "con un auto rentado. Incluye: principales atracciones, rutas recomendadas, "
            "zonas de interés y consejos prácticos de movilidad. Menciona los tipos de autos "
            "más adecuados para estas actividades (ej: SUV para excursiones, autos compactos "
            "para el centro, vans para grupos). Tono informativo y turístico. "
            "PROHIBIDO usar exclamaciones.\n"
            "Para listas usa ** arriba y abajo, - por ítem.\n"
            "Genera:\n"
            "<think>aquí tus pensamientos</think>\n"
            "|tit_1: título H3 específico sobre actividades en el destino|\n"
            "|desc_1: redacción de 220 a 250 palabras|\n"
            "IMPORTANTE: Solo usa | al inicio y final, NUNCA dentro del contenido."
        )
        raw2 = self._call(p2, temperature=TEMP_CREATIVE)
        fields2 = parse_fields(raw2)
        tit_1 = fields2.get("tit_1", "").strip()
        desc_1 = fields2.get("desc_1", "").strip()
        if not tit_1:
            tit_1 = f"Actividades recomendadas en {location} con auto rentado"
        if not desc_1:
            clean = re.sub(r"<think>.*?</think>", "", raw2, flags=re.DOTALL)
            clean = re.sub(r"\|[^|]+:", "", clean).replace("|", "").strip()
            desc_1 = clean
        fields["tit_1"] = tit_1
        fields["desc_1"] = desc_1

        # ── Llamada 3: tit_2 + desc_2 (mini-blog #2: agencias y tipos de autos) ──
        p3 = (
            f"Destino: {location}\n"
            "Redacta un mini-blog de 220 a 250 palabras sobre las principales agencias de renta "
            "de autos disponibles en este destino y los tipos de vehículos que ofrecen. "
            "Menciona agencias reconocidas como Avis, Budget, Hertz, Enterprise, National, "
            "Alamo, Dollar o Thrifty. Explica las categorías de autos disponibles y cómo elegir "
            "según el tipo de viaje (familia, negocios, aventura, etc.). "
            "Tono informativo con enfoque práctico. PROHIBIDO usar exclamaciones.\n"
            "Para listas usa ** arriba y abajo, - por ítem.\n"
            "Genera:\n"
            "<think>aquí tus pensamientos</think>\n"
            "|tit_2: título H3 específico sobre agencias y autos en el destino|\n"
            "|desc_2: redacción de 220 a 250 palabras|\n"
            "IMPORTANTE: Solo usa | al inicio y final, NUNCA dentro del contenido."
        )
        raw3 = self._call(p3, temperature=TEMP_CREATIVE)
        fields3 = parse_fields(raw3)
        tit_2 = fields3.get("tit_2", "").strip()
        desc_2 = fields3.get("desc_2", "").strip()
        if not tit_2:
            tit_2 = f"Agencias de renta de autos en {location}"
        if not desc_2:
            clean = re.sub(r"<think>.*?</think>", "", raw3, flags=re.DOTALL)
            clean = re.sub(r"\|[^|]+:", "", clean).replace("|", "").strip()
            desc_2 = clean
        fields["tit_2"] = tit_2
        fields["desc_2"] = desc_2

        return "\n".join(f"|{k}: {v}|" for k, v in fields.items() if v)

    def generate_advicestipocarrusel(self, titulo_limpio: str, nuevo_tema: str) -> str:
        """Consejos — H2 propio + desc introductoria."""
        prompt = (
            f"Nuevo tema: {nuevo_tema}, contexto LP: {titulo_limpio}\n"
            "Genera una introducción corta para una sección de consejos de viaje.\n"
            "REGLAS:\n"
            "- tit: H2 específico para sección de consejos. "
            "Ejemplos: 'Consejos para rentar un auto en Miami' / "
            "'Tips para alquilar un carro en Colombia'.\n"
            "- desc: 60 a 65 palabras.\n"
            "Genera:\n"
            "<think>aquí tus pensamientos</think>\n"
            "|tit: H2 para sección de consejos|\n"
            "|desc: redacción|"
        )
        raw = self._call(prompt, temperature=TEMP_BALANCED)
        tit_default = f"Consejos para rentar un auto — {nuevo_tema}"
        return self._parse_and_supervise(raw, tit_default=tit_default)

    def generate_faq_questions_from_title(self, titulo: str) -> List[str]:
        """
        Genera las preguntas FAQ estándar a partir del título del LP.
        Patrón fijo sin LLM — igual al enfoque del Cargue Masivo.
        """
        t = self._extract_location_from_title(titulo)
        return [
            f"¿Cuánto cuesta rentar un auto en {t}?",
            f"¿Qué se necesita para rentar un auto en {t}?",
            f"¿Cuál es la agencia de alquiler de autos con los precios más baratos en {t}?",
            f"¿Cuánto cuesta rentar un carro por una semana en {t}?",
            f"¿Cuál es la mejor zona para recoger un auto de alquiler en {t}?",
            f"¿Conviene reservar con anticipación el alquiler de autos en {t}?",
        ]

    def _extract_location_from_title(self, titulo: str) -> str:
        """Extrae ubicación legible desde títulos SEO ruidosos.

        Ejemplo: 'Landing Page - Dollar Orlando' -> 'Orlando'
        """
        if not titulo:
            return "el destino"

        t = re.sub(r"<[^>]+>", " ", titulo)
        t = re.sub(r"\s+", " ", t).strip()

        # 1) Intentar detectar ciudades conocidas primero (multi-word primero)
        known = sorted([c[0] for c in _FAV_CITY_DEFAULTS], key=len, reverse=True)
        for city in known:
            if re.search(rf"\b{re.escape(city)}\b", t, flags=re.IGNORECASE):
                return city

        # 2) Limpiar prefijos comunes
        cleaned = t
        cleaned = re.sub(r"(?i)^landing\s*page\s*[-:]*\s*", "", cleaned)
        cleaned = re.sub(r"(?i)alquiler\s+de\s+autos\s+en\s+", "", cleaned)
        cleaned = re.sub(r"(?i)renta\s+de\s+autos\s+en\s+", "", cleaned)
        cleaned = re.sub(r"(?i)agencias\s+de\s+renta\s+de\s+autos\s+en\s+", "", cleaned)
        cleaned = re.sub(r"\s+[-–|]\s+", " ", cleaned).strip()

        # 3) Última palabra(s) con inicial mayúscula
        tokens = [tok for tok in cleaned.split() if tok]
        if not tokens:
            return "el destino"

        # Si termina en dos palabras capitalizadas (ej: New York), conservar ambas
        if len(tokens) >= 2 and tokens[-1][:1].isupper() and tokens[-2][:1].isupper():
            return f"{tokens[-2]} {tokens[-1]}"
        return tokens[-1]

    def generate_fav_cities_from_title(self, titulo: str) -> List[str]:
        """
        Genera la lista de ciudades/destinos populares para el contexto del LP vía LLM.
        Se usa cuando el frontend no aporta ciudades (LP nuevo sin template content).
        """
        prompt = (
            f"Título de landing page: '{titulo}'\n"
            "Lista los 10 destinos o ciudades más visitados para rentar un auto "
            "en el contexto de este título.\n"
            "Responde SOLO con los nombres separados por comas, sin numeración "
            "ni explicaciones adicionales.\n"
            "Ejemplo: Miami, Orlando, Nueva York, Las Vegas, Los Ángeles, "
            "Chicago, Houston, San Francisco, Dallas, Atlanta"
        )
        raw = self._call(prompt, temperature=TEMP_PRECISE)
        raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

        # Intento 1: separado por comas
        cities = [c.strip() for c in raw.split(",") if c.strip() and len(c.strip()) > 1]

        # Intento 2: lineas (cuando responde en lista)
        if len(cities) < 3:
            line_candidates = []
            for line in raw.splitlines():
                cleaned = re.sub(r"^[-*\d\.)\s]+", "", line).strip()
                if cleaned and len(cleaned) > 1:
                    line_candidates.append(cleaned)
            if len(line_candidates) >= len(cities):
                cities = line_candidates

        # Limpieza final de ruido comun
        cleaned_out = []
        for city in cities:
            c = re.sub(r"\s+", " ", city).strip(" .;:-")
            if c and len(c) > 1 and c.lower() not in {"ciudades", "destinos"}:
                cleaned_out.append(c)

        if not cleaned_out:
            cleaned_out = [c[0] for c in _FAV_CITY_DEFAULTS]

        return cleaned_out[:17]

    def generate_advice_type(self, advice_types: List[str], nuevo_tema: str) -> str:
        """Consejos — descripciones individuales por tipo de consejo."""
        consejos_texto = "\n".join(
            [f"Consejo {i+1}: {c}" for i, c in enumerate(advice_types)]
        )
        prompt = (
            f"Tema: {nuevo_tema}\n"
            f"Genera una descripción (30 a 80 palabras) para cada consejo de viaje.\n\n"
            f"{consejos_texto}\n\n"
            "Formato: |desc_1: texto| |desc_2: texto| etc."
        )
        raw = self._call(prompt, temperature=TEMP_BALANCED)
        return self._parse_and_supervise(raw)

    def generate_bloquehistoria(self, tit_seo: str, nuevo_tema: str) -> str:
        """Bloque historia (MCR agencia) — H2 + descripción breve."""
        location = self._extract_location_from_title(nuevo_tema)
        import hashlib as _hbh
        _bloquehistoria_tit_variants = [
            f"Renta un auto y descubre {location} a tu ritmo",
            f"Alquila un auto en {location} y vive la experiencia",
            f"Tu viaje en {location} comienza con la renta correcta",
            f"Alquiler de autos en {location}: tu punto de partida",
        ]
        _bh_idx = int(_hbh.md5(nuevo_tema.encode()).hexdigest(), 16) % len(_bloquehistoria_tit_variants)
        tit_default = _bloquehistoria_tit_variants[_bh_idx]
        if self.brand == "mcr":
            tone = "serio y confiable"
            desc_default = (
                f"En {location}, comparar opciones de renta de autos te permite planear cada trayecto con mayor claridad. "
                "Elige la alternativa que mejor se ajusta a tu ruta y avanza con un itinerario eficiente, "
                "cómodo y alineado con tus tiempos de viaje."
            )
        else:
            tone = "cercano y dinámico"
            desc_default = (
                f"Recorrer {location} con movilidad propia te da libertad para improvisar y aprovechar cada plan. "
                "Compara opciones, organiza tus tiempos y arma una experiencia de viaje más flexible "
                "desde el primer día."
            )

        prompt = (
            f"Tema: {nuevo_tema}, contexto LP: {tit_seo}\n"
            "Genera contenido para un bloque narrativo corto de landing page.\n"
            "REGLAS:\n"
            "- tit: H2 breve y natural, OBLIGATORIO incluir 'alquiler' o 'renta' de forma orgánica. "
            "Ejemplos válidos: 'Renta un auto y descubre [destino] a tu ritmo' / "
            "'Alquila un auto en [destino] y vive la experiencia' / "
            "'Tu viaje en [destino] comienza con el alquiler correcto'.\n"
            f"- desc: 55 a 60 palabras, tono {tone}.\n"
            "- No uses listas ni markdown.\n"
            "Salida obligatoria:\n"
            "|tit: ...|\n"
            "|desc: ...|"
        )
        raw = self._call(prompt, temperature=TEMP_BALANCED)
        result = self._parse_and_supervise(raw, tit_default=tit_default)
        fields = parse_fields(result)
        if not fields.get("desc"):
            fields["desc"] = desc_default
        return "\n".join(f"|{k}: {v}|" for k, v in fields.items())
 

# Alias for compatibility
MilesGenerator = ContentGenerator
