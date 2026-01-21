import os
import re
from datetime import datetime
from typing import List, Dict, Tuple
from langchain_ollama import ChatOllama
from app.schemas.dto import AquaIntent
from app.services.firestore import fetch_sensor_events


# ----------------- AJUDANTES DE PERÍODO ----------------- #

def parse_period_from_text(text: str) -> str:
    """
    Converte expressões em português em códigos de período:

    - 'hoje' -> '1d' (aproximação: últimas 24 horas)
    - 'nos últimos 2 dias', 'nos últimos dois dias' -> '2d'
    - 'nos últimos 20 dias' -> '20d'
    - 'nos últimos 30 dias' -> '30d'
    - 'essa semana', 'nesta semana', 'nessa semana' -> 'this_week'
    - 'nesse mês', 'neste mês', 'esse mês', 'nesse ultimo mês', 'nesse último mês' -> 'this_month'
    - 'últimos dias' (sem número) -> '7d'
    - fallback -> '7d'
    """
    t = text.lower()

    # hoje
    if "hoje" in t:
        return "1d"

    # últimos X dias (com número explícito)
    m = re.search(r"(\d+)\s*dias?", t)
    if m:
        return f"{m.group(1)}d"

    # 'últimos 7 dias', 'últimos trinta dias' etc (não numéricos simples)
    if "últimos 7 dias" in t or "últimos sete dias" in t:
        return "7d"
    if "últimos 30 dias" in t or "últimos trinta dias" in t:
        return "30d"
    if "últimos 20 dias" in t or "últimos vinte dias" in t:
        return "20d"
    if "últimas 24 horas" in t:
        return "1d"

    # semana atual
    if "essa semana" in t or "nesta semana" in t or "nessa semana" in t or "esta semana" in t:
        return "this_week"

    # mês atual (incluindo 'nesse ultimo mês', que no uso prático é o mês corrente)
    if (
        "nesse mês" in t
        or "neste mês" in t
        or "esse mês" in t
        or "nesse ultimo mês" in t
        or "nesse último mês" in t
        or "neste ultimo mês" in t
        or "neste último mês" in t
    ):
        return "this_month"

    # 'últimos dias' genérico
    if "últimos dias" in t:
        return "7d"

    # fallback padrão
    return "7d"


def period_human_label(period: str) -> str:
    """Só para escrever bonito na resposta."""
    p = (period or "").lower()
    if p.endswith("d") and p[:-1].isdigit():
        dias = int(p[:-1])
        if dias == 1:
            return "no último dia"
        return f"nos últimos {dias} dias"
    if p == "this_week":
        return "nesta semana"
    if p == "this_month":
        return "neste mês"
    return f"no período ({period})"


# ----------------- LLM PARA INTENÇÃO ----------------- #

def _get_intent_llm() -> ChatOllama:
    """
    Cria o modelo Ollama via LangChain com saída estruturada AquaIntent.
    """
    base_llm = ChatOllama(
        model=os.getenv("OLLAMA_MODEL", "qwen2:0.5b"),
        temperature=0.0,
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        num_predict=256,
    )
    # LangChain converte a resposta diretamente em AquaIntent
    return base_llm.with_structured_output(AquaIntent)


