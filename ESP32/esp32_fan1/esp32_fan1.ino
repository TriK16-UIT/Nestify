#include "BluetoothSerial.h"
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"

#define LEDPIN 4
#define FANPIN 14
#define ATTEMPTS 5

// FAN SETUP
const int pwmFrequency = 5000;
const int pwmResolution = 8;
const int pwmChannel = 0;
int speed = 10;
String fanState = "OFF";

// DEVICE SETUP
String device_id = "FAN1";
String ssid, password, host, HubID, Topic, info;
String get_info[4];
bool bluetooth_disconnect = false;
long start_millis;
long timeout = 10000;

enum connection_stage { PAIRING, WIFI, MQTT, CONNECTED };
enum connection_stage stage = PAIRING;

BluetoothSerial SerialBT;
WiFiClient espClient;
PubSubClient client(espClient);
Preferences preferences;

// Function Prototypes
void initBluetooth();
void disconnectBluetooth();
void handleBluetoothData();
void clearBluetoothData();
void hard_reset();
bool initWiFi();
bool initMQTT();
void MQTTCallback(char* topic, byte* message, unsigned int length);
void publishStatus();
void setFanSpeed(int percentage);

void setFanSpeed(int percentage) {
  if (percentage < 0) percentage = 0;     // Ensure speed is not below 0%
  if (percentage > 100) percentage = 100; // Ensure speed is not above 100%

  int pwmValue = map(percentage, 0, 100, 0, 255);

  ledcWrite(pwmChannel, pwmValue);

}

void setup(){
  Serial.begin(115200);
  pinMode(LEDPIN, OUTPUT);

  //Brownout trigger disabled
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);

  // Initialize preferences
  preferences.begin("config", false);
  // For debugging
  preferences.clear();

  // Load stored values
  ssid = preferences.getString("ssid", "");
  password = preferences.getString("password", "");
  host = preferences.getString("host", "");
  HubID = preferences.getString("HubID", "");
  Topic = preferences.getString("Topic", "");
  speed = preferences.getInt("speed", 10);
  fanState = preferences.getString("fanState", "OFF");

  stage = (ssid != "" && password != "" && host != "" && HubID != "" && Topic != "") ? WIFI : PAIRING;

  ledcSetup(pwmChannel, pwmFrequency, pwmResolution);
  ledcAttachPin(FANPIN, pwmChannel);

  if (fanState == "ON") {
    setFanSpeed(speed);
  }
  else {
    setFanSpeed(0);
  }
}

void initBluetooth()
{
  digitalWrite(LEDPIN, HIGH);
  delay(2000);
  digitalWrite(LEDPIN, LOW);
  SerialBT.begin(device_id);
  Serial.printf("The device with name \"%s\" is started.\nNow you can pair it with Bluetooth!\n", device_id.c_str());
  bluetooth_disconnect = false;
}

void disconnectBluetooth()
{
  delay(1000);
  SerialBT.flush();
  SerialBT.disconnect();
  SerialBT.end();
  Serial.println("Bluetooth disconnected.");
  delay(1000);
  bluetooth_disconnect = true;
}

void handleBluetoothData()
{
  int j = 0;
  for (auto x : info)
  {
    if (x == '|')
    {
      j++;
      continue;  
    }
    else
      get_info[j] += x;
  }
  ssid = get_info[0];
  password = get_info[1];
  host = get_info[2];
  HubID = get_info[3];
  Topic = HubID + "/" + device_id;

  // Save the values
  preferences.putString("ssid", ssid);
  preferences.putString("password", password);
  preferences.putString("host", host);
  preferences.putString("HubID", HubID);
  preferences.putString("Topic", Topic);
}

void clearBluetoothData() {
  // Clear stored preferences
  preferences.clear();
  ssid = password = host = HubID = Topic = info = "";
  for (int i = 0; i < 4; i++) {
    get_info[i] = "";
  }
  Serial.println("Bluetooth data and preferences cleared.");
}

void hard_reset() {
  disconnectBluetooth();
  preferences.clear();
  ESP.restart();
}

bool initWiFi()
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

bool initMQTT()
{
  Serial.println(host);
  client.setServer(host.c_str(), 1883);
  client.setCallback(MQTTcallback);
  start_millis = millis();
  while (!client.connected())
  {
    if (WiFi.status() != WL_CONNECTED)
    {
      stage = WIFI;
      WiFi.disconnect(true, true);
      return false;
    }
    delay(500);
    Serial.print(".");
    if (client.connect("FAN1"))
    {
      Serial.println("MQTT Connected!");
      Serial.println(Topic.c_str());
      client.subscribe(Topic.c_str());
      return true;
    }
    if (millis() - start_millis > timeout)
    {
      Serial.println("MQTT Connection Failed!");
      return false;
    }
  }
  return false;
}

void MQTTcallback(char* topic, byte* message, unsigned int length) 
{
  String messageTemp;
  
  for (int i = 0; i < length; i++) {
    messageTemp += (char)message[i];
  }

  if (String(topic) == String(Topic)) {
    StaticJsonDocument<200> doc;
    DeserializationError error = deserializeJson(doc, messageTemp);

    Serial.println(messageTemp);

    if (error) {
      Serial.println("Error parsing JSON!");
      return;
    }

    if (doc.containsKey("status")) {
      String status = doc["status"].as<String>();
      if (status == "ON") {
        Serial.println("ON");
        setFanSpeed(speed);
        fanState = "ON";
        preferences.putString("fanState", "ON");
      }
      else if (status == "OFF") {
        Serial.println("OFF");
        setFanSpeed(0);
        fanState = "OFF";
        preferences.putString("fanState", "OFF");
      }
      else if (status == "disconnect") {
        Serial.println("disconnect");
        setFanSpeed(0);
        preferences.clear();
        ESP.restart();
      }
    }

    if (doc.containsKey("speed")) {
      speed = doc["speed"].as<int>();
      Serial.println(speed);
      if (fanState == "ON") {
        setFanSpeed(speed);
      }
      preferences.putInt("speed", speed);
    }
  }
}

void loop() {
  delay(20);
  static int wifi_attempts = 0;
  static int mqtt_attempts = 0;
  switch (stage)
  {
    case PAIRING:
      if (!bluetooth_disconnect) initBluetooth();
      Serial.println("Waiting for WiFi data provided by server... ");
      while (info == "") {
        if (SerialBT.available()) info = SerialBT.readString();
      }

      handleBluetoothData();

      stage = WIFI;
      break;

    case WIFI:
      Serial.println("Connecting to Wi-Fi...");
      if (initWiFi()) {
        stage = MQTT;
      }
      else {
        wifi_attempts++;
        if (wifi_attempts >= ATTEMPTS) { // Check if attempts exceed limit
          SerialBT.print("Error: WiFi connection failed|");
          hard_reset();
        }
      }
      break;

    case MQTT:
      Serial.println("Connecting to MQTT...");
      if (initMQTT()) {
        SerialBT.print("Success: MQTT connected|");
        disconnectBluetooth();
        stage = CONNECTED;
      }
      else {
        mqtt_attempts++;
        if (mqtt_attempts >= ATTEMPTS) {
          SerialBT.print("Error: MQTT connection failed|");
          hard_reset();
        }
      }
      break;

    case CONNECTED:
      if (!client.connected())
      {
        Serial.println("MQTT Disconnected");
        stage = MQTT;
      }
      client.loop();
      break;
  }
}

