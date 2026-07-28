#include <WiFi.h>
#include <HTTPClient.h>
#include <time.h>
#include <PubSubClient.h>

WiFiClient espClient;
PubSubClient mqttClient(espClient);

// ===================== WIFI / MQTT =====================
const char* ssid = "eng.mateus";
const char* password = "casamelo09";

const char* mqtt_server = "broker.hivemq.com";
const int mqtt_port = 1883;
const char* MQTT_CONTROL_TOPIC = "bomba/controle";
const char* MQTT_CONTROL_V2_TOPIC = "bomba/controle/v2";
const char* MQTT_STATE_TOPIC = "bomba/estado";

// ===================== FIRESTORE =====================
// Coleção sensores
const char* FIREBASE_SENSORES_URL =
  "https://firestore.googleapis.com/v1/projects/tcc1-155fa/databases/(default)/documents/sensores";
// Coleção comandos
const char* FIREBASE_COMANDOS_URL =
  "https://firestore.googleapis.com/v1/projects/tcc1-155fa/databases/(default)/documents/comandos";

const char* FIREBASE_API_KEY =
  "AIzaSyD-3x3bJH3r2n0hyngOOC7_WOuvPBHo_T4";

// ===================== NTP / HORÁRIO (UTC) =====================
const char* NTP_SERVER = "pool.ntp.org";
const long  GMT_OFFSET_SEC = 0;
const int   DAYLIGHT_OFFSET_SEC = 0;

// Retorna horário ISO 8601 em UTC (ex.: "2025-10-02T13:42:00Z")
String getISOTimeUTC() {
  time_t now = time(nullptr);
  struct tm* t = gmtime(&now);
  char buf[25];
  snprintf(buf, sizeof(buf), "%04d-%02d-%02dT%02d:%02d:%02dZ",
           t->tm_year + 1900, t->tm_mon + 1, t->tm_mday,
           t->tm_hour, t->tm_min, t->tm_sec);
  return String(buf);
}

void esperarSyncTime() {
  // Evita travar: aguarda até o epoch ficar "grande o suficiente"
  // (qualquer valor > ~2020 já indica NTP ok)
  time_t now = time(nullptr);
  while (now < 1600000000) {
    Serial.println("Esperando sincronização do tempo (NTP)...");
    delay(1000);
    now = time(nullptr);
  }
  Serial.print("Tempo sincronizado (UTC): ");
  Serial.println(getISOTimeUTC());
}

// ===================== PINOS =====================
#define SENSOR_BAIXO_PIN 18
#define SENSOR_ALTO_PIN  21

#define BOMBA_ATIVACAO_PIN 22   // saída para acionar relé/driver
#define BOMBA_STATUS_PIN   23   // entrada de status

#define LED_BAIXO_PIN 32
#define LED_MEDIO_PIN 19
#define LED_ALTO_PIN  33

// NOVO: acionamento físico (chave ligada em 3.3V)
#define ACIONAMENTO_FISICO_PIN 25
// No relé, os pinos 2,4,6, 7 e 8 são os que funcionam 

// ===================== ESTADOS / PRIORIDADE =====================
bool lastStateBaixo = LOW;
bool lastStateAlto  = LOW;

// Estado atual "comandado" da bomba (evita ficar reacionando toda hora)
bool bombaComandadaLigada = false;

// Remoto
bool remoteHasCommand = false;
bool remoteDesiredOn  = false;

// Automático (último desejo automático)
bool autoDesiredOn = false;

// Para logs/eventos
bool lastFisico = LOW;

// ===================== PROTÓTIPOS =====================
void conectarMQTT();
void callbackMQTT(char* topic, byte* payload, unsigned int length);

void verificarSensor(int pino, bool &ultimoEstado, const char* nome);
void avaliarEAplicarControle(const char* motivo);
void avaliarEAplicarControleDetalhado(const char* motivo, const String& commandId, const String& requestedSource);
void processarComandoRemoto(const String& commandId, const String& nome, bool desiredOn);

bool ativarBomba();
bool desligarBomba();