def detect_intent(question: str) -> AquaIntent:
    """
    Usa a LLM (via LangChain) para inferir a intenção da pergunta.
    Depois aplica regras de período pra garantir que period não fique em branco.
    """
    llm = _get_intent_llm()

    system_prompt = (
        "Você é um classificador de perguntas do sistema AquaMonitor.\n"
        "Receba perguntas em português sobre sensores de nível (alto/baixo) e reservatórios.\n"
        "Preencha o modelo AquaIntent com os campos corretos.\n\n"
        "Regras de mapeamento (kind):\n"
        "- Se o usuário pedir um resumo geral de eventos -> kind='summary_all'.\n"
        "- Se pedir resumo focado em nível baixo -> kind='summary_low', sensor='baixo'.\n"
        "- Se perguntar 'quantas vezes os sensores emitiram eventos' -> kind='count_events_all'.\n"
        "- Se perguntar 'quantas vezes a caixa ficou vazia' (sensor baixo desceu) "
        "  -> kind='count_low', sensor='baixo', estado='desceu'.\n"
        "- Se perguntar 'quantas vezes a caixa ficou cheia' (sensor alto subiu) "
        "  -> kind='count_full', sensor='alto', estado='subiu'.\n"
        "- Se perguntar 'quanto tempo a caixa ficou vazia' -> kind='duration_empty', sensor='baixo'.\n"
        "- Se perguntar 'quanto tempo a caixa ficou cheia' -> kind='duration_full', sensor='alto'.\n"
        "- Se perguntar 'quantas vezes e quanto tempo a caixa ficou vazia' "
        "  -> kind='count_and_duration_empty', sensor='baixo'.\n"
        "- Se perguntar 'quantas vezes e quanto tempo a caixa ficou cheia' "
        "  -> kind='count_and_duration_full', sensor='alto'.\n"
        "- Se perguntar ao mesmo tempo sobre 'vazia' e 'cheia' (ex: "
        "  'quantas vezes a caixa ficou vazia e quantas vezes ficou cheia nesse período') "
        "  -> kind='count_empty_and_full'.\n"
        "- Se perguntar sobre 'inconsistência', 'erro de sensor', 'anormalidade' ou 'algum problema nos sensores' "
        "  -> kind='health_check'.\n"
        "- Perguntas de apresentação como 'quem é você', 'quem é vc', "
        "  'o que você faz', 'qual o seu nome' -> kind='smalltalk'.\n"
        "- Se não tiver certeza -> kind='unknown'.\n\n"
        "Regras de período (period):\n"
        "- 'hoje' -> '1d'.\n"
        "- 'nos últimos 2 dias', 'nos últimos dois dias' -> '2d'.\n"
        "- 'nos últimos 20 dias' -> '20d'.\n"
        "- 'nos últimos 30 dias' -> '30d'.\n"
        "- 'essa semana', 'nesta semana', 'nessa semana' -> 'this_week'.\n"
        "- 'nesse mês', 'neste mês', 'esse mês', 'nesse ultimo mês' -> 'this_month'.\n"
        "- Se o usuário só disser 'últimos dias' sem número -> '7d'.\n"
        "- Se não entender, deixe period=None e o backend ajusta.\n\n"
        "Use apenas 'baixo' ou 'alto' para o campo sensor.\n"
    )



    messages = [
        ("system", system_prompt),
        ("human", question),
    ]

    intent: AquaIntent = llm.invoke(messages)

    # força período a partir de regras se veio vazio ou estranho
    if not intent.period:
        intent.period = parse_period_from_text(question)

    # fallback final
    if not intent.period:
        intent.period = "7d"

    return intent


# ----------------- CÁLCULOS EM CIMA DOS EVENTOS ----------------- #

def _compute_summary(events: List[Dict], only_sensor: str | None = None) -> Dict:
    total = 0
    by_sensor = {}
    by_estado = {}

    for e in events:
        sensor = str(e.get("sensor") or "").strip().lower()
        estado = str(e.get("estado") or "").strip().lower()

        if only_sensor and sensor != only_sensor:
            continue

        total += 1
        by_sensor[sensor] = by_sensor.get(sensor, 0) + 1
        by_estado[estado] = by_estado.get(estado, 0) + 1

    return {
        "total": total,
        "by_sensor": by_sensor,
        "by_estado": by_estado,
    }


