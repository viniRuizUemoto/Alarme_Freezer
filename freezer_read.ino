#include <ArduinoJson.h>
#include <WiFi.h>
#include <HTTPClient.h>

// Precisa pedir para o TI liberar o MAC Address do ESP32 para conectar no wi-fi
const char* ssid        = "DP@CORP";
const int   Port_Read   = 22; // Pino do ESP32 conectado ao alarme
const int   ID_Freezer  = 0;
const char* ntfy_server = "http://192.168.255.207:8800/warning/"+ std::to_string(ID_Freezer); // Se mudar o servidor alterar para host_IP:port/warning/id
char jsonOutput[500];

void setup() {
  // Comunicação Serial
  Serial.begin(115200);
  pinMode(Port_Read, INPUT);

  WiFi.begin(ssid);
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
  }


}

void loop() {
  // Verifica conexão Wi-Fi
  if ((WiFi.status() == WL_CONNECTED)) {
    // Base da requisição HTTP
    HTTPClient http;
    http.begin(ntfy_server);
    http.addHeader("Content-Type","application/json");

    const size_t CAPACITY = JSON_OBJECT_SIZE(1);
    StaticJsonDocument<CAPACITY> doc;
    JsonObject object = doc.to<JsonObject>();
    // Verifica se alarme acionado ou não
    if (digitalRead(Port_Read) == 1) {
      // caso de alarme não acionado
      object["status"] = 200;
      object["message"] = "Freezer OK";
    } else {
      // alarme acionado
      object["status"] = 406;
      object["message"] = "Freezer Fora da Temperatura";
    }
    serializeJson(doc, jsonOutput);
    int httpCode = http.POST(String(jsonOutput));

    // delay entre cada execuçao
    http.end();
    delay(1000);
  }

}
