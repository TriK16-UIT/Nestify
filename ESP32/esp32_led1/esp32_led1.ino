#include "BluetoothSerial.h"
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Preferences.h>

#define LEDPIN 4

String device_name = "LED1";
String ssid = "";
String password = "";
String host = "";
String HubID = "";
String get_info[4];
int j = 0;
String info;
String Topic;
String previousState = "";

bool bluetooth_disconnect = false;
long start_millis;
long timeout = 10000;
long lastMsg = 0;

enum connection_stage { PAIRING, WIFI, MQTT, CONNECTED };
enum connection_stage stage = PAIRING;

BluetoothSerial SerialBT;
WiFiClient espClient;
PubSubClient client(espClient);
Preferences preferences;

void setup(){
  Serial.begin(115200);
  pinMode(LEDPIN, OUTPUT);

  // Initialize preferences
  preferences.begin("wifi-config", false);

  // Load stored values
  ssid = preferences.getString("ssid", "");
  password = preferences.getString("password", "");
  host = preferences.getString("host", "");
  HubID = preferences.getString("HubID", "");
  Topic = preferences.getString("Topic", "");

  if (ssid != "" && password != "" && host != "" && HubID != "" && Topic != "") {
    stage = WIFI;
  } else {
    stage = PAIRING;
  }
}

void init_bluetooth()
{
  SerialBT.begin(device_name);
  Serial.printf("");
  Serial.printf("The device with name \"%s\" is started.\nNow you can pair it with Bluetooth!\n", device_name.c_str());
  bluetooth_disconnect = false;
}

void disconnect_bluetooth()
{
  delay(1000);
  Serial.println("BT stopping");
  delay(1000);
  SerialBT.flush();
  SerialBT.disconnect();
  SerialBT.end();
  Serial.println("BT stopped");
  delay(1000);
  bluetooth_disconnect = true;
}

void handle_bluetooth_data(String info)
{
  for (auto x : info)
  {
    if (x == '|')
    {
      j++;
      continue;  
    }
    else
      get_info[j] = get_info[j] + x;
  }
  ssid = get_info[0];
  password = get_info[1];
  host = get_info[2];
  HubID = get_info[3];
  Topic = HubID + "/" + device_name;

  // Save the values
  preferences.putString("ssid", ssid);
  preferences.putString("password", password);
  preferences.putString("host", host);
  preferences.putString("HubID", HubID);
  preferences.putString("Topic", Topic);
}

bool init_wifi()
{
  Serial.println(ssid);
  Serial.println(password);
  start_millis = millis();
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED)
  {
    delay(500);
    Serial.print(".");
    if (millis() - start_millis > timeout)
      {
        Serial.println("WiFi Connection Failed!");
        WiFi.disconnect(true, true);
        return false;
      }
    }
  Serial.println("WiFi connected!");
  return true;
}

bool init_mqtt()
{
  Serial.println(host);
  client.setServer(host.c_str(), 1883);
  client.setCallback(callback);
  start_millis = millis();
  while (client.connected())
  {
    if (WiFi.status() != WL_CONNECTED)
    {
      stage = WIFI;
      break;
    }
    delay(500);
    Serial.print(".");
    if (client.connect("ESP32_client2"))
    {
      Serial.println("MQTT Connected!");
      client.subscribe(Topic.c_str());
      return true;
    }
    if (millis() - start_millis > timeout)
    {
      Serial.println("MQTT Connection Failed!");
      WiFi.disconnect(true, true);
      return false;
    }
  }
}

void callback(char* topic, byte* message, unsigned int length) 
{
  String messageTemp;
  
  for (int i = 0; i < length; i++) {
    messageTemp += (char)message[i];
  }
  Serial.println();

  if (String(topic) == String(Topic)) {
      if (messageTemp == "ON")
      {
        Serial.println("Order Received!");
        digitalWrite(LEDPIN, HIGH);
        Serial.println("LED IS ON!");
      }
      else if (messageTemp == "OFF")
      {
        Serial.println("Order Received!");
        digitalWrite(LEDPIN, LOW);
        Serial.println("LED IS OFF!");
      }
      else if (messageTemp == "disconnect")
      {
        Serial.println("Disconnect command received, clearing preferences and restarting...");
        preferences.clear();
        ESP.restart();
      }
  }

  //Similarly add more if statements to check for other subscribed topics 
}

void loop() {
  delay(20);
  switch (stage)
  {
    case PAIRING:
      if (!bluetooth_disconnect)
        init_bluetooth();
      Serial.println("Waiting for SSID provided by server... ");
      Serial.println("Waiting for password provided by server... ");
      while (info == "")
      {
        if (SerialBT.available()) {
        info = SerialBT.readString();
        }
      }
      handle_bluetooth_data(info);
      if (ssid == "" || host == "")
        stage = PAIRING;
      else
        stage = WIFI;
      break;

    case WIFI:
      Serial.println("Waiting for Wi-Fi connection");
      if (init_wifi())
      {
        Serial.println("");
        Serial.println("Wifi connected");
        Serial.print("IP address: ");
        Serial.println(WiFi.localIP());
        disconnect_bluetooth();
        stage = MQTT;
      }
      else
      {
        Serial.println("Wi-Fi connection failed");
        delay(2000);
        stage = PAIRING;  
      }
      break;

    case MQTT:
      Serial.println("Waiting for MQTT connection");
      if (init_mqtt())
        stage = CONNECTED;
      else
        stage = PAIRING;
      break;

    case CONNECTED:
      if (!client.connected())
      {
        Serial.println("MQTT Disconnected");
        WiFi.disconnect(true, true);
        stage = PAIRING;
      }
      client.loop();

      long now = millis();
      if (now - lastMsg > 4000)
      {
        lastMsg = now;

        StaticJsonDocument<200> doc;
        String currentState = digitalRead(LEDPIN) == HIGH ? "ON" : "OFF";

        if (currentState != previousState) {
          doc["status"] = currentState;
          previousState = currentState;
        } else {
          doc["status"] = "";
        }
      
        doc["type"] = "toggle";

        char jsonBuffer[512];
        serializeJson(doc, jsonBuffer);

        Serial.println(jsonBuffer);
        client.publish(Topic.c_str(), jsonBuffer);
      }
      break;
  }
}