void enviarDadosFirestore(const char* sensor, const String& estado);
void enviarComandoFirestore(const String& mensagem, const String& acionamento);
void enviarComandoFirestoreDetalhado(
  const String& mensagem,
  const String& acionamento,
  bool requestedState,
  bool appliedState,
  bool applied,
  bool confirmed,
  bool stateChanged,
  const String& overriddenBy,
  const String& priority,
  const String& commandId,
  const String& reason
);
void publicarEstadoBomba(
  bool pumpOn,
  const String& mode,
  const String& source,
  bool confirmed,
  bool applied,
  const String& overriddenBy,
  const String& priority,
  const String& commandId,
  const String& reason
);
String gerarCommandId(const String& prefix);
String extrairStringJson(const String& json, const String& key);
bool extrairBoolJson(const String& json, const String& key, bool fallback);

static String escapeJson(const String& s) {
  // Escape básico para evitar quebrar JSON
  String out;
  out.reserve(s.length() + 8);
  for (size_t i = 0; i < s.length(); i++) {
    char c = s[i];
    if (c == '\"') out += "\\\"";
    else if (c == '\\') out += "\\\\";
    else if (c == '\n') out += "\\n";
    else if (c == '\r') out += "\\r";
    else if (c == '\t') out += "\\t";
    else out += c;
  }
  return out;
}

// ===================== SETUP =====================
void setup() {
  Serial.begin(115200);

  pinMode(SENSOR_BAIXO_PIN, INPUT_PULLDOWN);
  pinMode(SENSOR_ALTO_PIN,  INPUT_PULLDOWN);

  pinMode(BOMBA_ATIVACAO_PIN, OUTPUT);
  pinMode(BOMBA_STATUS_PIN,   INPUT_PULLDOWN);

  pinMode(LED_BAIXO_PIN, OUTPUT);
  pinMode(LED_MEDIO_PIN, OUTPUT);
  pinMode(LED_ALTO_PIN,  OUTPUT);

  pinMode(ACIONAMENTO_FISICO_PIN, INPUT_PULLDOWN);

  digitalWrite(LED_BAIXO_PIN, LOW);
  digitalWrite(LED_MEDIO_PIN, LOW);
  digitalWrite(LED_ALTO_PIN,  LOW);

  // Wi-Fi
  WiFi.begin(ssid, password);
  Serial.print("Conectando ao WiFi...");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".!");
  }
  Serial.println("\nConectado ao WiFi!");

  // MQTT
  mqttClient.setServer(mqtt_server, mqtt_port);
  mqttClient.setCallback(callbackMQTT);
  conectarMQTT();

  // NTP (UTC)
  configTime(GMT_OFFSET_SEC, DAYLIGHT_OFFSET_SEC, NTP_SERVER, "time.nist.gov");
  esperarSyncTime();

  // Estado inicial dos sensores
  lastStateBaixo = digitalRead(SENSOR_BAIXO_PIN);
  lastStateAlto  = digitalRead(SENSOR_ALTO_PIN);

  // Estado inicial do físico
  lastFisico = digitalRead(ACIONAMENTO_FISICO_PIN);

  Serial.println("Firmware iniciado.");
  Serial.print("Fisico inicial: ");
  Serial.println(lastFisico ? "ON" : "OFF");

  // Avalia estado inicial (prioridades)
  avaliarEAplicarControle("boot");
}

// ===================== LOOP =====================
void loop() {
  mqttClient.loop();

  // Sensores -> sempre válidos: envia e atualiza automático em eventos
  verificarSensor(SENSOR_ALTO_PIN,  lastStateAlto,  "alto");
  verificarSensor(SENSOR_BAIXO_PIN, lastStateBaixo, "baixo");

  // LEDs (como estava)
  bool condicaoMedio = (digitalRead(SENSOR_BAIXO_PIN) == LOW) &&
                       (digitalRead(SENSOR_ALTO_PIN)  == LOW);
  digitalWrite(LED_MEDIO_PIN, condicaoMedio ? HIGH : LOW);

  bool condicaoBaixo = (digitalRead(SENSOR_BAIXO_PIN) == HIGH);
  digitalWrite(LED_BAIXO_PIN, condicaoBaixo ? HIGH : LOW);

  bool condicaoAlto = (digitalRead(SENSOR_ALTO_PIN) == HIGH);
  digitalWrite(LED_ALTO_PIN, condicaoAlto ? HIGH : LOW);

  // Detecta mudança no acionamento físico (para log + reavaliar)
  bool fisico = digitalRead(ACIONAMENTO_FISICO_PIN);
  if (fisico != lastFisico) {
    lastFisico = fisico;
    Serial.print("Mudança no acionamento físico: ");
    Serial.println(fisico ? "ON (força bomba ligada)" : "OFF (libera prioridades)");
    avaliarEAplicarControle("mudança físico");
  }

  delay(200);
}

