#include <WiFi.h>
#include <HTTPClient.h>
#include <time.h>  
#include <PubSubClient.h>
WiFiClient espClient;
PubSubClient mqttClient(espClient);


const char* mqtt_server = "broker.hivemq.com";
const int mqtt_port = 1883;

const char* ssid = "Casa_09";
const char* password = "casamelo09";

const char* FIREBASE_HOST = "https://firestore.googleapis.com/v1/projects/tcc1-155fa/databases/(default)/documents/sensores";
const char* FIREBASE_API_KEY = "AIzaSyD-3x3bJH3r2n0hyngOOC7_WOuvPBHo_T4";

#define SENSOR_BAIXO_PIN 18
#define SENSOR_ALTO_PIN 21
#define BOMBA_ATIVACAO_PIN 22  
#define BOMBA_STATUS_PIN 23   
#define LED_BAIXO_PIN 32  
#define LED_MEDIO_PIN 19 
#define LED_ALTO_PIN 33 

bool lastStateBaixo = LOW;
bool lastStateAlto = LOW;
bool altoCaiu = false;

void setup() {
  Serial.begin(115200);
  
  pinMode(SENSOR_BAIXO_PIN, INPUT_PULLDOWN);
  pinMode(SENSOR_ALTO_PIN, INPUT_PULLDOWN);
  pinMode(BOMBA_ATIVACAO_PIN, OUTPUT);
  pinMode(BOMBA_STATUS_PIN, INPUT_PULLDOWN);

  pinMode(LED_BAIXO_PIN, OUTPUT);
  pinMode(LED_MEDIO_PIN, OUTPUT);           
  pinMode(LED_ALTO_PIN,  OUTPUT);

  digitalWrite(LED_BAIXO_PIN, LOW);
  digitalWrite(LED_MEDIO_PIN, LOW);  
  digitalWrite(LED_ALTO_PIN, LOW);

  WiFi.begin(ssid, password);
  Serial.print("Conectando ao WiFi...");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".!");
  }
  Serial.println("\nConectado ao WiFi!");

  mqttClient.setServer(mqtt_server, mqtt_port);
  mqttClient.setCallback(callbackMQTT);
  conectarMQTT();

  // Configura e espera sincronização do tempo
  configTime(-3 * 3600, 0, "pool.ntp.org", "time.nist.gov");
  esperarSyncTime();
}


void loop() {
  mqttClient.loop();
  verificarSensor(SENSOR_ALTO_PIN, lastStateAlto, "alto"); 
  verificarSensor(SENSOR_BAIXO_PIN, lastStateBaixo, "baixo");


bool condicaoMedio = (digitalRead(SENSOR_BAIXO_PIN) == LOW) && 
                     (digitalRead(SENSOR_ALTO_PIN)  == LOW);

digitalWrite(LED_MEDIO_PIN, condicaoMedio ? HIGH : LOW);

bool condicaoBaixo = (digitalRead(SENSOR_BAIXO_PIN) == HIGH);
digitalWrite(LED_BAIXO_PIN, condicaoBaixo ? HIGH : LOW);

bool condicaoAlto = (digitalRead(SENSOR_ALTO_PIN) == HIGH);
digitalWrite(LED_ALTO_PIN, condicaoAlto ? HIGH : LOW);


  delay(500);
}


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
  for (int i = 0; i < length; i++) {
    mensagem += (char)payload[i];
  }

  Serial.print("Recebido: ");
  Serial.println(mensagem);

  // Separar nome e comando
  int espaco = mensagem.indexOf(' ');
  if (espaco > 0) {
    String nome = mensagem.substring(0, espaco);
    String comando = mensagem.substring(espaco + 1);

    if (comando == "ligar") {
      ativarBomba();
      enviarComandoFirestore(nome + " ligou");
    } else if (comando == "desligar") {
      desligarBomba();
      enviarComandoFirestore(nome + " desligou");
    }
  }
}


void verificarSensor(int pino, bool &ultimoEstado, const char* nome) {
  // Debounce simples
  bool leitura = digitalRead(pino);
  delay(15);
  bool estadoAtual = digitalRead(pino);
  if (estadoAtual != leitura) return; // ruído

  if (estadoAtual != ultimoEstado) {
    ultimoEstado = estadoAtual;

    // "subindo" por sensor:
    //  - baixo: SUBIU quando ABRIU (LOW)
    //  - alto : SUBIU quando FECHOU (HIGH)
    bool subindo = (strcmp(nome, "baixo") == 0) ? (estadoAtual == LOW)
                                                : (estadoAtual == HIGH);

    // Mensagem (mantém a inversão apenas para o "baixo")
    const char* msg;
    if (strcmp(nome, "baixo") == 0) {
      // baixo: FECHOU(HIGH)=desceu, ABRIU(LOW)=subiu
      msg = (estadoAtual == HIGH) ? "desceu" : "subiu";
    } else {
      // alto: FECHOU(HIGH)=subiu, ABRIU(LOW)=desceu
      msg = (estadoAtual == HIGH) ? "subiu" : "desceu";
    }

    if (validarSequencia2Niveis(nome, subindo)) {
      Serial.printf("Sensor %s: %s\n", nome, msg);
      enviarDadosFirestore(nome, msg);

      if (strcmp(nome, "alto") == 0 && subindo) { // alto FECHOU -> cheio
        desligarBomba();
        altoCaiu = false;
      }
      if (strcmp(nome, "alto") == 0 && !subindo) { // alto ABRIU -> começou a esvaziar
        altoCaiu = true;
      }
      if (strcmp(nome, "baixo") == 0 && !subindo && altoCaiu) { // baixo FECHOU após alto cair -> liga
        ativarBomba();
        altoCaiu = false;
      }
    } else {
      Serial.println("Erro: Mudança de nível inválida!");
    }
  }
}