def _format_duration(seconds: float) -> str:
    if seconds <= 0:
        return "0 minutos"
    minutos = int(seconds // 60)
    horas = minutos // 60
    minutos = minutos % 60
    dias = horas // 24
    horas = horas % 24

    partes = []
    if dias:
        partes.append(f"{dias} dia(s)")
    if horas:
        partes.append(f"{horas} hora(s)")
    if minutos:
        partes.append(f"{minutos} minuto(s)")
    return " e ".join(partes)


def _duration_for_sensor_state(
    events: List[Dict],
    sensor_alvo: str,
    estado_down: str,
    estado_up: str,
) -> float:
    """
    Calcula o tempo total (em segundos) em que o sensor_alvo ficou no estado "baixo" ou "alto",
    considerando pares estado_down -> estado_up.

    Exemplo:
    - Para caixa vazia: sensor='baixo', estado_down='desceu', estado_up='subiu'.
    """
    # ordena cronologicamente
    events_sorted = sorted(events, key=lambda e: e.get("timestamp"))

    last_down_ts: datetime | None = None
    total_seconds = 0.0

    for e in events_sorted:
        sensor = str(e.get("sensor") or "").strip().lower()
        estado = str(e.get("estado") or "").strip().lower()
        ts = e.get("timestamp")

        if not isinstance(ts, datetime):
            continue

        if sensor == sensor_alvo and estado == estado_down:
            last_down_ts = ts

        elif sensor == sensor_alvo and estado == estado_up:
            if last_down_ts is not None:
                total_seconds += (ts - last_down_ts).total_seconds()
                last_down_ts = None

    # se terminar o período ainda "baixo"/"alto", poderíamos opcionalmente contar até o fim do período;
    # por simplicidade, vamos ignorar esse caso por enquanto.
    return total_seconds


# ----------------- FUNÇÃO PRINCIPAL USADA PELO ENDPOINT ----------------- #

def handle_analytics_question(question: str) -> Tuple[str, AquaIntent]:
    """
    Fluxo completo:
    - Trata smalltalk e perguntas muito gerais via regras simples.
    - Usa LLM + AquaIntent para perguntas analíticas.
    - Aplica regras para casos específicos (duas métricas na mesma pergunta,
      vazio+cheio, inconsistência, etc.).
    """
    q_lower = question.lower().strip()

    # 0) SMALLTALK / APRESENTAÇÃO – não precisa nem chamar a LLM
    smalltalk_patterns = [
        "quem é você",
        "quem é vc",
        "quem e vc",
        "quem e você",
        "qual o seu nome",
        "qual é o seu nome",
        "o que você faz",
        "o que vc faz",
        "o que você é",
        "quem é o aquamonitor",
        "quem é o assistente",
    ]
    if any(p in q_lower for p in smalltalk_patterns):
        intent = AquaIntent(kind="smalltalk")
        answer = (
            "Eu sou o assistente de IA do AquaMonitor. "
            "Analiso os eventos dos sensores da caixa d'água para responder perguntas "
            "sobre quantas vezes a caixa ficou vazia ou cheia, tempos de funcionamento "
            "e possíveis comportamentos anormais ao longo do tempo."
        )
        return answer, intent

    # 1) Detecta intenção com LLM
    intent = detect_intent(question)

    # 2) Regras manuais complementares (melhor do que depender só do modelo pequeno)

    # 2.1) Se falar de inconsistência / problema, força health_check
    if any(x in q_lower for x in ["inconsist", "anormal", "estranho", "problema nos sensores"]):
        intent.kind = "health_check"

    # 2.2) Se perguntar vazio E cheio na mesma frase, responde duas contagens
    if "vazia" in q_lower and "cheia" in q_lower and "quantas vezes" in q_lower:
        intent.kind = "count_empty_and_full"

    # 2.3) Quantas vezes E quanto tempo (vazia)
    if "vazia" in q_lower and "quantas vezes" in q_lower and "quanto tempo" in q_lower:
        intent.kind = "count_and_duration_empty"
        intent.sensor = "baixo"

    # 2.4) Quantas vezes E quanto tempo (cheia)
    if "cheia" in q_lower and "quantas vezes" in q_lower and "quanto tempo" in q_lower:
        intent.kind = "count_and_duration_full"
        intent.sensor = "alto"

    # garante período
    period = intent.period or parse_period_from_text(question)
    intent.period = period
    label_period = period_human_label(period)

    # 3) Busca eventos do Firestore
    events = fetch_sensor_events(period)

    # 4) Decide resposta conforme a intenção

    # UNKNOWN
    if intent.kind == "unknown":
        return (
            "Ainda não consegui entender bem o tipo de análise que você quer. "
            "Tente perguntar, por exemplo: "
            "'Quantas vezes a caixa ficou vazia nos últimos 20 dias?' "
            "ou 'Me dê um resumo dos eventos nesta semana'.",
            intent,
        )

    # SUMMARY_ALL
    if intent.kind == "summary_all":
        summary = _compute_summary(events)
        linhas = [
            f"Resumo de eventos {label_period}:",
            f"- Total de eventos registrados: {summary['total']}",
            "",
            "Por sensor:",
        ]
        for sensor, cnt in summary["by_sensor"].items():
            linhas.append(f"  • {sensor}: {cnt} evento(s)")
        linhas.append("")
        linhas.append("Por estado:")
        for estado, cnt in summary["by_estado"].items():
            linhas.append(f"  • {estado}: {cnt} evento(s)")
        return ("\n".join(linhas), intent)

    # SUMMARY_LOW
    if intent.kind == "summary_low":
        summary = _compute_summary(events, only_sensor="baixo")
        linhas = [
            f"Resumo do sensor de nível BAIXO {label_period}:",
            f"- Total de eventos do sensor baixo: {summary['total']}",
        ]
        if summary["total"] > 0:
            linhas.append("Por estado:")
            for estado, cnt in summary["by_estado"].items():
                linhas.append(f"  • {estado}: {cnt} evento(s)")
        return ("\n".join(linhas), intent)

    # COUNT_EVENTS_ALL
    if intent.kind == "count_events_all":
        total = len(events)
        resposta = (
            f"{label_period}, todos os sensores registraram um total de "
            f"{total} evento(s) (considerando alto/baixo, subiu/desceu)."
        )
        return resposta, intent

    # COUNT_LOW (caixa vazia)
    if intent.kind == "count_low":
        cnt = sum(
            1
            for e in events
            if str(e.get("sensor") or "").strip().lower() == "baixo"
            and str(e.get("estado") or "").strip().lower() == "desceu"
        )
        resposta = (
            f"{label_period}, a caixa ficou VAZIA (sensor baixo DESCEU) "
            f"{cnt} vez(es)."
        )
        return resposta, intent

    # COUNT_FULL (caixa cheia)
    if intent.kind == "count_full":
        cnt = sum(
            1
            for e in events
            if str(e.get("sensor") or "").strip().lower() == "alto"
            and str(e.get("estado") or "").strip().lower() == "subiu"
        )
        resposta = (
            f"{label_period}, a caixa ficou CHEIA (sensor alto SUBIU) "
            f"{cnt} vez(es)."
        )
        return resposta, intent

    # COUNT_EMPTY_AND_FULL (duas contagens na mesma resposta)
    if intent.kind == "count_empty_and_full":
        cnt_empty = sum(
            1
            for e in events
            if str(e.get("sensor") or "").strip().lower() == "baixo"
            and str(e.get("estado") or "").strip().lower() == "desceu"
        )
        cnt_full = sum(
            1
            for e in events
            if str(e.get("sensor") or "").strip().lower() == "alto"
            and str(e.get("estado") or "").strip().lower() == "subiu"
        )
        resposta = (
            f"{label_period}, a caixa ficou VAZIA (sensor baixo DESCEU) "
            f"{cnt_empty} vez(es) e ficou CHEIA (sensor alto SUBIU) "
            f"{cnt_full} vez(es)."
        )
        return resposta, intent

    # DURATION_EMPTY
    if intent.kind == "duration_empty":
        seconds = _duration_for_sensor_state(
            events,
            sensor_alvo="baixo",
            estado_down="desceu",
            estado_up="subiu",
        )
        resposta = (
            f"{label_period}, a caixa ficou VAZIA por aproximadamente "
            f"{_format_duration(seconds)} no total."
        )
        return resposta, intent

    # DURATION_FULL
    if intent.kind == "duration_full":
        seconds = _duration_for_sensor_state(
            events,
            sensor_alvo="alto",
            estado_down="subiu",
            estado_up="desceu",
        )
        resposta = (
            f"{label_period}, a caixa ficou CHEIA por aproximadamente "
            f"{_format_duration(seconds)} no total."
        )
        return resposta, intent

    # NOVO: COUNT_AND_DURATION_EMPTY
    if intent.kind == "count_and_duration_empty":
        cnt = sum(
            1
            for e in events
            if str(e.get("sensor") or "").strip().lower() == "baixo"
            and str(e.get("estado") or "").strip().lower() == "desceu"
        )
        seconds = _duration_for_sensor_state(
            events,
            sensor_alvo="baixo",
            estado_down="desceu",
            estado_up="subiu",
        )
        resposta = (
            f"{label_period}, a caixa ficou VAZIA (sensor baixo DESCEU) "
            f"{cnt} vez(es) e permaneceu vazia por cerca de "
            f"{_format_duration(seconds)} ao todo."
        )
        return resposta, intent

    # NOVO: COUNT_AND_DURATION_FULL
    if intent.kind == "count_and_duration_full":
        cnt = sum(
            1
            for e in events
            if str(e.get("sensor") or "").strip().lower() == "alto"
            and str(e.get("estado") or "").strip().lower() == "subiu"
        )
        seconds = _duration_for_sensor_state(
            events,
            sensor_alvo="alto",
            estado_down="subiu",
            estado_up="desceu",
        )
        resposta = (
            f"{label_period}, a caixa ficou CHEIA (sensor alto SUBIU) "
            f"{cnt} vez(es) e permaneceu cheia por cerca de "
            f"{_format_duration(seconds)} ao todo."
        )
        return resposta, intent

    # HEALTH_CHECK (inconsistência / comportamento anormal)
    if intent.kind == "health_check":
        summary = _compute_summary(events)
        total = summary["total"]
        low_events = summary["by_sensor"].get("baixo", 0)
        high_events = summary["by_sensor"].get("alto", 0)

        linhas = [
            f"Verificação de consistência dos sensores {label_period}:",
            f"- Total de eventos registrados: {total}.",
            f"- Sensor BAIXO: {low_events} evento(s).",
            f"- Sensor ALTO: {high_events} evento(s).",
            "",
        ]

        if total == 0:
            linhas.append(
                "Não foram registrados eventos no período. "
                "Isso pode indicar pouca variação no nível ou algum problema na leitura dos sensores."
            )
        else:
            if low_events == 0:
                linhas.append(
                    "O sensor de nível BAIXO não registrou eventos. "
                    "Se isso for inesperado, pode haver falha nesse sensor ou na instalação."
                )
            if high_events == 0:
                linhas.append(
                    "O sensor de nível ALTO não registrou eventos. "
                    "Se a caixa costuma encher com frequência, isso pode indicar problema no sensor alto."
                )
            if low_events > 0 and high_events > 0:
                linhas.append(
                    "Ambos os sensores registraram eventos, o que indica comportamento ativo. "
                    "Para uma análise mais profunda, seria interessante comparar com períodos anteriores "
                    "ou definir limites de operação considerados normais."
                )

        return ("\n".join(linhas), intent)

    # fallback geral
    return (
        "Ainda não implementei este tipo específico de análise, "
        "mas posso responder sobre quantidade de eventos, tempo de caixa vazia/cheia "
        "e resumos por período.",
        intent,
    )