// ===================== MQTT =====================
void conectarMQTT() {
  while (!mqttClient.connected()) {
    Serial.print("Conectando ao MQTT...");
    if (mqttClient.connect("esp32_client")) {
      Serial.println("Conectado!");
      mqttClient.subscribe(MQTT_CONTROL_TOPIC);
      mqttClient.subscribe(MQTT_CONTROL_V2_TOPIC);
      publicarEstadoBomba(
        bombaComandadaLigada,
        "boot",
        "firmware",
        false,
        true,
        "",
        "boot",
        gerarCommandId("boot"),
        "mqtt conectado"
      );
    } else {
      Serial.print(".");
      delay(2000);
    }
  }
}

void callbackMQTT(char* topic, byte* payload, unsigned int length) {
  String topicName = String(topic);
  String mensagem;
  for (unsigned int i = 0; i < length; i++) {
    mensagem += (char)payload[i];
  }

  Serial.print("MQTT recebido: ");
  Serial.println(mensagem);

  if (topicName == MQTT_CONTROL_V2_TOPIC) {
    String commandId = extrairStringJson(mensagem, "command_id");
    if (commandId.length() == 0) {
      commandId = gerarCommandId("mqtt");
    }

    bool desiredOn = extrairBoolJson(mensagem, "desired_on", false);
    String command = extrairStringJson(mensagem, "command");
    command.toLowerCase();
    if (command == "ligar") {
      desiredOn = true;
    } else if (command == "desligar") {
      desiredOn = false;
    } else if (mensagem.indexOf("\"desired_on\"") < 0) {
      Serial.println("JSON MQTT ignorado: comando ausente.");
      return;
    }

    processarComandoRemoto(commandId, "bomba", desiredOn);
    return;
  }

  // Espera formato: "<nome> ligar" ou "<nome> desligar"
  int espaco = mensagem.indexOf(' ');
  if (espaco <= 0) return;

  String nome = mensagem.substring(0, espaco);
  String comando = mensagem.substring(espaco + 1);
  comando.trim();

  if (comando == "ligar") {
    processarComandoRemoto(gerarCommandId("legacy"), nome, true);
  } else if (comando == "desligar") {
    processarComandoRemoto(gerarCommandId("legacy"), nome, false);
  }
}