bool validarSequencia2Niveis(const char* nome, bool subindo) {
  bool baixo = digitalRead(SENSOR_BAIXO_PIN);
  bool alto  = digitalRead(SENSOR_ALTO_PIN);

  if (subindo) {
    // "subindo" físico:
    //  - baixo: ABRIU (LOW)
    //  - alto : FECHOU (HIGH)
    if (strcmp(nome, "baixo") == 0) {
      // início do enchimento: pode abrir a qualquer momento
      return true;
    }
    if (strcmp(nome, "alto") == 0) {
      // alto só deve fechar se baixo já estiver alto (enchendo corretamente)
      return (baixo == LOW);
    }
  } else {
    // "descendo" físico:
    //  - baixo: FECHOU (HIGH)
    //  - alto : ABRIU  (LOW)
    if (strcmp(nome, "alto") == 0) {
      // alto cai primeiro ao esvaziar; baixo ainda deve estar HIGH
      return (baixo == LOW);
    }
    if (strcmp(nome, "baixo") == 0) {
      // baixo só deve fechar quando alto já estiver baixo
      return (alto == LOW);
    }
  }
  return false;
}


void ativarBomba() {
  Serial.println("Ativando bomba...");
  digitalWrite(BOMBA_ATIVACAO_PIN, HIGH);
  delay(100);

  unsigned long inicio = millis();
  while (millis() - inicio < 5000) {
    if (digitalRead(BOMBA_STATUS_PIN) == HIGH) {
      Serial.println("Bomba ligada com sucesso!");
      return;
    }
  }
  Serial.println("Erro: Bomba não foi ligada dentro do tempo!");
}


void desligarBomba() {
  Serial.println("Desligando bomba...");
  digitalWrite(BOMBA_ATIVACAO_PIN, LOW);
}


void enviarDadosFirestore(const char* sensor, String estado) {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;

    String url = String(FIREBASE_HOST) + "?key=" + FIREBASE_API_KEY;

    String jsonPayload =
      "{ \"fields\": { "
        "\"sensor\": { \"stringValue\": \"" + String(sensor) + "\" }, "
        "\"estado\": { \"stringValue\": \"" + estado + "\" }, "
        "\"timestamp\": { \"timestampValue\": \"" + getISOTime() + "\" } "
      "} }";

    http.begin(url);
    http.addHeader("Content-Type", "application/json");

    int httpResponseCode = http.POST(jsonPayload);

    if (httpResponseCode > 0) {
      Serial.printf("Dados enviados! Código HTTP: %d\n", httpResponseCode);
    } else {
      Serial.printf("Erro ao enviar: %s\n",
        http.errorToString(httpResponseCode).c_str());
    }

    http.end();
  } else {
    Serial.println("Erro: WiFi não conectado.");
  }
}


void enviarComandoFirestore(String mensagem) {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;

    String url = String(FIREBASE_HOST) + "?key=" + FIREBASE_API_KEY;
    String jsonPayload =
      "{ \"fields\": { "
      "\"bomba\": { \"stringValue\": \"" + mensagem + "\" }, "
      "\"timestamp\": { \"timestampValue\": \"" + getISOTime() + "\" } "
      "} }";

    http.begin(url);
    http.addHeader("Content-Type", "application/json");

    int httpResponseCode = http.POST(jsonPayload);

    if (httpResponseCode > 0) {
      Serial.printf("Comando enviado! Código HTTP: %d\n", httpResponseCode);
    } else {
      Serial.printf("Erro ao enviar comando: %s\n", http.errorToString(httpResponseCode).c_str());
    }

    http.end();
  }
}


String getISOTime() {
  time_t now;
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) {
    return "1970-01-01T00:00:00Z";
  }
  char buffer[30];
  strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%SZ", &timeinfo);
  return String(buffer);
}


void esperarSyncTime() {
  struct tm timeinfo;
  while (!getLocalTime(&timeinfo)) {
    Serial.println("Esperando sincronização do tempo...");
    delay(1000);
  }
}