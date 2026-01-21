#include <WiFi.h>
#include <HTTPClient.h>
#include <time.h>
#include <PubSubClient.h>

WiFiClient espClient;
PubSubClient mqttClient(espClient);

// ===================== WIFI / MQTT =====================
const char* ssid = "wifi-zone-ufam-1";
const char* password = "";

const char* mqtt_server = "broker.hivemq.com";
const int mqtt_port = 1883;

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

void ativarBomba();
void desligarBomba();

void enviarDadosFirestore(const char* sensor, const String& estado);
void enviarComandoFirestore(const String& mensagem, const String& acionamento);

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
      mqttClient.subscribe("bomba/controle");
    } else {
      Serial.print(".");
      delay(2000);
    }
  }
}

void callbackMQTT(char* topic, byte* payload, unsigned int length) {
  String mensagem;
  for (unsigned int i = 0; i < length; i++) {
    mensagem += (char)payload[i];
  }

  Serial.print("MQTT recebido: ");
  Serial.println(mensagem);

  // Espera formato: "<nome> ligar" ou "<nome> desligar"
  int espaco = mensagem.indexOf(' ');
  if (espaco <= 0) return;

  String nome = mensagem.substring(0, espaco);
  String comando = mensagem.substring(espaco + 1);
  comando.trim();

  if (comando == "ligar") {
    remoteHasCommand = true;
    remoteDesiredOn = true;

    // Se físico estiver ON, ignora efetividade, mas registra (útil p/ auditoria)
    if (digitalRead(ACIONAMENTO_FISICO_PIN) == HIGH) {
      Serial.println("Remoto IGNORADO (físico ativo).");
      enviarComandoFirestore(nome + " pediu LIGAR (ignorado: físico ativo)", "remoto");
      return;
    }

    Serial.println("Remoto aplicado: LIGAR");
    avaliarEAplicarControle("mqtt ligar");
    enviarComandoFirestore(nome + " ligou", "remoto");

  } else if (comando == "desligar") {
    remoteHasCommand = true;
    remoteDesiredOn = false;

    if (digitalRead(ACIONAMENTO_FISICO_PIN) == HIGH) {
      Serial.println("Remoto IGNORADO (físico ativo).");
      enviarComandoFirestore(nome + " pediu DESLIGAR (ignorado: físico ativo)", "remoto");
      return;
    }

    Serial.println("Remoto aplicado: DESLIGAR");
    avaliarEAplicarControle("mqtt desligar");
    enviarComandoFirestore(nome + " desligar", "remoto");
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
    // só tenta aplicar se não houver físico e se remoto não estiver mandando
    avaliarEAplicarControle("evento sensor (auto)");
    // opcional: registrar comando automático apenas quando ele realmente muda a bomba
    // (o registro final acontece dentro de avaliarEAplicarControle quando houver mudança)
  }
}

// ===================== PRIORIDADE E APLICAÇÃO =====================
void avaliarEAplicarControle(const char* motivo) {
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

  // Se não mudou, não faz nada
  if (desiredOn == bombaComandadaLigada) return;

  Serial.print("Aplicando controle (");
  Serial.print(motivo);
  Serial.print(") => ");
  Serial.print(desiredOn ? "LIGAR" : "DESLIGAR");
  Serial.print(" | acionamento=");
  Serial.println(acionamento);

  if (desiredOn) {
    ativarBomba();
    bombaComandadaLigada = true;
    enviarComandoFirestore("bomba ligar", acionamento);
  } else {
    desligarBomba();
    bombaComandadaLigada = false;
    enviarComandoFirestore("bomba desligar", acionamento);
  }
}

// ===================== BOMBA =====================
void ativarBomba() {
  Serial.println("Ativando bomba...");
  digitalWrite(BOMBA_ATIVACAO_PIN, HIGH);
  delay(100);

  // Confirmação opcional via status pin
  unsigned long inicio = millis();
  while (millis() - inicio < 5000) {
    if (digitalRead(BOMBA_STATUS_PIN) == HIGH) {
      Serial.println("Bomba ligada (status OK)!");
      return;
    }
  }
  Serial.println("Aviso: status não confirmou em 5s (mas comando foi enviado).");
}

void desligarBomba() {
  Serial.println("Desligando bomba...");
  digitalWrite(BOMBA_ATIVACAO_PIN, LOW);
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