// ===================== SENSORES =====================
void verificarSensor(int pino, bool &ultimoEstado, const char* nome) {
  // Debounce simples
  bool leitura = digitalRead(pino);
  delay(15);
  bool estadoAtual = digitalRead(pino);
  if (estadoAtual != leitura) return; // ruído

  if (estadoAtual == ultimoEstado) return;
  ultimoEstado = estadoAtual;

  // Mantém sua semântica original:
  // baixo: HIGH = "desceu", LOW = "subiu"
  // alto : HIGH = "subiu",  LOW = "desceu"
  const char* msg;
  if (strcmp(nome, "baixo") == 0) {
    msg = (estadoAtual == HIGH) ? "desceu" : "subiu";
  } else {
    msg = (estadoAtual == HIGH) ? "subiu" : "desceu";
  }

  Serial.printf("Sensor %s mudou: %s\n", nome, msg);
  enviarDadosFirestore(nome, String(msg));

  // Atualiza automático APENAS pelas regras pedidas:
  //  - se baixo "desceu" => liga
  //  - se alto  "subiu"  => desliga
  bool autoChanged = false;

  if (strcmp(nome, "baixo") == 0 && String(msg) == "desceu") {
    autoDesiredOn = true;
    autoChanged = true;
    Serial.println("Auto: baixo DESCEU => deseja LIGAR bomba");
  }

  if (strcmp(nome, "alto") == 0 && String(msg) == "subiu") {
    autoDesiredOn = false;
    autoChanged = true;
    Serial.println("Auto: alto SUBIU => deseja DESLIGAR bomba");
  }

  if (autoChanged) {
    if (digitalRead(ACIONAMENTO_FISICO_PIN) == HIGH || remoteHasCommand) {
      String overriddenBy = digitalRead(ACIONAMENTO_FISICO_PIN) == HIGH ? "físico" : "remoto";
      String commandId = gerarCommandId("auto");
      String mensagem = autoDesiredOn ? "bomba ligar" : "bomba desligar";
      enviarComandoFirestoreDetalhado(
        mensagem,
        "automático",
        autoDesiredOn,
        bombaComandadaLigada,
        false,
        true,
        false,
        overriddenBy,
        overriddenBy,
        commandId,
        "automatico sobreposto por prioridade"
      );
      publicarEstadoBomba(
        bombaComandadaLigada,
        overriddenBy,
        "automático",
        true,
        false,
        overriddenBy,
        overriddenBy,
        commandId,
        "automatico sobreposto por prioridade"
      );
    }

    avaliarEAplicarControle("evento sensor (auto)");
  }
}

// ===================== PRIORIDADE E APLICAÇÃO =====================
void avaliarEAplicarControle(const char* motivo) {
  avaliarEAplicarControleDetalhado(motivo, "", "");
}

void avaliarEAplicarControleDetalhado(const char* motivo, const String& commandId, const String& requestedSource) {
  bool fisico = (digitalRead(ACIONAMENTO_FISICO_PIN) == HIGH);

  bool desiredOn = false;
  String acionamento = "automático";

  if (fisico) {
    desiredOn = true;
    acionamento = "físico";
  } else if (remoteHasCommand) {
    desiredOn = remoteDesiredOn;
    acionamento = "remoto";
  } else {
    desiredOn = autoDesiredOn;
    acionamento = "automático";
  }

  String effectiveCommandId = commandId;
  if (effectiveCommandId.length() == 0) {
    effectiveCommandId = gerarCommandId(acionamento);
  }

  if (desiredOn == bombaComandadaLigada) {
    if (commandId.length() > 0 || requestedSource.length() > 0) {
      enviarComandoFirestoreDetalhado(
        desiredOn ? "bomba ligar" : "bomba desligar",
        acionamento,
        desiredOn,
        bombaComandadaLigada,
        true,
        true,
        false,
        "",
        acionamento,
        effectiveCommandId,
        "estado ja estava aplicado"
      );
      publicarEstadoBomba(
        bombaComandadaLigada,
        acionamento,
        requestedSource.length() > 0 ? requestedSource : acionamento,
        true,
        true,
        "",
        acionamento,
        effectiveCommandId,
        "estado ja estava aplicado"
      );
    }
    return;
  }

  Serial.print("Aplicando controle (");
  Serial.print(motivo);
  Serial.print(") => ");
  Serial.print(desiredOn ? "LIGAR" : "DESLIGAR");
  Serial.print(" | acionamento=");
  Serial.println(acionamento);

  bool confirmed = false;
  if (desiredOn) {
    confirmed = ativarBomba();
    bombaComandadaLigada = true;
  } else {
    confirmed = desligarBomba();
    bombaComandadaLigada = false;
  }

  enviarComandoFirestoreDetalhado(
    desiredOn ? "bomba ligar" : "bomba desligar",
    acionamento,
    desiredOn,
    bombaComandadaLigada,
    true,
    confirmed,
    true,
    "",
    acionamento,
    effectiveCommandId,
    String(motivo)
  );
  publicarEstadoBomba(
    bombaComandadaLigada,
    acionamento,
    requestedSource.length() > 0 ? requestedSource : acionamento,
    confirmed,
    true,
    "",
    acionamento,
    effectiveCommandId,
    String(motivo)
  );
}

