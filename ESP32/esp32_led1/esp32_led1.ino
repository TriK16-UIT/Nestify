#include "BluetoothSerial.h"
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"
#include <Adafruit_NeoPixel.h>

#define LEDPIN 2
#define RESETPIN 33
#define PIN 14
#define ATTEMPTS 5
#define NUMPIXELS 8

// LIGHT SETUP
Adafruit_NeoPixel pixels(NUMPIXELS, PIN, NEO_GRB + NEO_KHZ800);
int dim = 10; // Default brightness (max)
int r = 255, g = 255, b = 255; // Default color (white)
String ledState = "OFF"; // Default state is OFF

// DEVICE SETUP
String device_id = "LIGHT1";
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

/*************  RESET BUTTON FLAGS  *************/
volatile bool resetPressed = false;
volatile unsigned long lastResetPress = 0;
const unsigned long debounceDelay = 50;

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
void setNeoPixelColor(int r, int g, int b);

/*************  ISR FOR RESET BUTTON  *************/
void IRAM_ATTR RESET_ISR() {
  unsigned long currentTime = millis();
  if (currentTime - lastResetPress > debounceDelay) {
    resetPressed = true;
    lastResetPress = currentTime;
  }
}

void setNeoPixelColor(int r, int g, int b) {
  for (int i = 0; i < NUMPIXELS; i++) {
    pixels.setPixelColor(i, pixels.Color(r, g, b));
  }
}

void setup(){
  Serial.begin(115200);
  pinMode(LEDPIN, OUTPUT);
  pinMode(RESETPIN, INPUT_PULLUP);  // Reset button with internal pullup

  //Brownout trigger disabled
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);

  attachInterrupt(digitalPinToInterrupt(RESETPIN), RESET_ISR, FALLING);

  // Initialize preferences
  preferences.begin("config", false);
  // For debugging
  // preferences.clear();

  // Load stored values
  ssid = preferences.getString("ssid", "");
  password = preferences.getString("password", "");
  host = preferences.getString("host", "");
  HubID = preferences.getString("HubID", "");
  Topic = preferences.getString("Topic", "");
  dim = preferences.getInt("dim", 10);
  r = preferences.getInt("r", 255);
  g = preferences.getInt("g", 255);
  b = preferences.getInt("b", 255);
  ledState = preferences.getString("ledState", "OFF");

  stage = (ssid != "" && password != "" && host != "" && HubID != "" && Topic != "") ? WIFI : PAIRING;

  pixels.begin();
  pixels.setBrightness(dim);
  setNeoPixelColor(r, g, b);

  if (ledState == "ON") {
    pixels.show();
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
  pixels.clear();
  pixels.show();
  
  // If MQTT is connected, announce reset to Hub
  if (client.connected() && stage == CONNECTED) {
    Serial.println("Announcing reset to Hub...");
    JsonDocument resetDoc;
    resetDoc["status"] = "reset";
    resetDoc["type"] = "toggle";
    String resetMessage;
    serializeJson(resetDoc, resetMessage);
    
    client.publish(Topic.c_str(), resetMessage.c_str());
    client.loop(); // Ensure message is sent
    delay(500);    // Give time for message to be transmitted
  }
  else if (!bluetooth_disconnect) {
    Serial.println("Announcing reset to Hub...");
    SerialBT.print("Error: Hard reset triggered|");
    delay(500);
  }
  
  disconnectBluetooth();
  preferences.clear();
  Serial.println("Performing hard reset...");
  delay(1000);
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
  client.setCallback(MQTTCallback);
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
    if (client.connect("LIGHT1"))
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

void MQTTCallback(char* topic, byte* message, unsigned int length) 
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
        pixels.setBrightness(dim);
        setNeoPixelColor(r, g, b);
        pixels.show();
        ledState = "ON";
        preferences.putString("ledState", "ON");
      }
      else if (status == "OFF") {
        Serial.println("OFF");
        pixels.clear();
        pixels.show();
        ledState = "OFF";
        preferences.putString("ledState", "OFF");
      }
      else if (status == "disconnect") {
        Serial.println("disconnect");
        pixels.clear();
        pixels.show();
        preferences.clear();
        ESP.restart();
      }
    }

    if (doc.containsKey("dim")) {
      dim = doc["dim"].as<int>();
      Serial.println(dim);
      pixels.clear();
      pixels.setBrightness(dim);
      setNeoPixelColor(r, g, b);
      if (ledState == "ON") {
        pixels.show();
      }
      preferences.putInt("dim", dim);
    }

    if (doc.containsKey("colour")) {
      String colour = doc["colour"].as<String>();
      Serial.println(colour.c_str());
      if (colour[0] == '#') {
        colour.remove(0, 1); // Remove the '#' character
      }
      if (colour.length() == 6) {
        long rgb = strtol(colour.c_str(), NULL, 16);
        r = (rgb >> 16) & 0xFF;
        g = (rgb >> 8) & 0xFF;
        b = rgb & 0xFF;

        pixels.clear();
        pixels.setBrightness(dim);
        setNeoPixelColor(r, g, b);

        if (ledState == "ON") {
          pixels.show();
        }
        preferences.putInt("r", r);
        preferences.putInt("g", g);
        preferences.putInt("b", b);
      }
    }
  }

  //Similarly add more if statements to check for other subscribed topics 
}

void loop() {
  delay(20);

  // Check for reset button press
  if (resetPressed) {
    resetPressed = false;
    Serial.println("Reset button pressed - performing hard reset");
    hard_reset();
  }

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

