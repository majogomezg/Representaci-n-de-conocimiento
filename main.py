# -------------------------------------------
# Parte generada con apoyo de IA (ChatGPT).
# Prompt base (resumen): "Implementar red semántica con es_un/instancia/atributo,
# herencia de atributos y consultas 'atributo X de Y?' y
# 'clases o instancias con atributo X y valor Z?'."
# -------------------------------------------

from collections import deque, defaultdict
import sys
import re

class SemanticNet:
    def __init__(self):
        self.parents = defaultdict(set)
        # instancia -> clase
        self.class_of = {}
        # atributos directos: entidad -> {atributo: valor}
        self.attrs = defaultdict(dict)
        # catálogos
        self.classes = set()
        self.instances = set()

    # --------- carga de hechos ---------
    def add_es_un(self, child: str, parent: str):
        self.parents[child].add(parent)
        self.classes.add(child)
        self.classes.add(parent)

    def add_instancia(self, inst: str, klass: str):
        self.class_of[inst] = klass
        self.instances.add(inst)
        self.classes.add(klass)

    def add_atributo(self, entity: str, attr: str, value: str):
        self.attrs[entity][attr] = value

    # --------- utilidades ---------
    def all_entities(self):
        # unión: clases, instancias y cualquier entidad que aparezca solo con atributo
        return sorted(set(self.classes) | set(self.instances) | set(self.attrs.keys()))

    # --------- resolución de herencia ---------
    def _get_attr_from_class_chain(self, klass: str, attr: str):
        """Busca attr en klass y ancestros (BFS: primero más cercanos)."""
        if not klass:
            return None
        visited = set()
        q = deque([klass])
        while q:
            c = q.popleft()
            if c in visited:
                continue
            visited.add(c)
            # atributo directo en la clase actual
            if attr in self.attrs.get(c, {}):
                return self.attrs[c][attr]
            # subir a padres
            for p in self.parents.get(c, ()):
                if p not in visited:
                    q.append(p)
        return None

    def get_effective_attr(self, entity: str, attr: str):
        """Valor efectivo del atributo para clase o instancia (con herencia)."""
        # 1) si es instancia: prioridad al atributo directo de la instancia
        if entity in self.instances:
            if attr in self.attrs.get(entity, {}):
                return self.attrs[entity][attr]
            klass = self.class_of.get(entity)
            return self._get_attr_from_class_chain(klass, attr)

        # 2) si es clase: busca en la clase y luego ancestros
        if entity in self.classes or entity in self.attrs:
            # puede aparecer como clase implícita si solo tiene atributos
            if attr in self.attrs.get(entity, {}):
                return self.attrs[entity][attr]
            return self._get_attr_from_class_chain(entity, attr)

        # 3) entidad desconocida
        return None

# --------- parsing del archivo ---------
FACT_RE = re.compile(r'^\s*(es_un|instancia|atributo)\s*\((.+)\)\s*$')

def parse_fact(line: str):
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    m = FACT_RE.match(line)
    if not m:
        raise ValueError(f"Línea inválida: {line}")
    kind, inside = m.group(1), m.group(2)
    parts = [p.strip() for p in inside.split(",")]
    if kind == "es_un":
        if len(parts) != 2:
            raise ValueError(f"es_un requiere 2 argumentos: {line}")
        return ("es_un", parts[0], parts[1])
    elif kind == "instancia":
        if len(parts) != 2:
            raise ValueError(f"instancia requiere 2 argumentos: {line}")
        return ("instancia", parts[0], parts[1])
    else:  # atributo
        if len(parts) != 3:
            raise ValueError(f"atributo requiere 3 argumentos: {line}")
        return ("atributo", parts[0], parts[1], parts[2])

def load_file(path: str) -> SemanticNet:
    net = SemanticNet()
    with open(path, "r", encoding="utf-8") as f:
        for ln, raw in enumerate(f, start=1):
            raw = raw.strip()
            if not raw or raw.startswith("#"):
                continue
            fact = parse_fact(raw)
            if not fact:
                continue
            if fact[0] == "es_un":
                _, a, b = fact
                net.add_es_un(a, b)
            elif fact[0] == "instancia":
                _, i, c = fact
                net.add_instancia(i, c)
            else:
                _, e, a, v = fact
                net.add_atributo(e, a, v)
    return net

# --------- parsing de consultas ---------
Q1_RE = re.compile(r'^\s*atributo\s+(\S+)\s+de\s+(\S+)\?\s*$', re.IGNORECASE)
Q2_RE = re.compile(r'^\s*clases\s+o\s+instancias\s+con\s+atributo\s+(\S+)\s+y\s+valor\s+(\S+)\?\s*$', re.IGNORECASE)

def answer_query(net: SemanticNet, q: str) -> str:
    m1 = Q1_RE.match(q)
    if m1:
        attr, entity = m1.group(1), m1.group(2)
        val = net.get_effective_attr(entity, attr)
        if val is None:
            return f"{entity} no tiene atributo {attr} (ni por herencia)."
        return f"atributo {attr} de {entity} = {val}"

    m2 = Q2_RE.match(q)
    if m2:
        attr, value = m2.group(1), m2.group(2)
        matches = []
        for e in net.all_entities():
            val = net.get_effective_attr(e, attr)
            if val == value:
                matches.append(e)
        if not matches:
            return f"No hay clases o instancias con atributo {attr} y valor {value}."
        return "Coincidencias: " + ", ".join(matches)

    return "Consulta no reconocida. Usa:\n- atributo X de Y?\n- clases o instancias con atributo X y valor Z?"

# --------- CLI ---------
def main():
    if len(sys.argv) < 2:
        print("Uso: python main.py <ruta_al_txt>")
        sys.exit(1)
    path = sys.argv[1]
    try:
        net = load_file(path)
    except Exception as e:
        print(f"Error leyendo archivo: {e}")
        sys.exit(1)

    print("Red cargada. Escribe consultas y presiona Enter. 'salir' para terminar.")
    print("Ejemplos:")
    print("  atributo color de Tom?")
    print("  atributo tiene de Tom?")
    print("  clases o instancias con atributo tiene y valor pelo?")

    while True:
        try:
            q = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nHasta luego.")
            break
        if q.lower() in ("salir", "exit", "quit"):
            break
        if not q:
            continue
        print(answer_query(net, q))

if __name__ == "__main__":
    main()