void processarComandoRemoto(const String& commandId, const String& nome, bool desiredOn) {
  remoteHasCommand = true;
  remoteDesiredOn = desiredOn;

  if (digitalRead(ACIONAMENTO_FISICO_PIN) == HIGH) {
    Serial.println("Remoto IGNORADO (físico ativo).");
    enviarComandoFirestoreDetalhado(
      desiredOn ? nome + " pediu LIGAR" : nome + " pediu DESLIGAR",
      "remoto",
      desiredOn,
      bombaComandadaLigada,
      false,
      true,
      false,
      "físico",
      "físico",
      commandId,
      "comando remoto sobreposto por acionamento fisico"
    );
    publicarEstadoBomba(
      bombaComandadaLigada,
      "manual chave",
      "remoto",
      true,
      false,
      "físico",
      "físico",
      commandId,
      "comando remoto sobreposto por acionamento fisico"
    );
    return;
  }

  Serial.println(desiredOn ? "Remoto recebido: LIGAR" : "Remoto recebido: DESLIGAR");
  avaliarEAplicarControleDetalhado(desiredOn ? "mqtt ligar" : "mqtt desligar", commandId, "remoto");
}

// ===================== BOMBA =====================
bool ativarBomba() {
  Serial.println("Ativando bomba...");
  digitalWrite(BOMBA_ATIVACAO_PIN, HIGH);
  delay(100);

  // Confirmação opcional via status pin
  unsigned long inicio = millis();
  while (millis() - inicio < 5000) {
    if (digitalRead(BOMBA_STATUS_PIN) == HIGH) {
      Serial.println("Bomba ligada (status OK)!");
      return true;
    }
  }
  Serial.println("Aviso: status não confirmou em 5s (mas comando foi enviado).");
  return false;
}

bool desligarBomba() {
  Serial.println("Desligando bomba...");
  digitalWrite(BOMBA_ATIVACAO_PIN, LOW);
  delay(100);
  bool confirmed = digitalRead(BOMBA_STATUS_PIN) == LOW;
  if (confirmed) {
    Serial.println("Bomba desligada (status OK)!");
  } else {
    Serial.println("Aviso: status não confirmou desligamento.");
  }
  return confirmed;
}

// ===================== FIRESTORE =====================
void enviarDadosFirestore(const char* sensor, const String& estado) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Erro: WiFi não conectado (sensores).");
    return;
  }

  HTTPClient http;
  String url = String(FIREBASE_SENSORES_URL) + "?key=" + FIREBASE_API_KEY;

  String jsonPayload =
    "{ \"fields\": { "
      "\"sensor\": { \"stringValue\": \"" + escapeJson(String(sensor)) + "\" }, "
      "\"estado\": { \"stringValue\": \"" + escapeJson(estado) + "\" }, "
      "\"timestamp\": { \"timestampValue\": \"" + getISOTimeUTC() + "\" } "
    "} }";

  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  int httpResponseCode = http.POST(jsonPayload);

  if (httpResponseCode > 0) {
    Serial.printf("Sensor enviado (Firestore). HTTP: %d\n", httpResponseCode);
  } else {
    Serial.printf("Erro Firestore (sensores): %s\n",
                  http.errorToString(httpResponseCode).c_str());
  }
  http.end();
}

void enviarComandoFirestore(const String& mensagem, const String& acionamento) {
  bool requestedState = mensagem.indexOf("deslig") < 0;
  enviarComandoFirestoreDetalhado(
    mensagem,
    acionamento,
    requestedState,
    bombaComandadaLigada,
    true,
    true,
    true,
    "",
    acionamento,
    gerarCommandId("legacy"),
    "registro legado"
  );
}

