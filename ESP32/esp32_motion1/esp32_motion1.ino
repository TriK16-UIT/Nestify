#include "BluetoothSerial.h"
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"
#include <esp_camera.h>
#include "Base64.h"


/**********  USER‑ADJUSTABLE HARDWARE PINS  **********/
#define PIRPIN      12      // HC‑SR501 OUT pin → GPIO13
#define LEDPIN       4       // status LED (kept from your code)

/*  ESP32‑CAM (AI‑Thinker) camera pin map  */
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22
/******************************************************/

#define ATTEMPTS 5
String device_id = "MOTION1";
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

/*************  MOTION‑CAPTURE FLAGS  *************/
bool motionDetected = false;   // set in ISR

/*************  FUNCTION PROTOTYPES  *************/
void initBluetooth();
void disconnectBluetooth();
void handleBluetoothData();
void clearBluetoothData();
void hard_reset();
bool initWiFi();
bool initMQTT();
void MQTTCallback(char* topic, byte* message, unsigned int length);
void publishPicture();
bool initCamera();

/*************  ISR FOR PIR SENSOR  *************/
void IRAM_ATTR PIR_ISR() {
  motionDetected = true;
}

/*************  CAMERA INITIALISATION  *************/
bool initCamera() {
  camera_config_t config;
  config.ledc_channel   = LEDC_CHANNEL_0;
  config.ledc_timer     = LEDC_TIMER_0;
  config.pin_d0         = Y2_GPIO_NUM;
  config.pin_d1         = Y3_GPIO_NUM;
  config.pin_d2         = Y4_GPIO_NUM;
  config.pin_d3         = Y5_GPIO_NUM;
  config.pin_d4         = Y6_GPIO_NUM;
  config.pin_d5         = Y7_GPIO_NUM;
  config.pin_d6         = Y8_GPIO_NUM;
  config.pin_d7         = Y9_GPIO_NUM;
  config.pin_xclk       = XCLK_GPIO_NUM;
  config.pin_pclk       = PCLK_GPIO_NUM;
  config.pin_vsync      = VSYNC_GPIO_NUM;
  config.pin_href       = HREF_GPIO_NUM;
  config.pin_sccb_sda   = SIOD_GPIO_NUM;
  config.pin_sccb_scl   = SIOC_GPIO_NUM;
  config.pin_pwdn       = PWDN_GPIO_NUM;
  config.pin_reset      = RESET_GPIO_NUM;
  config.xclk_freq_hz   = 20000000;
  config.pixel_format   = PIXFORMAT_JPEG;
  // Frame parameters – trade quality vs. size as needed
  config.frame_size     = FRAMESIZE_QVGA;
  config.jpeg_quality   = 12;          // 0–63 (lower = better quality)
  config.fb_count       = 1;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    return false;
  }
  return true;
}

/*************  MQTT PAYLOAD PUBLISHER  *************/
void publishPicture() {
  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) {
    return;
  }

  JsonDocument doc; 

  // Encode to Base64
  String base64Image = base64::encode(fb->buf, fb->len);
  esp_camera_fb_return(fb); // Free memory

  doc["type"] = "motion";
  doc["image"] = base64Image;

  String jsonBuffer;
  serializeJson(doc, jsonBuffer);
 
  // Publish the entire payload at once
  bool success = client.publish(Topic.c_str(), jsonBuffer.c_str());
  
  if (success) {
    Serial.println("Image published successfully");
  } else {
    Serial.println("Failed to publish image");
  }
}

void setup(){
  Serial.begin(115200);
  pinMode(LEDPIN, OUTPUT);
  pinMode(PIRPIN, INPUT_PULLUP);
  // attach PIR interrupt
  attachInterrupt(digitalPinToInterrupt(PIRPIN), PIR_ISR, RISING);

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
 
  stage = (ssid != "" && password != "" && host != "" && HubID != "" && Topic != "") ? WIFI : PAIRING;
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
    if (client.connect("MOTION1"))
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
      if (status == "disconnect") {
        Serial.println("disconnect");
        preferences.clear();
        ESP.restart();
      }
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
        if (!initCamera()) { hard_reset(); }
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
      
      if (motionDetected) {
        publishPicture();
        digitalWrite(LEDPIN, HIGH);
        delay(1000);
        digitalWrite(LEDPIN, LOW);
        motionDetected = false;
        delay(100);
      }
      break;
  }
}