void enviarComandoFirestoreDetalhado(
  const String& mensagem,
  const String& acionamento,
  bool requestedState,
  bool appliedState,
  bool applied,
  bool confirmed,
  bool stateChanged,
  const String& overriddenBy,
  const String& priority,
  const String& commandId,
  const String& reason
) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Erro: WiFi não conectado (comandos).");
    return;
  }

  HTTPClient http;
  String url = String(FIREBASE_COMANDOS_URL) + "?key=" + FIREBASE_API_KEY;

  String jsonPayload =
    "{ \"fields\": { "
      "\"bomba\": { \"stringValue\": \"" + escapeJson(mensagem) + "\" }, "
      "\"acionamento\": { \"stringValue\": \"" + escapeJson(acionamento) + "\" }, "
      "\"source\": { \"stringValue\": \"" + escapeJson(acionamento) + "\" }, "
      "\"command_id\": { \"stringValue\": \"" + escapeJson(commandId) + "\" }, "
      "\"requested_state\": { \"booleanValue\": " + String(requestedState ? "true" : "false") + " }, "
      "\"applied_state\": { \"booleanValue\": " + String(appliedState ? "true" : "false") + " }, "
      "\"applied\": { \"booleanValue\": " + String(applied ? "true" : "false") + " }, "
      "\"confirmed\": { \"booleanValue\": " + String(confirmed ? "true" : "false") + " }, "
      "\"state_changed\": { \"booleanValue\": " + String(stateChanged ? "true" : "false") + " }, "
      "\"priority\": { \"stringValue\": \"" + escapeJson(priority) + "\" }, "
      "\"overridden_by\": { \"stringValue\": \"" + escapeJson(overriddenBy) + "\" }, "
      "\"reason\": { \"stringValue\": \"" + escapeJson(reason) + "\" }, "
      "\"timestamp\": { \"timestampValue\": \"" + getISOTimeUTC() + "\" } "
    "} }";

  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  int httpResponseCode = http.POST(jsonPayload);

  if (httpResponseCode > 0) {
    Serial.printf("Comando enviado (Firestore). HTTP: %d\n", httpResponseCode);
  } else {
    Serial.printf("Erro Firestore (comandos): %s\n",
                  http.errorToString(httpResponseCode).c_str());
  }
  http.end();
}

void publicarEstadoBomba(
  bool pumpOn,
  const String& mode,
  const String& source,
  bool confirmed,
  bool applied,
  const String& overriddenBy,
  const String& priority,
  const String& commandId,
  const String& reason
) {
  if (!mqttClient.connected()) return;

  String payload =
    "{"
      "\"schema_version\":1,"
      "\"pump_on\":" + String(pumpOn ? "true" : "false") + ","
      "\"mode\":\"" + escapeJson(mode) + "\","
      "\"confirmed\":" + String(confirmed ? "true" : "false") + ","
      "\"applied\":" + String(applied ? "true" : "false") + ","
      "\"source\":\"" + escapeJson(source) + "\","
      "\"priority\":\"" + escapeJson(priority) + "\","
      "\"overridden_by\":\"" + escapeJson(overriddenBy) + "\","
      "\"command_id\":\"" + escapeJson(commandId) + "\","
      "\"reason\":\"" + escapeJson(reason) + "\","
      "\"timestamp\":\"" + getISOTimeUTC() + "\""
    "}";

  mqttClient.publish(MQTT_STATE_TOPIC, payload.c_str(), true);
  Serial.print("Estado bomba publicado: ");
  Serial.println(payload);
}

String gerarCommandId(const String& prefix) {
  return prefix + "-" + String((unsigned long)time(nullptr)) + "-" + String(millis());
}

String extrairStringJson(const String& json, const String& key) {
  String pattern = "\"" + key + "\"";
  int keyIndex = json.indexOf(pattern);
  if (keyIndex < 0) return "";
  int colon = json.indexOf(':', keyIndex + pattern.length());
  if (colon < 0) return "";
  int firstQuote = json.indexOf('"', colon + 1);
  if (firstQuote < 0) return "";
  int secondQuote = json.indexOf('"', firstQuote + 1);
  if (secondQuote < 0) return "";
  return json.substring(firstQuote + 1, secondQuote);
}

bool extrairBoolJson(const String& json, const String& key, bool fallback) {
  String pattern = "\"" + key + "\"";
  int keyIndex = json.indexOf(pattern);
  if (keyIndex < 0) return fallback;
  int colon = json.indexOf(':', keyIndex + pattern.length());
  if (colon < 0) return fallback;
  String rest = json.substring(colon + 1);
  rest.trim();
  if (rest.startsWith("true")) return true;
  if (rest.startsWith("false")) return false;
  return fallback;
}
