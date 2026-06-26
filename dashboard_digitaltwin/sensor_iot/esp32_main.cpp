#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClient.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <HTTPClient.h>
#include <DHT.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include <mbedtls/md.h>
#include <mbedtls/base64.h>
#include <time.h>
#include <IRremoteESP8266.h>
#include <IRrecv.h>
#include <IRsend.h>
#include <IRutils.h>
#include <ir_Gree.h>

#ifdef __has_include
#if __has_include("secrets.h")
#include "secrets.h"
#endif
#endif

#ifndef WIFI_SSID
#define WIFI_SSID "CHANGE_ME_WIFI_SSID"
#endif

#ifndef WIFI_PASSWORD
#define WIFI_PASSWORD "CHANGE_ME_WIFI_PASSWORD"
#endif

#ifndef IOT_HUB_NAME
#define IOT_HUB_NAME "CHANGE_ME_IOT_HUB_NAME"
#endif

#ifndef IOT_DEVICE_ID
#define IOT_DEVICE_ID "CHANGE_ME_DEVICE_ID"
#endif

#ifndef IOT_DEVICE_KEY
#define IOT_DEVICE_KEY "CHANGE_ME_DEVICE_KEY"
#endif

#ifndef RPI_GATEWAY_URL
#define RPI_GATEWAY_URL "http://192.168.1.14:5001/api/collect"
#endif

#ifndef USE_RPI_GATEWAY
#define USE_RPI_GATEWAY 1  // 1 = Kirim ke RPi Gateway, 0 = skip
#endif

// ===== TINYML MODULE - Lightweight ML for ESP32 =====
// Implements: Moving Average, Anomaly Detection, Pattern Classification

// Moving Average Filter - Smooth noisy sensor readings
class MovingAverageFilter {
private:
  static const uint8_t BUFFER_SIZE = 10;
  float buffer[BUFFER_SIZE];
  uint8_t index;
  uint8_t count;
  float sum;

public:
  MovingAverageFilter() : index(0), count(0), sum(0) {
    for (uint8_t i = 0; i < BUFFER_SIZE; i++) {
      buffer[i] = 0.0f;
    }
  }

  float update(float value) {
    if (count > 0) {
      sum -= buffer[index];
    }
    buffer[index] = value;
    sum += value;
    index = (index + 1) % BUFFER_SIZE;
    if (count < BUFFER_SIZE) {
      count++;
    }
    return sum / static_cast<float>(count);
  }

  float getAverage() const {
    if (count == 0) return 0.0f;
    return sum / static_cast<float>(count);
  }

  void reset() {
    index = 0;
    count = 0;
    sum = 0;
    for (uint8_t i = 0; i < BUFFER_SIZE; i++) {
      buffer[i] = 0.0f;
    }
  }
};

// Anomaly Detection - Threshold-based anomaly detection
struct AnomalyResult {
  bool isAnomaly;
  float confidence;
  const char* reason;
};

class AnomalyDetector {
private:
  const float VOLTAGE_MIN = 180.0f;
  const float VOLTAGE_MAX = 250.0f;
  const float CURRENT_MAX = 15.0f;
  const float CURRENT_SPIKE = 5.0f;
  const float TEMP_MIN = 15.0f;
  const float TEMP_MAX = 45.0f;
  float prevVoltage;
  float prevCurrent;
  bool hasPrev;

public:
  AnomalyDetector() : prevVoltage(0.0f), prevCurrent(0.0f), hasPrev(false) {}

  AnomalyResult detect(float voltage, float current, float temperature) {
    AnomalyResult result = {false, 0.0f, "normal"};

    if (voltage > 0.0f) {
      if (voltage < VOLTAGE_MIN) {
        result.isAnomaly = true; result.confidence = 0.95f; result.reason = "voltage_low"; return result;
      }
      if (voltage > VOLTAGE_MAX) {
        result.isAnomaly = true; result.confidence = 0.95f; result.reason = "voltage_high"; return result;
      }
      if (hasPrev) {
        float voltageDelta = abs(voltage - prevVoltage);
        if (voltageDelta > 50.0f) {
          result.isAnomaly = true; result.confidence = 0.85f; result.reason = "voltage_spike"; return result;
        }
      }
    }

    if (current > CURRENT_MAX) {
      result.isAnomaly = true; result.confidence = 0.90f; result.reason = "current_high"; return result;
    }
    if (hasPrev && current > 0.0f) {
      float currentDelta = abs(current - prevCurrent);
      if (currentDelta > CURRENT_SPIKE) {
        result.isAnomaly = true; result.confidence = 0.80f; result.reason = "current_spike"; return result;
      }
    }

    if (!isnan(temperature)) {
      if (temperature < TEMP_MIN || temperature > TEMP_MAX) {
        result.isAnomaly = true; result.confidence = 0.75f; result.reason = "temperature_abnormal"; return result;
      }
    }

    result.isAnomaly = false; result.confidence = 1.0f; result.reason = "normal";
    return result;
  }

  void updateHistory(float voltage, float current) {
    prevVoltage = voltage; prevCurrent = current; hasPrev = true;
  }

  void reset() { hasPrev = false; }
};

// Power Usage Pattern Classifier
enum PowerMode { POWER_LIGHT, POWER_NORMAL, POWER_HEAVY, POWER_UNKNOWN };

class PowerClassifier {
private:
  const float THRESHOLD_LIGHT = 100.0f;
  const float THRESHOLD_HEAVY = 500.0f;

  float calculateConfidence(float power, float threshold, bool below) {
    float delta = abs(power - threshold);
    if (delta < 20.0f) return 0.70f;
    if (delta < 50.0f) return 0.85f;
    return 0.95f;
  }

public:
  PowerClassifier() {}

  PowerMode classify(float power) {
    if (power <= 0.0f) return POWER_UNKNOWN;
    if (power < THRESHOLD_LIGHT) return POWER_LIGHT;
    if (power > THRESHOLD_HEAVY) return POWER_HEAVY;
    return POWER_NORMAL;
  }

  const char* getModeLabel(PowerMode mode) {
    switch (mode) {
      case POWER_LIGHT: return "efficient";
      case POWER_NORMAL: return "moderate";
      case POWER_HEAVY: return "high";
      default: return "unknown";
    }
  }

  float getModeConfidence(float power, PowerMode mode) {
    switch (mode) {
      case POWER_LIGHT: return calculateConfidence(power, THRESHOLD_LIGHT, true);
      case POWER_NORMAL: return 0.90f;
      case POWER_HEAVY: return calculateConfidence(power, THRESHOLD_HEAVY, false);
      default: return 0.5f;
    }
  }
};

// TinyML Controller - manages all ML components
class TinyMLController {
public:
  MovingAverageFilter tempFilter;
  MovingAverageFilter humidityFilter;
  MovingAverageFilter voltageFilter;
  MovingAverageFilter currentFilter;
  MovingAverageFilter powerFilter;
  AnomalyDetector anomalyDetector;
  PowerClassifier powerClassifier;
  unsigned long lastInferenceUs;

  TinyMLController() : lastInferenceUs(0) {}

  void reset() {
    tempFilter.reset(); humidityFilter.reset(); voltageFilter.reset();
    currentFilter.reset(); powerFilter.reset(); anomalyDetector.reset();
    lastInferenceUs = 0;
  }
};

// Global TinyML instance
TinyMLController tinyml;

// ===== AZURE IoT Hub ROOT CERTIFICATE =====
// DigiCert Global Root G2 - Required for Azure IoT Hub TLS
const char* azure_root_ca = R"EOF(
-----BEGIN CERTIFICATE-----
MIIDjjCCAnagAwIBAgIQAzrx5qcRqaC7KGSxHQn65TANBgkqhkiG9w0BAQsFADBh
MQswCQYDVQQGEwJVUzEVMBMGA1UEChMMRGlnaUNlcnQgSW5jMRkwFwYDVQQLExB3
d3cuZGlnaWNlcnQuY29tMSAwHgYDVQQDExdEaWdpQ2VydCBHbG9iYWwgUm9vdCBH
MjAeFw0xMzA4MDExMjAwMDBaFw0zODAxMTUxMjAwMDBaMGExCzAJBgNVBAYTAlVT
MRUwEwYDVQQKEwxEaWdpQ2VydCBJbmMxGTAXBgNVBAsTEHd3dy5kaWdpY2VydC5j
b20xIDAeBgNVBAMTF0RpZ2lDZXJ0IEdsb2JhbCBSb290IEcyMIIBIjANBgkqhkiG
9w0BAQEFAAOCAQ8AMIIBCgKCAQEAuzfNNNx7a8myaJCtSnX/RrohCgiN9RlUyfuI
2/Ou8jqJkTx65qsGGmvPrC3oXgkkRLpimn7Wo6h+4FR1IAWsULecYxpsMNzaHxmx
1x7e/dfgy5SDN67sH0NO3Xss0r0upS/kqbitOtSZpLYl6ZtrAGCSYP9PIUkY92eQ
q2EGnI/yuum06ZIya7XzV+hdG82MHauVBJVJ8zUtluNJbd134/tJS7SsVQepj5Wz
tCO7TG1F8PapspUwtP1MVYwnSlcUfIKdzXOS0xZKBgyMUNGPHgm+F6HmIcr9g+UQ
vIOlCsRnKPZzFBQ9RnbDhxSJITRNrw9FDKZJobq7nMWxM4MphQIDAQABo0IwQDAP
BgNVHRMBAf8EBTADAQH/MA4GA1UdDwEB/wQEAwIBhjAdBgNVHQ4EFgQUTiJUIBiV
5uNu5g/6+rkS7QYXjzkwDQYJKoZIhvcNAQELBQADggEBAGBnKJRvDkhj6zHd6mcY
1Yl9PMCcit2BnLWsKjaSi2cEMoH0KVLJ8DP/vACgRqAeq0wDVnQHlPv+l3F5nGL6
ibHn/g9d7VoTvZ/gMZJedj7evkS6fLvNf/R3PG1kLCwLEomJMzBfOKx8TWSPXpLn
dS8ongPpfOPi4/fOHNBwPHAYw/TLKHDip3LyN3t/DAHI+QyH0EQNF7xR9HHQGP23
m0ao57w+czK/tz5WLnSH9wiWD18lPMPdmY+j3PCn93wdYdGU3GcLfoxJZ5Cb5FDk
tvALPBOjks61ihRdDLXgQy/wr+H+Km8RpFVXiJHH/t9DAggndkuYB8RgHny3DnGx
p1U=
-----END CERTIFICATE-----
)EOF";

// ===== KONFIGURASI WiFi =====
const char* ssid = WIFI_SSID;
const char* password = WIFI_PASSWORD;

// ===== KONFIGURASI AZURE IoT Hub =====
// Dapatkan nilai-nilai ini dari Azure Portal > IoT Hub > Devices
const char* iotHubName = IOT_HUB_NAME;        // Nama IoT Hub (tanpa .azure-devices.net)
const char* deviceId = IOT_DEVICE_ID;         // Device ID yang terdaftar di IoT Hub
const char* deviceKey = IOT_DEVICE_KEY;       // Primary Key device

// MQTT Configuration untuk Azure IoT Hub
String mqtt_server = String(iotHubName) + ".azure-devices.net";
const int mqtt_port = 8883;  // Port MQTT over TLS (wajib untuk Azure)
String mqtt_username = mqtt_server + "/" + String(deviceId) + "/?api-version=2021-04-12";
// Topic dengan properties: content-type = application/json
String mqtt_topic = "devices/" + String(deviceId) + "/messages/events/$.ct=application%2Fjson&$.ce=utf-8";
String mqtt_c2d_topic = "devices/" + String(deviceId) + "/messages/devicebound/#";

// ===== KONFIGURASI DHT11 =====
#define DHTPIN 14    // Pin data DHT11 terhubung ke GPIO 14
#define DHTTYPE DHT11     // Tipe sensor DHT11

// ===== KONFIGURASI IR CLOSED-LOOP AC =====
#define IR_TX_PIN 4
#define IR_RX_PIN 27
#define IR_CAPTURE_BUFFER_SIZE 1024
#define IR_CAPTURE_TIMEOUT_MS 50

// ===== SENSOR TEGANGAN ZMPT101B =====
// Pin: GPIO 34 (ADC1_CH6) - Kompatibel dengan WiFi
// Kalibrasi: 220V PLN Indonesia
#define ZMPT101B_PIN 34
#define ADC_BITS 12
#define ADC_COUNTS 4096       // 2^12 = 4096
#define VREF 3.3              // Tegangan referensi ESP32
#define VOLTAGE_CALIBRATION 660.0  // Faktor kalibrasi: target 220V PLN
#define RMS_THRESHOLD 0.15    // Threshold minimum RMS (filter noise) - turunkan dari 0.25
#define VOLTAGE_THRESHOLD 100.0  // Minimum tegangan valid - turunkan dari 150
#define VOLTAGE_MAX_VALID 300.0  // Maksimum tegangan valid (filter salah baca)

// ===== SENSOR ARUS SCT013-000 (100A/50mA) =====
// Pin: GPIO 32 (ADC1_CH4) - Kompatibel dengan WiFi
// Rangkaian: Merah->Resistor 1kΩ->GPIO32, Hitam->GND (tanpa bias)
#define SCT013_PIN 32
#define BURDEN_RESISTOR 1000.0    // 1kΩ burden resistor
#define CURRENT_CALIBRATION 300.0 // Faktor kalibrasi untuk burden 1kΩ
#define CURRENT_RMS_THRESHOLD 0.01  // Threshold minimum RMS arus
#define CURRENT_THRESHOLD_MIN 0.1   // Arus minimum (0.1A = ~22W)
#define DISABLE_CURRENT_SENSOR false

// Inisialisasi objek
DHT dht(DHTPIN, DHTTYPE);
IRsend irsend(IR_TX_PIN);
IRrecv irrecv(IR_RX_PIN, IR_CAPTURE_BUFFER_SIZE, IR_CAPTURE_TIMEOUT_MS, true);
decode_results irResults;
// Model Gree untuk GWC-09F5S: coba YBOFB dulu, lalu YAW1F, lalu YX1FSF.
// Parameter 3 (inverted): false = direct GPIO → LED (tanpa transistor)
//                          true  = jika pakai transistor NPN (sinyal terbalik)
//build_flag IR_INVERTED di platformio.ini mengaktifkan ini otomatis
// Ganti runtime via serial: ac-model yaw1f / ac-model ybofb / ac-model yx1fsf
#if IR_INVERTED
IRGreeAC greeAc(IR_TX_PIN, gree_ac_remote_model_t::YBOFB, true);
#else
IRGreeAC greeAc(IR_TX_PIN, gree_ac_remote_model_t::YBOFB, false);
#endif
WiFiClientSecure espClient;  // Gunakan WiFiClientSecure untuk TLS
PubSubClient client(espClient);
Preferences rawIrPrefs;
bool rawIrStorageReady = false;

// Variabel untuk SAS Token
String sasToken = "";
unsigned long sasTokenExpiry = 0;

// Variabel untuk timing
unsigned long lastMsg = 0;
const long interval = 5000; // Kirim data setiap 5 detik
const unsigned long SAS_TOKEN_REFRESH_WINDOW = 120; // Refresh 2 menit sebelum expiry

// Counter untuk statistik
unsigned long successCount = 0;
unsigned long failCount = 0;

const uint16_t IR_SEND_FREQUENCY_KHZ = 38;
const uint16_t IR_MAX_RAW_LENGTH = 600;
const unsigned long IR_SEND_COOLDOWN_MS = 1500;

const float DEFAULT_TARGET_TEMP_C = 24.0;
const float TEMP_HYSTERESIS_UP_C = 0.7;
const float TEMP_HYSTERESIS_DOWN_C = 0.4;
const unsigned long AC_COMMAND_COOLDOWN_MS = 90000;
const float HOT_START_THRESHOLD_C = 28.0;
const float FAN_MODE_MAX_HUMIDITY_PERCENT = 70.0;
const float FAN_MODE_MAX_FEELS_LIKE_MARGIN_C = 0.2;
const uint8_t RAW_COOL_PROFILE_MIN_C = kGreeMinTempC;
const uint8_t RAW_COOL_PROFILE_MAX_C = kGreeMaxTempC;

uint16_t lastIrRaw[IR_MAX_RAW_LENGTH];
uint16_t powerIrRaw[IR_MAX_RAW_LENGTH];
uint16_t offIrRaw[IR_MAX_RAW_LENGTH];
uint16_t fanIrRaw[IR_MAX_RAW_LENGTH];
uint16_t coolIrRaw[kGreeMaxTempC + 1][IR_MAX_RAW_LENGTH];
uint16_t lastIrRawLen = 0;
uint16_t powerIrRawLen = 0;
uint16_t offIrRawLen = 0;
uint16_t fanIrRawLen = 0;
uint16_t coolIrRawLen[kGreeMaxTempC + 1];
bool hasLastIrRaw = false;
bool hasPowerIrRaw = false;
bool hasOffIrRaw = false;
bool hasFanIrRaw = false;
bool hasCoolIrRaw[kGreeMaxTempC + 1];
unsigned long lastIrSendAt = 0;
String serialInputBuffer = "";
bool irCaptureEnabled = false;

bool closedLoopEnabled = true;
bool hasMlTargetTemp = false;
float mlTargetTempC = DEFAULT_TARGET_TEMP_C;
float effectiveTargetTempC = DEFAULT_TARGET_TEMP_C;
String targetSource = "default";

bool acPowerState = false;
uint8_t acModeState = kGreeCool;
uint8_t acFanState = kGreeFanAuto;
uint8_t acSetpointState = 24;

bool acDesiredPowerState = false;
uint8_t acDesiredModeState = kGreeCool;
uint8_t acDesiredFanState = kGreeFanAuto;
uint8_t acDesiredSetpointState = 24;

unsigned long lastAcCommandAt = 0;
String acLastReason = "startup";
float lastMeasuredTempC = NAN;
float lastMeasuredHumidityPercent = NAN;
float lastMeasuredHeatIndexC = NAN;
float lastControlTempC = NAN;
bool hasSensorSnapshot = false;
String closedLoopBand = "startup";

void setupWiFi();
void handleIrCapture();
void handleSerialInput();
void processSerialCommand(const String& rawCommand);
bool sendRawIrFrame(uint16_t* frame, uint16_t frameLen, uint8_t repeatCount, const char* label,
                    bool bypassCooldown = false);
void sendToRPiGateway(const char* jsonBuffer);
void mqttCallback(char* topic, byte* payload, unsigned int length);
void handleCloudControlMessage(const char* topic, const byte* payload, unsigned int length);
void printClosedLoopStatus();
uint8_t clampAcSetpoint(float tempC);
const char* acModeToLabel(uint8_t mode);
const char* acFanToLabel(uint8_t fan);
const char* acModelToLabel(gree_ac_remote_model_t model);
uint8_t modeFromString(const String& mode);
uint8_t fanFromString(const String& fan);
bool setAcModelFromString(const String& modelName);
bool hasPendingAcCommand();
void setDesiredAcState(bool powerOn, uint8_t mode, uint8_t fan, uint8_t setpoint, const char* reason);
bool sendAcCommandNow(bool powerOn, uint8_t mode, uint8_t fan, uint8_t setpoint, const char* reason, bool bypassCooldown);
bool flushPendingAcCommand();
bool persistRawProfile(const char* storageKey, const uint16_t* frame, uint16_t frameLen, bool available);
bool loadRawProfile(const char* storageKey, uint16_t* frame, uint16_t* frameLen, bool* availableFlag);
void loadStoredRawProfiles();
bool saveLastIrCapture(uint16_t* frame, uint16_t* frameLen, bool* availableFlag, const char* label,
                       const char* storageKey = nullptr);
uint8_t countCoolRawProfiles();
void printRawProfileSummary();
bool findBestCoolRawProfile(uint8_t requestedSetpoint, uint8_t* resolvedSetpoint);
bool trySendRawAcState(bool powerOn, uint8_t mode, uint8_t fan, uint8_t requestedSetpoint,
                       bool bypassCooldown, uint8_t* appliedMode, uint8_t* appliedSetpoint);
void setMlTargetTemp(float targetC, const char* source);
void clearMlTargetTemp();
float calculateControlTemperature(float suhuCelsius, float kelembaban, float* heatIndexC);
bool extractTargetTempFromPayload(const JsonDocument& doc, float* targetTempC);
void triggerClosedLoopRecheck(const char* source);
void applyClosedLoopControl(float suhuCelsius, float kelembaban);

String getIsoTimestampUTC() {
  time_t now = time(nullptr);
  struct tm timeInfo;

  if (!gmtime_r(&now, &timeInfo)) {
    return "";
  }

  char buffer[32];
  strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%SZ", &timeInfo);
  return String(buffer);
}

void setMlTargetTemp(float targetC, const char* source) {
  mlTargetTempC = constrain(targetC, static_cast<float>(kGreeMinTempC), static_cast<float>(kGreeMaxTempC));
  hasMlTargetTemp = true;
  effectiveTargetTempC = mlTargetTempC;
  targetSource = source;
}

void clearMlTargetTemp() {
  hasMlTargetTemp = false;
  effectiveTargetTempC = DEFAULT_TARGET_TEMP_C;
  targetSource = "default";
}

float calculateControlTemperature(float suhuCelsius, float kelembaban, float* heatIndexC) {
  float heatIndex = NAN;

  if (!isnan(suhuCelsius) && !isnan(kelembaban)) {
    heatIndex = dht.computeHeatIndex(suhuCelsius, kelembaban, false);
  }

  if (heatIndexC != nullptr) {
    *heatIndexC = heatIndex;
  }

  if (isnan(suhuCelsius)) {
    return NAN;
  }

  if (isnan(heatIndex)) {
    return suhuCelsius;
  }

  return heatIndex > suhuCelsius ? heatIndex : suhuCelsius;
}

bool extractTargetTempFromPayload(const JsonDocument& doc, float* targetTempC) {
  if (targetTempC == nullptr) {
    return false;
  }

  auto readTarget = [&](JsonVariantConst value) -> bool {
    if (value.is<float>() || value.is<double>() || value.is<int>() || value.is<long>() ||
        value.is<unsigned int>() || value.is<unsigned long>()) {
      *targetTempC = value.as<float>();
      return true;
    }
    if (value.is<const char*>()) {
      String text = value.as<String>();
      text.trim();
      if (text.length() == 0) {
        return false;
      }
      char firstChar = text.charAt(0);
      if (!(isDigit(firstChar) || firstChar == '-' || firstChar == '+')) {
        return false;
      }
      *targetTempC = text.toFloat();
      return true;
    }
    return false;
  };

  if (readTarget(doc["target_temp"]) ||
      readTarget(doc["recommended_temp"]) ||
      readTarget(doc["predicted_temp"]) ||
      readTarget(doc["recommendedTemp"])) {
    return true;
  }

  JsonVariantConst dataNode = doc["data"];
  if (dataNode.isNull()) {
    return false;
  }

  if (readTarget(dataNode["target_temp"]) ||
      readTarget(dataNode["recommended_temp"]) ||
      readTarget(dataNode["predicted_temp"]) ||
      readTarget(dataNode["recommendedTemp"])) {
    return true;
  }

  JsonVariantConst recommendationNode = dataNode["recommendation"];
  if (recommendationNode.isNull()) {
    return false;
  }

  return readTarget(recommendationNode["target_temp"]) ||
         readTarget(recommendationNode["recommended_temp"]) ||
         readTarget(recommendationNode["predicted_temp"]) ||
         readTarget(recommendationNode["recommendedTemp"]);
}

void triggerClosedLoopRecheck(const char* source) {
  if (!closedLoopEnabled || !hasSensorSnapshot || isnan(lastMeasuredTempC)) {
    return;
  }

  Serial.print("🔁 Re-evaluasi closed-loop dari snapshot sensor | source=");
  Serial.println(source);
  applyClosedLoopControl(lastMeasuredTempC, lastMeasuredHumidityPercent);
}

bool persistRawProfile(const char* storageKey, const uint16_t* frame, uint16_t frameLen, bool available) {
  if (!rawIrStorageReady || storageKey == nullptr || storageKey[0] == '\0') {
    return false;
  }

  char lenKey[16];
  char dataKey[16];
  snprintf(lenKey, sizeof(lenKey), "%s_l", storageKey);
  snprintf(dataKey, sizeof(dataKey), "%s_d", storageKey);

  if (!available || frame == nullptr || frameLen == 0) {
    rawIrPrefs.remove(lenKey);
    rawIrPrefs.remove(dataKey);
    return true;
  }

  rawIrPrefs.putUShort(lenKey, frameLen);
  size_t written = rawIrPrefs.putBytes(dataKey, frame, frameLen * sizeof(uint16_t));
  return written == (frameLen * sizeof(uint16_t));
}

bool loadRawProfile(const char* storageKey, uint16_t* frame, uint16_t* frameLen, bool* availableFlag) {
  if (!rawIrStorageReady || storageKey == nullptr || storageKey[0] == '\0' || frame == nullptr ||
      frameLen == nullptr || availableFlag == nullptr) {
    return false;
  }

  char lenKey[16];
  char dataKey[16];
  snprintf(lenKey, sizeof(lenKey), "%s_l", storageKey);
  snprintf(dataKey, sizeof(dataKey), "%s_d", storageKey);

  uint16_t storedLen = rawIrPrefs.getUShort(lenKey, 0);
  size_t storedBytes = rawIrPrefs.getBytesLength(dataKey);
  if (storedLen == 0 || storedBytes != storedLen * sizeof(uint16_t) || storedLen > IR_MAX_RAW_LENGTH) {
    *frameLen = 0;
    *availableFlag = false;
    return false;
  }

  size_t readBytes = rawIrPrefs.getBytes(dataKey, frame, storedLen * sizeof(uint16_t));
  if (readBytes != storedLen * sizeof(uint16_t)) {
    *frameLen = 0;
    *availableFlag = false;
    return false;
  }

  *frameLen = storedLen;
  *availableFlag = true;
  return true;
}

void loadStoredRawProfiles() {
  if (!rawIrStorageReady) {
    return;
  }

  loadRawProfile("power", powerIrRaw, &powerIrRawLen, &hasPowerIrRaw);
  loadRawProfile("off", offIrRaw, &offIrRawLen, &hasOffIrRaw);
  loadRawProfile("fan", fanIrRaw, &fanIrRawLen, &hasFanIrRaw);

  for (uint8_t setpoint = RAW_COOL_PROFILE_MIN_C; setpoint <= RAW_COOL_PROFILE_MAX_C; setpoint++) {
    char key[16];
    snprintf(key, sizeof(key), "cool_%u", setpoint);
    loadRawProfile(key, coolIrRaw[setpoint], &coolIrRawLen[setpoint], &hasCoolIrRaw[setpoint]);
  }
}

bool saveLastIrCapture(uint16_t* frame, uint16_t* frameLen, bool* availableFlag, const char* label,
                       const char* storageKey) {
  if (!hasLastIrRaw || lastIrRawLen == 0) {
    Serial.println("⚠️ Belum ada capture IR. Tekan tombol remote dulu.");
    return false;
  }

  if (frame == nullptr || frameLen == nullptr || availableFlag == nullptr) {
    Serial.println("⚠️ Profil IR tidak valid.");
    return false;
  }

  for (uint16_t i = 0; i < lastIrRawLen; i++) {
    frame[i] = lastIrRaw[i];
  }
  *frameLen = lastIrRawLen;
  *availableFlag = true;

  Serial.print("💾 Profil IR tersimpan: ");
  Serial.print(label);
  Serial.print(" | raw length=");
  Serial.println(*frameLen);

  if (storageKey != nullptr) {
    bool persisted = persistRawProfile(storageKey, frame, *frameLen, *availableFlag);
    Serial.print("   Flash save: ");
    Serial.println(persisted ? "ok" : "gagal");
  }
  return true;
}

uint8_t countCoolRawProfiles() {
  uint8_t count = 0;
  for (uint8_t setpoint = RAW_COOL_PROFILE_MIN_C; setpoint <= RAW_COOL_PROFILE_MAX_C; setpoint++) {
    if (hasCoolIrRaw[setpoint] && coolIrRawLen[setpoint] > 0) {
      count++;
    }
  }
  return count;
}

void printRawProfileSummary() {
  Serial.println("Raw IR profiles:");
  Serial.print("  off: ");
  Serial.println(hasOffIrRaw ? "ready" : "empty");
  Serial.print("  fan: ");
  Serial.println(hasFanIrRaw ? "ready" : "empty");
  Serial.print("  cool count: ");
  Serial.println(countCoolRawProfiles());
  Serial.print("  cool setpoints: ");

  bool first = true;
  for (uint8_t setpoint = RAW_COOL_PROFILE_MIN_C; setpoint <= RAW_COOL_PROFILE_MAX_C; setpoint++) {
    if (!hasCoolIrRaw[setpoint] || coolIrRawLen[setpoint] == 0) {
      continue;
    }

    if (!first) {
      Serial.print(", ");
    }
    Serial.print(setpoint);
    first = false;
  }

  if (first) {
    Serial.print("-");
  }
  Serial.println();
}

bool findBestCoolRawProfile(uint8_t requestedSetpoint, uint8_t* resolvedSetpoint) {
  if (resolvedSetpoint == nullptr) {
    return false;
  }

  requestedSetpoint = clampAcSetpoint(requestedSetpoint);
  int bestDiff = 100;
  bool found = false;

  for (uint8_t setpoint = RAW_COOL_PROFILE_MIN_C; setpoint <= RAW_COOL_PROFILE_MAX_C; setpoint++) {
    if (!hasCoolIrRaw[setpoint] || coolIrRawLen[setpoint] == 0) {
      continue;
    }

    int diff = abs(static_cast<int>(setpoint) - static_cast<int>(requestedSetpoint));
    if (!found || diff < bestDiff) {
      *resolvedSetpoint = setpoint;
      bestDiff = diff;
      found = true;
    }
  }

  return found;
}

bool trySendRawAcState(bool powerOn, uint8_t mode, uint8_t fan, uint8_t requestedSetpoint,
                       bool bypassCooldown, uint8_t* appliedMode, uint8_t* appliedSetpoint) {
  (void)fan;

  if (appliedMode != nullptr) {
    *appliedMode = mode;
  }
  if (appliedSetpoint != nullptr) {
    *appliedSetpoint = requestedSetpoint;
  }

  if (!powerOn) {
    if (!hasOffIrRaw || offIrRawLen == 0) {
      return false;
    }
    return sendRawIrFrame(offIrRaw, offIrRawLen, 1, "off", bypassCooldown);
  }

  if (mode == kGreeFan) {
    if (!hasFanIrRaw || fanIrRawLen == 0) {
      return false;
    }
    return sendRawIrFrame(fanIrRaw, fanIrRawLen, 1, "fan", bypassCooldown);
  }

  if (mode != kGreeCool) {
    return false;
  }

  uint8_t resolvedSetpoint = requestedSetpoint;
  if (!findBestCoolRawProfile(requestedSetpoint, &resolvedSetpoint)) {
    return false;
  }

  char label[16];
  snprintf(label, sizeof(label), "cool-%u", resolvedSetpoint);
  bool sent = sendRawIrFrame(coolIrRaw[resolvedSetpoint], coolIrRawLen[resolvedSetpoint], 1,
                             label, bypassCooldown);

  if (!sent) {
    return false;
  }

  if (appliedMode != nullptr) {
    *appliedMode = kGreeCool;
  }
  if (appliedSetpoint != nullptr) {
    *appliedSetpoint = resolvedSetpoint;
  }
  return true;
}

void ensureWiFiConnected() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }

  Serial.println("\n⚠️ WiFi terputus, mencoba konek ulang...");
  WiFi.disconnect(true, true);
  delay(250);
  setupWiFi();
}

bool sendRawIrFrame(uint16_t* frame, uint16_t frameLen, uint8_t repeatCount, const char* label,
                    bool bypassCooldown) {
  if (frame == nullptr || frameLen == 0) {
    Serial.println("⚠️ Frame IR kosong, tidak ada data untuk dikirim.");
    return false;
  }

  unsigned long now = millis();
  if (!bypassCooldown && now - lastIrSendAt < IR_SEND_COOLDOWN_MS) {
    unsigned long waitMs = IR_SEND_COOLDOWN_MS - (now - lastIrSendAt);
    Serial.print("⏳ Tunggu ");
    Serial.print(waitMs);
    Serial.println(" ms sebelum kirim IR berikutnya.");
    return false;
  }

  if (repeatCount == 0) {
    repeatCount = 1;
  }

  // Matikan receiver sementara untuk menghindari self-capture dan timer conflict
  irrecv.disableIRIn();
  delay(5);

  for (uint8_t i = 0; i < repeatCount; i++) {
    irsend.sendRaw(frame, frameLen, IR_SEND_FREQUENCY_KHZ);
    delay(80);
  }

  // Nyalakan kembali receiver setelah selesai kirim
  delay(20);
  irrecv.enableIRIn();

  lastIrSendAt = millis();
  Serial.print("✅ IR terkirim (");
  Serial.print(label);
  Serial.print(") | raw length=");
  Serial.print(frameLen);
  Serial.print(" | repeat=");
  Serial.println(repeatCount);
  return true;
}

void processSerialCommand(const String& rawCommand) {
  String command = rawCommand;
  command.trim();
  command.toLowerCase();

  if (command.length() == 0) {
    return;
  }

  if (command == "ir-help") {
    Serial.println("Perintah IR & Closed-loop:");
    Serial.println("  ir-help         -> tampilkan daftar perintah");
    Serial.println("  ir-save-power   -> simpan capture terakhir jadi tombol POWER");
    Serial.println("  ir-save-off     -> simpan capture OFF asli dari remote");
    Serial.println("  ir-save-fan     -> simpan capture ON + FAN asli dari remote");
    Serial.println("  ir-save-cool 24 -> simpan capture ON + COOL setpoint tertentu");
    Serial.println("  ir-send-last    -> kirim ulang capture terakhir");
    Serial.println("  ir-send-power   -> kirim ulang frame POWER yang tersimpan");
    Serial.println("  ir-send-off     -> kirim profil OFF raw");
    Serial.println("  ir-send-fan     -> kirim profil FAN raw");
    Serial.println("  ir-send-cool 24 -> kirim profil COOL raw");
    Serial.println("  ir-list         -> tampilkan daftar profil raw tersimpan");
    Serial.println("  ir-capture-on   -> aktifkan mode capture KY-022");
    Serial.println("  ir-capture-off  -> nonaktifkan mode capture KY-022");
    Serial.println("  cl-enable       -> aktifkan closed-loop otomatis");
    Serial.println("  cl-disable      -> nonaktifkan closed-loop otomatis");
    Serial.println("  cl-status       -> tampilkan status closed-loop");
    Serial.println("  cl-target 24.0  -> set target suhu dari simulasi ML");
    Serial.println("  cl-clear-target -> hapus target ML, pakai default");
    Serial.println("  tinyml-status   -> tampilkan status TinyML (filter, anomaly)");
    Serial.println("  tinyml-reset    -> reset semua filter dan detector");
    Serial.println("  ac-resend       -> kirim ulang state AC sekarang (bypass cooldown)");
    Serial.println("  ac-test-cool 24 -> kirim COOL via raw profile");
    Serial.println("  ac-test-lib 24  -> kirim COOL via library langsung");
    Serial.println("  ir-test-led     -> test LED IR blink (pakai kamera HP lihat)");
    Serial.println("  ir-gpio-test    -> test GPIO4 on/off (ukur multimeter)");
    Serial.println("  ir-direct-test  -> test kirim pattern raw via irsend");
    Serial.println("  led-on          -> test GPIO4 langsung HIGH");
    Serial.println("  led-off         -> test GPIO4 langsung LOW");
    return;
  }

  if (command == "cl-enable") {
    closedLoopEnabled = true;
    Serial.println("✅ Closed-loop diaktifkan.");
    triggerClosedLoopRecheck("serial_cl_enable");
    return;
  }

  if (command == "cl-disable") {
    closedLoopEnabled = false;
    Serial.println("⏸️ Closed-loop dinonaktifkan.");
    return;
  }

  if (command == "cl-status") {
    printClosedLoopStatus();
    return;
  }

  if (command.startsWith("cl-target ")) {
    String value = command.substring(String("cl-target ").length());
    float target = value.toFloat();
    if (target < kGreeMinTempC || target > kGreeMaxTempC) {
      Serial.print("⚠️ Target harus di rentang ");
      Serial.print(kGreeMinTempC);
      Serial.print("-");
      Serial.print(kGreeMaxTempC);
      Serial.println(" C");
      return;
    }

    setMlTargetTemp(target, "ml");
    Serial.print("🎯 Target ML diset ke ");
    Serial.print(mlTargetTempC, 1);
    Serial.println(" C");
    triggerClosedLoopRecheck("serial_cl_target");
    return;
  }

  if (command == "cl-clear-target") {
    clearMlTargetTemp();
    Serial.println("♻️ Target ML dihapus, kembali ke target default.");
    triggerClosedLoopRecheck("serial_cl_clear_target");
    return;
  }

  // TinyML commands
  if (command == "tinyml-status") {
    Serial.println("TinyML Status:");
    Serial.print("  Inference time: ");
    Serial.print(tinyml.lastInferenceUs);
    Serial.println(" us");
    Serial.print("  Temp filter avg: ");
    Serial.print(tinyml.tempFilter.getAverage(), 2);
    Serial.println(" C");
    Serial.print("  Voltage filter avg: ");
    Serial.print(tinyml.voltageFilter.getAverage(), 2);
    Serial.println(" V");
    Serial.print("  Power filter avg: ");
    Serial.print(tinyml.powerFilter.getAverage(), 2);
    Serial.println(" W");
    return;
  }

  if (command == "tinyml-reset") {
    tinyml.reset();
    Serial.println("✅ TinyML filters and anomaly detector reset.");
    return;
  }

  if (command == "ac-off") {
    setDesiredAcState(false, acDesiredModeState, acDesiredFanState, acDesiredSetpointState, "manual_ac_off");
    flushPendingAcCommand();
    return;
  }

  if (command == "ac-resend") {
    setDesiredAcState(acDesiredPowerState, acDesiredModeState, acDesiredFanState, acDesiredSetpointState, "manual_resend");
    sendAcCommandNow(acDesiredPowerState, acDesiredModeState, acDesiredFanState, acDesiredSetpointState, acLastReason.c_str(), true);
    return;
  }

  if (command.startsWith("ac-test-cool")) {
    String value = command.substring(String("ac-test-cool").length());
    value.trim();
    uint8_t setpoint = acDesiredSetpointState;
    if (value.length() > 0) {
      setpoint = clampAcSetpoint(value.toFloat());
    }
    setDesiredAcState(true, kGreeCool, kGreeFanAuto, setpoint, "manual_test_cool");
    sendAcCommandNow(acDesiredPowerState, acDesiredModeState, acDesiredFanState, acDesiredSetpointState, acLastReason.c_str(), true);
    return;
  }

  // Test kirim via library GreeAC (bypass raw profiles)
  if (command.startsWith("ac-test-lib")) {
    String value = command.substring(String("ac-test-lib").length());
    value.trim();
    uint8_t setpoint = 24;
    if (value.length() > 0) {
      setpoint = clampAcSetpoint(value.toFloat());
    }
    Serial.println("IR library direct test...");
    irrecv.disableIRIn();
    delay(5);
    greeAc.setPower(true);
    greeAc.setMode(kGreeCool);
    greeAc.setFan(kGreeFanAuto);
    greeAc.setTemp(setpoint);
    greeAc.setSwingVertical(true, kGreeSwingAuto);
    greeAc.send(kGreeDefaultRepeat + 1);
    delay(20);
    irrecv.enableIRIn();
    Serial.print("✅ Library IR terkirim");
    Serial.print(" | model=");
    Serial.print(acModelToLabel(greeAc.getModel()));
    Serial.print(" | temp=");
    Serial.print(setpoint);
    Serial.println("C");
    return;
  }

  if (command.startsWith("ac-model ")) {
    String value = command.substring(String("ac-model ").length());
    value.trim();
    value.toLowerCase();
    if (!setAcModelFromString(value)) {
      Serial.println("⚠️ Model tidak dikenali. Pilih: yaw1f | ybofb | yx1fsf");
      return;
    }

    Serial.print("✅ Model remote Gree diset ke ");
    Serial.println(acModelToLabel(greeAc.getModel()));
    return;
  }

  if (command == "ir-capture-on") {
    irCaptureEnabled = true;
    Serial.println("✅ IR capture aktif.");
    return;
  }

  if (command == "ir-capture-off") {
    irCaptureEnabled = false;
    Serial.println("⏸️ IR capture nonaktif.");
    return;
  }

  if (command == "ir-test-led") {
    Serial.println("🔴 Test LED IR blink 3x...");
    irrecv.disableIRIn();
    delay(5);
    uint16_t blinkPattern[] = {500, 500, 500, 500, 500, 500};
    for (int i = 0; i < 3; i++) {
      irsend.sendRaw(blinkPattern, 6, 38);
      delay(200);
    }
    delay(20);
    irrecv.enableIRIn();
    Serial.println("✅ Selesai. Lihat LED dengan kamera HP.");
    return;
  }

  if (command == "ir-gpio-test") {
    Serial.print("🔌 Test GPIO");
    Serial.print(IR_TX_PIN);
    Serial.println(" ON/OFF...");
    irrecv.disableIRIn();
    pinMode(IR_TX_PIN, OUTPUT);
    digitalWrite(IR_TX_PIN, HIGH);
    delay(1000);
    Serial.println("   HIGH 1 detik - ukur multimeter");
    digitalWrite(IR_TX_PIN, LOW);
    delay(1000);
    Serial.println("   LOW 1 detik - ukur multimeter");
    irrecv.enableIRIn();
    Serial.println("✅ Selesai. Cek voltage GPIO4.");
    return;
  }

  if (command == "led-on") {
    irrecv.disableIRIn();
    pinMode(IR_TX_PIN, OUTPUT);
    digitalWrite(IR_TX_PIN, HIGH);
    Serial.println("✅ GPIO4 HIGH");
    irrecv.enableIRIn();
    return;
  }

  if (command == "led-off") {
    irrecv.disableIRIn();
    pinMode(IR_TX_PIN, OUTPUT);
    digitalWrite(IR_TX_PIN, LOW);
    Serial.println("✅ GPIO4 LOW");
    irrecv.enableIRIn();
    return;
  }

  if (command == "ir-direct-test") {
    Serial.println("📡 Test kirim pattern raw langsung...");
    irrecv.disableIRIn();
    uint16_t testPattern[] = {9000, 4500, 500, 1500, 500, 1500, 500, 500};
    irsend.sendRaw(testPattern, 8, 38);
    delay(100);
    irrecv.enableIRIn();
    Serial.println("✅ Pattern terkirim");
    return;
  }

  if (command == "ir-save-power") {
    saveLastIrCapture(powerIrRaw, &powerIrRawLen, &hasPowerIrRaw, "power", "power");
    return;
  }

  if (command == "ir-save-off") {
    saveLastIrCapture(offIrRaw, &offIrRawLen, &hasOffIrRaw, "off", "off");
    return;
  }

  if (command == "ir-save-fan") {
    saveLastIrCapture(fanIrRaw, &fanIrRawLen, &hasFanIrRaw, "fan", "fan");
    return;
  }

  if (command.startsWith("ir-save-cool ")) {
    String value = command.substring(String("ir-save-cool ").length());
    value.trim();
    int setpoint = value.toInt();
    if (setpoint < RAW_COOL_PROFILE_MIN_C || setpoint > RAW_COOL_PROFILE_MAX_C) {
      Serial.print("⚠️ Setpoint COOL harus di rentang ");
      Serial.print(RAW_COOL_PROFILE_MIN_C);
      Serial.print("-");
      Serial.print(RAW_COOL_PROFILE_MAX_C);
      Serial.println(" C");
      return;
    }
    char label[16];
    snprintf(label, sizeof(label), "cool-%d", setpoint);
    char storageKey[16];
    snprintf(storageKey, sizeof(storageKey), "cool_%d", setpoint);
    saveLastIrCapture(coolIrRaw[setpoint], &coolIrRawLen[setpoint], &hasCoolIrRaw[setpoint],
                      label, storageKey);
    return;
  }

  if (command == "ir-send-last") {
    if (!hasLastIrRaw || lastIrRawLen == 0) {
      Serial.println("⚠️ Tidak ada capture terakhir untuk dikirim.");
      return;
    }
    sendRawIrFrame(lastIrRaw, lastIrRawLen, 1, "last");
    return;
  }

  if (command == "ir-send-power") {
    if (!hasPowerIrRaw || powerIrRawLen == 0) {
      Serial.println("⚠️ Belum ada frame POWER. Jalankan ir-save-power setelah capture.");
      return;
    }
    sendRawIrFrame(powerIrRaw, powerIrRawLen, 1, "power");
    return;
  }

  if (command == "ir-send-off") {
    if (!hasOffIrRaw || offIrRawLen == 0) {
      Serial.println("⚠️ Belum ada profil OFF raw.");
      return;
    }
    sendRawIrFrame(offIrRaw, offIrRawLen, 1, "off", true);
    return;
  }

  if (command == "ir-send-fan") {
    if (!hasFanIrRaw || fanIrRawLen == 0) {
      Serial.println("⚠️ Belum ada profil FAN raw.");
      return;
    }
    sendRawIrFrame(fanIrRaw, fanIrRawLen, 1, "fan", true);
    return;
  }

  if (command.startsWith("ir-send-cool ")) {
    String value = command.substring(String("ir-send-cool ").length());
    value.trim();
    int setpoint = value.toInt();
    if (setpoint < RAW_COOL_PROFILE_MIN_C || setpoint > RAW_COOL_PROFILE_MAX_C) {
      Serial.print("⚠️ Setpoint COOL harus di rentang ");
      Serial.print(RAW_COOL_PROFILE_MIN_C);
      Serial.print("-");
      Serial.print(RAW_COOL_PROFILE_MAX_C);
      Serial.println(" C");
      return;
    }
    if (!hasCoolIrRaw[setpoint] || coolIrRawLen[setpoint] == 0) {
      Serial.println("⚠️ Belum ada profil COOL raw untuk setpoint itu.");
      return;
    }
    char label[16];
    snprintf(label, sizeof(label), "cool-%d", setpoint);
    sendRawIrFrame(coolIrRaw[setpoint], coolIrRawLen[setpoint], 1, label, true);
    return;
  }

  if (command == "ir-list") {
    printRawProfileSummary();
    return;
  }

  Serial.print("⚠️ Perintah tidak dikenal: ");
  Serial.println(command);
  Serial.println("   Ketik ir-help untuk melihat daftar perintah.");
}

void handleSerialInput() {
  while (Serial.available() > 0) {
    char c = static_cast<char>(Serial.read());

    if (c == '\r') {
      continue;
    }

    if (c == '\n') {
      processSerialCommand(serialInputBuffer);
      serialInputBuffer = "";
      continue;
    }

    if (serialInputBuffer.length() < 96) {
      serialInputBuffer += c;
    }
  }
}

void handleIrCapture() {
  if (!irCaptureEnabled) {
    return;
  }

  if (!irrecv.decode(&irResults)) {
    return;
  }

  if (irResults.rawlen > 1) {
    uint16_t usableLen = irResults.rawlen - 1;
    if (usableLen > IR_MAX_RAW_LENGTH) {
      usableLen = IR_MAX_RAW_LENGTH;
    }

    for (uint16_t i = 0; i < usableLen; i++) {
      uint32_t rawMicros = irResults.rawbuf[i + 1] * kRawTick;
      if (rawMicros > 65535) {
        rawMicros = 65535;
      }
      lastIrRaw[i] = static_cast<uint16_t>(rawMicros);
    }

    lastIrRawLen = usableLen;
    hasLastIrRaw = true;
  }

  Serial.println("\n📥 IR tertangkap dari remote AC:");
  Serial.println(resultToHumanReadableBasic(&irResults));
  Serial.println(resultToSourceCode(&irResults));

  if (irResults.rawlen > IR_MAX_RAW_LENGTH + 1) {
    Serial.print("⚠️ Raw IR dipotong ke ");
    Serial.print(IR_MAX_RAW_LENGTH);
    Serial.println(" sample karena batas buffer.");
  }

  Serial.println("Perintah cepat: ir-save-off | ir-save-fan | ir-save-cool 24 | ir-list | ir-help");
  irrecv.resume();
}

const char* acModeToLabel(uint8_t mode) {
  switch (mode) {
    case kGreeCool:
      return "cool";
    case kGreeFan:
      return "fan";
    case kGreeDry:
      return "dry";
    case kGreeHeat:
      return "heat";
    case kGreeAuto:
      return "auto";
    default:
      return "unknown";
  }
}

const char* acFanToLabel(uint8_t fan) {
  switch (fan) {
    case kGreeFanAuto:
      return "auto";
    case kGreeFanMin:
      return "min";
    case kGreeFanMed:
      return "med";
    case kGreeFanMax:
      return "max";
    default:
      return "unknown";
  }
}

const char* acModelToLabel(gree_ac_remote_model_t model) {
  switch (model) {
    case gree_ac_remote_model_t::YAW1F:
      return "yaw1f";
    case gree_ac_remote_model_t::YBOFB:
      return "ybofb";
    case gree_ac_remote_model_t::YX1FSF:
      return "yx1fsf";
    default:
      return "unknown";
  }
}

uint8_t clampAcSetpoint(float tempC) {
  if (tempC < kGreeMinTempC) {
    return kGreeMinTempC;
  }
  if (tempC > kGreeMaxTempC) {
    return kGreeMaxTempC;
  }
  return static_cast<uint8_t>(round(tempC));
}

uint8_t modeFromString(const String& mode) {
  if (mode == "cool") return kGreeCool;
  if (mode == "fan") return kGreeFan;
  if (mode == "dry") return kGreeDry;
  if (mode == "heat") return kGreeHeat;
  if (mode == "auto") return kGreeAuto;
  return acDesiredModeState;
}

uint8_t fanFromString(const String& fan) {
  if (fan == "auto") return kGreeFanAuto;
  if (fan == "min" || fan == "low") return kGreeFanMin;
  if (fan == "med" || fan == "medium") return kGreeFanMed;
  if (fan == "max" || fan == "high") return kGreeFanMax;
  return acDesiredFanState;
}

bool setAcModelFromString(const String& modelName) {
  if (modelName == "yaw1f") {
    greeAc.setModel(gree_ac_remote_model_t::YAW1F);
    return true;
  }
  if (modelName == "ybofb") {
    greeAc.setModel(gree_ac_remote_model_t::YBOFB);
    return true;
  }
  if (modelName == "yx1fsf" || modelName == "yx1f2f") {
    greeAc.setModel(gree_ac_remote_model_t::YX1FSF);
    return true;
  }
  return false;
}

bool hasPendingAcCommand() {
  return acDesiredPowerState != acPowerState ||
         acDesiredModeState != acModeState ||
         acDesiredFanState != acFanState ||
         acDesiredSetpointState != acSetpointState;
}

void setDesiredAcState(bool powerOn, uint8_t mode, uint8_t fan, uint8_t setpoint, const char* reason) {
  acDesiredPowerState = powerOn;
  acDesiredModeState = mode;
  acDesiredFanState = fan;
  acDesiredSetpointState = setpoint;
  acLastReason = reason;
}

bool sendAcCommandNow(bool powerOn, uint8_t mode, uint8_t fan, uint8_t setpoint, const char* reason, bool bypassCooldown) {
  unsigned long now = millis();
  bool powerOffTransition = (!powerOn && acPowerState);
  if (!bypassCooldown && !powerOffTransition && (now - lastAcCommandAt < AC_COMMAND_COOLDOWN_MS)) {
    return false;
  }
  if (!bypassCooldown && (now - lastIrSendAt < IR_SEND_COOLDOWN_MS)) {
    return false;
  }

  uint8_t appliedMode = mode;
  uint8_t appliedSetpoint = setpoint;
  bool sent = trySendRawAcState(powerOn, mode, fan, setpoint, bypassCooldown, &appliedMode, &appliedSetpoint);

  if (!sent) {
    // Matikan receiver sementara untuk menghindari self-capture dan timer conflict
    irrecv.disableIRIn();
    delay(5);

    greeAc.setPower(powerOn);
    greeAc.setMode(mode);
    greeAc.setFan(fan);
    greeAc.setTemp(setpoint);
    greeAc.setSwingVertical(true, kGreeSwingAuto);
    greeAc.send(kGreeDefaultRepeat + 1);

    // Nyalakan kembali receiver setelah selesai kirim
    delay(20);
    irrecv.enableIRIn();

    lastIrSendAt = millis();
    appliedMode = mode;
    appliedSetpoint = setpoint;
  }

  acPowerState = powerOn;
  acModeState = appliedMode;
  acFanState = fan;
  acSetpointState = appliedSetpoint;
  acDesiredPowerState = powerOn;
  acDesiredModeState = appliedMode;
  acDesiredFanState = fan;
  acDesiredSetpointState = appliedSetpoint;
  acLastReason = reason;
  lastAcCommandAt = millis();

  Serial.print("🤖 AC command terkirim | power=");
  Serial.print(acPowerState ? "on" : "off");
  Serial.print(" | mode=");
  Serial.print(acModeToLabel(acModeState));
  Serial.print(" | fan=");
  Serial.print(acFanToLabel(acFanState));
  Serial.print(" | setpoint=");
  Serial.print(acSetpointState);
  Serial.print("C | reason=");
  Serial.println(acLastReason);

  return true;
}

bool flushPendingAcCommand() {
  if (!hasPendingAcCommand()) {
    return false;
  }

  return sendAcCommandNow(acDesiredPowerState, acDesiredModeState, acDesiredFanState,
                          acDesiredSetpointState, acLastReason.c_str(), false);
}

void printClosedLoopStatus() {
  Serial.println("Closed-loop status:");
  Serial.print("  enabled: ");
  Serial.println(closedLoopEnabled ? "true" : "false");
  Serial.print("  target source: ");
  Serial.println(targetSource);
  Serial.print("  target temp: ");
  Serial.print(effectiveTargetTempC, 1);
  Serial.println(" C");
  Serial.print("  control band: ");
  Serial.println(closedLoopBand);
  Serial.print("  AC power: ");
  Serial.println(acPowerState ? "on" : "off");
  Serial.print("  AC mode: ");
  Serial.println(acModeToLabel(acModeState));
  Serial.print("  AC fan: ");
  Serial.println(acFanToLabel(acFanState));
  Serial.print("  AC model: ");
  Serial.println(acModelToLabel(greeAc.getModel()));
  Serial.print("  AC setpoint: ");
  Serial.print(acSetpointState);
  Serial.println(" C");
  Serial.print("  Last reason: ");
  Serial.println(acLastReason);
  Serial.print("  Pending command: ");
  Serial.println(hasPendingAcCommand() ? "yes" : "no");
  if (hasSensorSnapshot) {
    Serial.print("  Last room temp: ");
    Serial.print(lastMeasuredTempC, 1);
    Serial.println(" C");
    Serial.print("  Last humidity: ");
    Serial.print(lastMeasuredHumidityPercent, 1);
    Serial.println(" %");
    if (!isnan(lastMeasuredHeatIndexC)) {
      Serial.print("  Heat index: ");
      Serial.print(lastMeasuredHeatIndexC, 1);
      Serial.println(" C");
    }
    Serial.print("  Control temp: ");
    Serial.print(lastControlTempC, 1);
    Serial.println(" C");
  }
  printRawProfileSummary();
}

void handleCloudControlMessage(const char* topic, const byte* payload, unsigned int length) {
  (void)topic;

  const size_t maxPayload = 511;
  size_t copyLen = length < maxPayload ? length : maxPayload;
  char message[512];
  memcpy(message, payload, copyLen);
  message[copyLen] = '\0';

  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, message);
  if (err) {
    String raw = String(message);
    raw.trim();
    raw.toLowerCase();

    if (raw == "cl-enable") {
      closedLoopEnabled = true;
      Serial.println("📥 Cloud command: closed-loop enabled");
      triggerClosedLoopRecheck("cloud_cl_enable");
      return;
    }
    if (raw == "cl-disable") {
      closedLoopEnabled = false;
      Serial.println("📥 Cloud command: closed-loop disabled");
      return;
    }

    Serial.println("⚠️ Payload cloud tidak valid JSON dan tidak dikenali.");
    return;
  }

  bool hasDirectAcState = false;
  bool applyNow = false;

  bool desiredPower = acDesiredPowerState;
  uint8_t desiredMode = acDesiredModeState;
  uint8_t desiredFan = acDesiredFanState;
  uint8_t desiredSetpoint = acDesiredSetpointState;

  if (doc["closed_loop_enabled"].is<bool>()) {
    closedLoopEnabled = doc["closed_loop_enabled"].as<bool>();
  }

  float targetCandidate = NAN;
  if (extractTargetTempFromPayload(doc, &targetCandidate)) {
    setMlTargetTemp(targetCandidate, "ml");
  }

  if (doc["clear_ml_target"].is<bool>() && doc["clear_ml_target"].as<bool>()) {
    clearMlTargetTemp();
  }

  if (doc["power"].is<bool>()) {
    desiredPower = doc["power"].as<bool>();
    hasDirectAcState = true;
  }

  if (doc["mode"].is<const char*>()) {
    String mode = doc["mode"].as<String>();
    mode.toLowerCase();
    desiredMode = modeFromString(mode);
    hasDirectAcState = true;
  }

  if (doc["fan"].is<const char*>()) {
    String fan = doc["fan"].as<String>();
    fan.toLowerCase();
    desiredFan = fanFromString(fan);
    hasDirectAcState = true;
  }

  if (doc["setpoint_temp"].is<float>() || doc["setpoint_temp"].is<int>()) {
    desiredSetpoint = clampAcSetpoint(doc["setpoint_temp"].as<float>());
    hasDirectAcState = true;
  } else if (doc["setpoint"].is<float>() || doc["setpoint"].is<int>()) {
    desiredSetpoint = clampAcSetpoint(doc["setpoint"].as<float>());
    hasDirectAcState = true;
  }

  if (doc["apply_now"].is<bool>()) {
    applyNow = doc["apply_now"].as<bool>();
  }

  if (hasDirectAcState) {
    setDesiredAcState(desiredPower, desiredMode, desiredFan, desiredSetpoint, "cloud_command");
  }

  if (applyNow) {
    flushPendingAcCommand();
  } else if (!hasDirectAcState && (closedLoopEnabled || !isnan(targetCandidate))) {
    triggerClosedLoopRecheck("cloud_ml_update");
  }

  printClosedLoopStatus();
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  Serial.print("\n📩 C2D command diterima dari topic: ");
  Serial.println(topic);
  handleCloudControlMessage(topic, payload, length);
}

void applyClosedLoopControl(float suhuCelsius, float kelembaban) {
  lastMeasuredTempC = suhuCelsius;
  lastMeasuredHumidityPercent = kelembaban;
  lastControlTempC = calculateControlTemperature(suhuCelsius, kelembaban, &lastMeasuredHeatIndexC);
  hasSensorSnapshot = !isnan(suhuCelsius);

  if (hasMlTargetTemp) {
    effectiveTargetTempC = mlTargetTempC;
    targetSource = "ml";
  } else {
    effectiveTargetTempC = DEFAULT_TARGET_TEMP_C;
    targetSource = "default";
  }

  if (!closedLoopEnabled || isnan(suhuCelsius)) {
    closedLoopBand = closedLoopEnabled ? "waiting_sensor" : "manual_pause";
    return;
  }

  uint8_t targetSetpoint = clampAcSetpoint(effectiveTargetTempC);
  float hotStartThreshold = effectiveTargetTempC + TEMP_HYSTERESIS_UP_C;
  float coolThreshold = effectiveTargetTempC + TEMP_HYSTERESIS_UP_C;
  float fanThreshold = effectiveTargetTempC - TEMP_HYSTERESIS_DOWN_C;
  bool humidityValid = !isnan(kelembaban);
  bool feelsHot = !isnan(lastControlTempC) && lastControlTempC >= coolThreshold;
  bool roomReachedTarget = suhuCelsius <= fanThreshold;
  bool feelsComfortable = !isnan(lastControlTempC) &&
                          lastControlTempC <= (effectiveTargetTempC + FAN_MODE_MAX_FEELS_LIKE_MARGIN_C);
  bool humidityTooHighForFan = humidityValid && kelembaban > FAN_MODE_MAX_HUMIDITY_PERCENT;

  if (!hasMlTargetTemp && HOT_START_THRESHOLD_C > hotStartThreshold) {
    hotStartThreshold = HOT_START_THRESHOLD_C;
  }

  if (!acDesiredPowerState && !isnan(lastControlTempC) && lastControlTempC >= hotStartThreshold) {
    closedLoopBand = "start_cooling";
    setDesiredAcState(true, kGreeCool, kGreeFanAuto, targetSetpoint,
                      lastMeasuredHeatIndexC > suhuCelsius ? "auto_feels_hot_start" : "auto_hot_start");
    flushPendingAcCommand();
    return;
  }

  if (!acDesiredPowerState) {
    closedLoopBand = "standby";
    return;
  }

  if (feelsHot) {
    closedLoopBand = "cooling";
    setDesiredAcState(true, kGreeCool, kGreeFanAuto, targetSetpoint,
                      lastMeasuredHeatIndexC > suhuCelsius ? "auto_feels_hot_cooling" : "auto_need_cooling");
  } else if (roomReachedTarget && feelsComfortable && !humidityTooHighForFan) {
    closedLoopBand = "fan_maintain";
    setDesiredAcState(true, kGreeFan, kGreeFanAuto, targetSetpoint, "auto_target_reached_fan");
  } else if (roomReachedTarget && humidityTooHighForFan) {
    closedLoopBand = "hold_cool_humidity";
    setDesiredAcState(true, kGreeCool, kGreeFanAuto, targetSetpoint, "auto_hold_cool_high_humidity");
  } else {
    closedLoopBand = (acDesiredModeState == kGreeCool) ? "hold_cool" : "hold_fan";
  }

  flushPendingAcCommand();
}

// Struktur untuk hasil pembacaan tegangan
struct VoltageReading {
  float voltage;      // Tegangan terukur (V)
  float rms;          // Nilai RMS mentah
  int adcRaw;         // Nilai ADC mentah
  bool isConnected;   // Status koneksi sensor
  float smoothed;      // Nilai smoothed dari TinyML
};

// Struktur untuk hasil pembacaan arus
struct CurrentReading {
  float current;      // Arus terukur (A)
  float rms;          // Nilai RMS mentah (V)
  int adcRaw;         // Nilai ADC mentah
  bool isConnected;   // Status koneksi sensor
  float power;        // Daya (W) = Tegangan × Arus
  float smoothed;      // Nilai smoothed dari TinyML
};

// Fungsi untuk membaca tegangan AC (RMS) dengan validasi
VoltageReading readACVoltage() {
  VoltageReading result;
  
  // Ambil banyak sampel untuk menangkap gelombang AC
  // PLN Indonesia: 50Hz = 20ms per cycle, sample 2000 untuk ~10 cycle (akurasi lebih baik)
  int numSamples = 2000;
  float sumSquares = 0;
  float sumVoltage = 0;
  long sumADC = 0;
  
  for (int i = 0; i < numSamples; i++) {
    // Baca nilai ADC
    int adcValue = analogRead(ZMPT101B_PIN);
    sumADC += adcValue;
    
    // Konversi ADC ke tegangan (0-3.3V)
    float voltage = (adcValue * VREF) / ADC_COUNTS;

    // Hitung statistik sample untuk RMS AC dengan offset DC dinamis.
    // Ini lebih stabil daripada offset statis 1.65V yang bisa meleset antar modul.
    sumVoltage += voltage;
    sumSquares += (voltage * voltage);
    
    delayMicroseconds(200);  // Delay kecil untuk sampling (5kHz sampling rate)
  }
  
  float meanVoltage = sumVoltage / numSamples;
  float variance = (sumSquares / numSamples) - (meanVoltage * meanVoltage);
  if (variance < 0.0f) {
    variance = 0.0f;
  }

  // Hitung nilai RMS (Root Mean Square)
  float rms = sqrt(variance);
  
  // Hitung rata-rata ADC
  int avgADC = sumADC / numSamples;
  
  // Kalibrasi ke tegangan AC sebenarnya (220V)
  float actualVoltage = rms * VOLTAGE_CALIBRATION;
  
  // Validasi: Periksa apakah RMS cukup besar (bukan noise)
  // Dan tegangan hasil kalibrasi melewati threshold
  result.rms = rms;
  result.adcRaw = avgADC;
  
  if (rms > RMS_THRESHOLD && actualVoltage > VOLTAGE_THRESHOLD && actualVoltage <= VOLTAGE_MAX_VALID) {
    result.voltage = actualVoltage;
    result.isConnected = true;
  } else {
    // Jika di bawah threshold, anggap tidak ada sinyal (noise)
    result.voltage = 0.0;
    result.isConnected = false;
  }
  
  return result;
}

// Fungsi untuk membaca arus AC (RMS) dari SCT013-000
// Rangkaian sederhana: Merah->Resistor 62Ω->GPIO32, Hitam->GND (tanpa bias voltage)
CurrentReading readACCurrent() {
  CurrentReading result;
  
  // Ambil banyak sampel untuk menangkap gelombang AC
  // Dengan rangkaian tanpa bias, ADC hanya baca sisi positif (half-wave rectified)
  int numSamples = 2000;
  float sumSquares = 0;
  long sumADC = 0;
  int maxADC = 0;
  
  for (int i = 0; i < numSamples; i++) {
    // Baca nilai ADC
    int adcValue = analogRead(SCT013_PIN);
    sumADC += adcValue;
    if (adcValue > maxADC) maxADC = adcValue;
    
    // Konversi ADC ke tegangan (0-3.3V)
    float voltage = (adcValue * VREF) / ADC_COUNTS;
    
    // Untuk rangkaian tanpa bias, tidak perlu kurangi offset DC
    // ADC sudah baca dari 0V (ground reference)
    
    // Kuadratkan nilai untuk perhitungan RMS
    sumSquares += (voltage * voltage);
    
    delayMicroseconds(200);  // Delay kecil untuk sampling (5kHz sampling rate)
  }
  
  // Hitung nilai RMS (Root Mean Square) dalam volt
  float rmsVoltage = sqrt(sumSquares / numSamples);
  
  // Hitung rata-rata ADC
  int avgADC = sumADC / numSamples;
  
  // Konversi RMS voltage ke RMS current
  // I_rms = V_rms / R_burden
  // Kemudian scale berdasarkan ratio SCT013: 100A primary / 0.05A secondary = 2000:1
  float rmsCurrent = (rmsVoltage / BURDEN_RESISTOR) * CURRENT_CALIBRATION;
  
  // Simpan hasil
  result.rms = rmsVoltage;
  result.adcRaw = avgADC;
  
  // Validasi: Periksa kondisi sensor
  // ADC saturasi (>4090) menandakan sensor tidak terhubung dengan benar atau floating
  // RMS > 3.0V juga menandakan ADC saturasi (noise karena pin floating)
  if (avgADC > 4090 || rmsVoltage > 3.0) {
    // ADC saturasi = pin floating / tidak terhubung
    result.current = 0.0;
    result.isConnected = false;
  } else if (rmsVoltage > CURRENT_RMS_THRESHOLD && rmsCurrent > CURRENT_THRESHOLD_MIN) {
    result.current = rmsCurrent;
    result.isConnected = true;
  } else {
    // Jika di bawah threshold, anggap tidak ada arus (noise atau no-load)
    result.current = 0.0;
    result.isConnected = false;
  }
  
  result.power = 0.0;  // Akan dihitung di loop() dengan data tegangan
  
  return result;
}

// Fungsi untuk koneksi WiFi
void setupWiFi() {
  delay(10);
  Serial.println();
  Serial.print("Menghubungkan ke WiFi: ");
  Serial.println(ssid);
  
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println();
  Serial.println("WiFi terhubung!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
}

// Fungsi untuk generate SAS Token untuk Azure IoT Hub
String generateSasToken(const char* key, String url, long expiry) {
  // URL encode
  url.toLowerCase();
  String stringToSign = url + "\n" + String(expiry);
  
  // Decode Base64 key menggunakan mbedtls
  size_t keyLength = strlen(key);
  size_t decodedKeyLength = 0;
  unsigned char decodedKey[64];
  
  mbedtls_base64_decode(decodedKey, sizeof(decodedKey), &decodedKeyLength, 
                        (const unsigned char*)key, keyLength);
  
  // HMAC-SHA256
  unsigned char hmacResult[32];
  mbedtls_md_context_t ctx;
  mbedtls_md_type_t md_type = MBEDTLS_MD_SHA256;
  
  mbedtls_md_init(&ctx);
  mbedtls_md_setup(&ctx, mbedtls_md_info_from_type(md_type), 1);
  mbedtls_md_hmac_starts(&ctx, decodedKey, decodedKeyLength);
  mbedtls_md_hmac_update(&ctx, (const unsigned char*)stringToSign.c_str(), stringToSign.length());
  mbedtls_md_hmac_finish(&ctx, hmacResult);
  mbedtls_md_free(&ctx);
  
  // Encode result to Base64 menggunakan mbedtls
  unsigned char encodedSignature[64];
  size_t encodedLength = 0;
  mbedtls_base64_encode(encodedSignature, sizeof(encodedSignature), &encodedLength, 
                        hmacResult, 32);
  
  String signature = String((char*)encodedSignature);
  
  // URL encode signature
  signature.replace("+", "%2B");
  signature.replace("=", "%3D");
  signature.replace("/", "%2F");
  
  // Create SAS token
  String sasToken = "SharedAccessSignature sr=" + url + "&sig=" + signature + "&se=" + String(expiry);
  
  return sasToken;
}

// Kirim data ke RPi Gateway via HTTP POST
void sendToRPiGateway(const char* jsonBuffer) {
  #if USE_RPI_GATEWAY
  // Pastikan WiFi masih terhubung
  ensureWiFiConnected();

  HTTPClient http;
  WiFiClient wifiClient;

  Serial.print("📤 Mengirim ke RPi Gateway: ");
  Serial.println(RPI_GATEWAY_URL);

  if (http.begin(wifiClient, RPI_GATEWAY_URL)) {
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(5000);  // 5 detik timeout

    int httpCode = http.POST(jsonBuffer);

    if (httpCode > 0) {
      String response = http.getString();
      Serial.print("✓ HTTP POST success (");
      Serial.print(httpCode);
      Serial.print("): ");
      Serial.println(response);

      #if USE_RPI_GATEWAY
      successCount++;
      #endif
    } else {
      Serial.print("✗ HTTP POST failed: ");
      Serial.println(http.errorToString(httpCode).c_str());

      #if USE_RPI_GATEWAY
      failCount++;
      #endif
    }

    http.end();
  } else {
    Serial.println("✗ Gagal koneksi ke RPi Gateway");
    #if USE_RPI_GATEWAY
    failCount++;
    #endif
  }

  Serial.print("   Stats - Sukses: ");
  Serial.print(successCount);
  Serial.print(", Gagal: ");
  Serial.print(failCount);
  Serial.println();
  #endif
}

// Fungsi untuk koneksi ulang ke Azure IoT Hub
void reconnectMQTT() {
  ensureWiFiConnected();

  while (!client.connected()) {
    Serial.println("\nMenghubungkan ke Azure IoT Hub...");
    Serial.print("Hub: ");
    Serial.println(mqtt_server);
    Serial.print("Device ID: ");
    Serial.println(deviceId);
    
    // Test DNS resolution
    IPAddress ip;
    Serial.print("📡 Resolving DNS... ");
    if (WiFi.hostByName(mqtt_server.c_str(), ip)) {
      Serial.print("OK! IP: ");
      Serial.println(ip);
    } else {
      Serial.println("GAGAL! DNS tidak bisa di-resolve");
      Serial.println("  Coba lagi dalam 5 detik...");
      delay(5000);
      continue;
    }
    
    // Test TCP connection ke port 8883
    Serial.print("🔌 Testing TCP port 8883... ");
    WiFiClient testClient;
    if (testClient.connect(mqtt_server.c_str(), 8883)) {
      Serial.println("OK! Port terbuka");
      testClient.stop();
    } else {
      Serial.println("GAGAL! Port 8883 diblokir atau timeout");
      Serial.println("  Kemungkinan firewall/router memblokir koneksi IoT");
      Serial.println("  Coba lagi dalam 5 detik...");
      delay(5000);
      continue;
    }
    
    // Generate SAS Token jika expired atau belum ada
    unsigned long currentTime = time(nullptr);
    if (sasToken == "" || currentTime >= (sasTokenExpiry - SAS_TOKEN_REFRESH_WINDOW)) {
      Serial.println("Generating new SAS Token...");
      sasTokenExpiry = currentTime + 3600; // Token valid untuk 1 jam
      String resourceUri = mqtt_server + "/devices/" + String(deviceId);
      sasToken = generateSasToken(deviceKey, resourceUri, sasTokenExpiry);
      Serial.println("✓ SAS Token generated");
    }
    
    // Koneksi dengan SAS Token
    if (client.connect(deviceId, mqtt_username.c_str(), sasToken.c_str())) {
      Serial.println("✓ Terhubung ke Azure IoT Hub!");
      if (client.subscribe(mqtt_c2d_topic.c_str())) {
        Serial.print("✓ Subscribe C2D topic: ");
        Serial.println(mqtt_c2d_topic);
      } else {
        Serial.println("⚠️ Gagal subscribe C2D topic.");
      }
    } else {
      Serial.print("✗ Gagal, rc=");
      Serial.print(client.state());
      Serial.println(" | Periksa konfigurasi IoT Hub");
      Serial.println("  Error codes:");
      Serial.println("  -4: Connection timeout");
      Serial.println("  -3: Connection lost");
      Serial.println("  -2: Connect failed");
      Serial.println("   5: Connection refused (bad credentials)");
      Serial.println("\n  Coba lagi dalam 5 detik...");
      delay(5000);
    }
  }
}

void setup() {
  // Inisialisasi komunikasi serial
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n\n===========================================");
  Serial.println("ESP32 Digital Twin - Monitoring Sensor");
  Serial.println("DHT11 + ZMPT101B + SCT013-000");
  Serial.println("Tegangan AC 220V + Arus AC 100A");
  Serial.println("===========================================");
  
  Serial.println("⚠️  KESELAMATAN: Pastikan sensor terpasang dengan benar!");
  Serial.print("   DHT11 DATA: GPIO ");
  Serial.println(DHTPIN);
  Serial.print("   IR TX LED: GPIO ");
  Serial.println(IR_TX_PIN);
  Serial.print("   IR RX KY-022 (OUT): GPIO ");
  Serial.println(IR_RX_PIN);
  Serial.println("   ZMPT101B:");
  Serial.println("   - Input: Fase & Netral dari stopkontak 220V");
  Serial.println("   - Output: VCC, GND, OUT ke ESP32 GPIO35");
  Serial.println("   SCT013-000:");
  Serial.println("   - Clamp pada kabel FASE beban yang aktif");
  Serial.println("   - Kabel MERAH: Resistor 62Ω -> ESP32 GPIO32");
  Serial.println("   - Kabel HITAM: ESP32 GND");
  Serial.println("   - JANGAN hubungkan 220V langsung ke ESP32!\n");
  
  // Inisialisasi sensor DHT
  dht.begin();

  rawIrStorageReady = rawIrPrefs.begin("acraw", false);
  if (rawIrStorageReady) {
    loadStoredRawProfiles();
    Serial.println("💾 Raw IR profiles loaded dari flash.");
    printRawProfileSummary();
  } else {
    Serial.println("⚠️ Gagal membuka storage raw IR (Preferences).");
  }

  // Inisialisasi IR untuk mode capture dan mode send command AC
  irsend.begin();
  irrecv.enableIRIn();
  greeAc.begin();
  greeAc.setPower(acPowerState);
  greeAc.setMode(acModeState);
  greeAc.setFan(acFanState);
  greeAc.setTemp(acSetpointState);
  greeAc.setSwingVertical(true, kGreeSwingAuto);

  acDesiredPowerState = acPowerState;
  acDesiredModeState = acModeState;
  acDesiredFanState = acFanState;
  acDesiredSetpointState = acSetpointState;

  Serial.println("\n📡 IR stack aktif (capture + transmitter)");
  Serial.println("   Mode capture default: OFF (hindari noise KY-022 saat closed-loop otomatis).");
  Serial.println("   Aktifkan capture bila perlu debug: ir-capture-on");
  Serial.println("   Arahkan remote AC Gree ke KY-022 hanya saat capture aktif.");
  Serial.println("   Ketik ir-help di serial monitor untuk perintah capture/kirim uji.");
  Serial.println("   Untuk model Gree yang tidak cocok library, simpan profil raw: off, fan, cool-24, dst.");
  Serial.println("   Closed-loop aktif: AC otomatis COOL/FAN berbasis suhu-terasa, kelembaban, dan target ML.");

  Serial.println("\n🤖 TINYML AKTIF:");
  Serial.println("   - Moving Average Filter (10-sample buffer) untuk smooth data");
  Serial.println("   - Anomaly Detection (voltage/current/temperature)");
  Serial.println("   - Power Mode Classifier (efficient/moderate/high)");
  Serial.println("   - Perintah: tinyml-status | tinyml-reset");
  
  // Inisialisasi ADC untuk sensor tegangan
  analogReadResolution(ADC_BITS);  // Set resolusi ADC 12-bit
  analogSetAttenuation(ADC_11db);  // Set atenuasi untuk range 0-3.3V
  
  // Koneksi WiFi
  setupWiFi();
  
  // Sinkronisasi waktu dengan NTP (diperlukan untuk SAS Token)
  Serial.println("\n⏰ Sinkronisasi waktu dengan NTP...");
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
  time_t now = time(nullptr);
  int retry = 0;
  while (now < 8 * 3600 * 2 && retry < 15) {
    delay(500);
    Serial.print(".");
    now = time(nullptr);
    retry++;
  }
  if (now < 8 * 3600 * 2) {
    Serial.println("\n✗ Gagal sinkronisasi waktu!");
    Serial.println("  Restart ESP32 atau periksa koneksi internet");
  } else {
    Serial.println("\n✓ Waktu tersinkronisasi");
    Serial.print("  Current time: ");
    Serial.println(ctime(&now));
  }
  
  // Konfigurasi TLS dengan Root CA Certificate Azure IoT Hub
  Serial.println("🔐 Mengkonfigurasi TLS dengan Azure Root CA...");
  espClient.setCACert(azure_root_ca);
  espClient.setTimeout(30);    // TLS timeout 30 detik (untuk slow networks)
  espClient.setHandshakeTimeout(30); // TLS handshake timeout
  
  // Konfigurasi MQTT dengan buffer size lebih besar untuk Azure IoT Hub
  #if !USE_RPI_GATEWAY
  client.setServer(mqtt_server.c_str(), mqtt_port);
  client.setCallback(mqttCallback);
  client.setBufferSize(1024);  // Buffer lebih besar untuk JSON + overhead
  client.setKeepAlive(60);     // Keep alive 60 detik (lebih responsif)
  client.setSocketTimeout(60); // Socket timeout 60 detik (lebih toleran)
  #endif

  Serial.println("\n📡 Konfigurasi selesai");
  Serial.print("   Gateway mode: ");
  #if USE_RPI_GATEWAY
  Serial.println("RPi HTTP Gateway");
  Serial.print("   RPi URL: ");
  Serial.println(RPI_GATEWAY_URL);
  #else
  Serial.println("Azure IoT Hub MQTT");
  Serial.print("   IoT Hub: ");
  Serial.println(mqtt_server);
  #endif
  
  Serial.println("\n🔧 STATUS KALIBRASI:");
  Serial.println("   TEGANGAN (ZMPT101B):");
  Serial.println("   ✓ Target grid: 220V PLN Indonesia");
  Serial.print("   ✓ Faktor kalibrasi awal: ");
  Serial.println(VOLTAGE_CALIBRATION, 1);
  Serial.print("   ✓ Rentang valid: ");
  Serial.print(VOLTAGE_THRESHOLD, 0);
  Serial.print("V - ");
  Serial.print(VOLTAGE_MAX_VALID, 0);
  Serial.println("V");
  Serial.println("   ARUS (SCT013-000):");
  Serial.print("   ✓ Burden resistor: ");
  Serial.print(BURDEN_RESISTOR, 0);
  Serial.println(" ohm");
  Serial.println("   ✓ Ratio: 2000:1 (100A primary / 50mA secondary)");
  Serial.print("   ✓ Threshold RMS arus: ");
  Serial.print(CURRENT_RMS_THRESHOLD, 3);
  Serial.println(" V\n");
  Serial.println("   📌 CARA KALIBRASI ARUS:");
  Serial.println("   1. Jepit SCT013 pada kabel FASE beban (misal: lampu 100W)");
  Serial.println("   2. Nyalakan beban dan catat 'RMS mentah (I)' dari Serial Monitor");
  Serial.println("   3. Hitung arus sebenarnya: I = P/V (100W/220V = 0.45A)");
  Serial.println("   4. Jika tidak akurat, sesuaikan: BURDEN_RESISTOR = (RMS_mentah × 2000) / Arus_sebenarnya");
  Serial.println("   5. Contoh: RMS=0.014V, Arus=0.45A -> R = (0.014×2000)/0.45 = 62Ω\n");
  
  // Koneksi awal (skip jika pakai RPi Gateway)
  #if !USE_RPI_GATEWAY
  reconnectMQTT();
  #else
  Serial.println("\n✓ Mode RPi Gateway aktif - tidak perlu koneksi MQTT");
  Serial.println("   Data akan dikirim via HTTP POST ke RPi setiap 5 detik");
  #endif

  delay(100);
}

void loop() {
  ensureWiFiConnected();

  handleSerialInput();
  handleIrCapture();
  flushPendingAcCommand();

  // Skip SAS token refresh jika pakai RPi Gateway (tidak butuh MQTT)
  #if !USE_RPI_GATEWAY
  unsigned long currentEpoch = time(nullptr);
  if (sasToken != "" && currentEpoch > 0 && currentEpoch >= (sasTokenExpiry - SAS_TOKEN_REFRESH_WINDOW)) {
    Serial.println("\n⏳ SAS Token hampir expired, refresh koneksi MQTT...");
    client.disconnect();
    sasToken = "";
  }

  // Maintain koneksi MQTT - panggil loop() sesering mungkin
  client.loop();

  // Cek koneksi hanya jika terputus
  if (!client.connected()) {
    Serial.println("\n⚠️ Koneksi MQTT terputus, reconnecting...");
    reconnectMQTT();
  }

  // Panggil client.loop() lagi untuk process incoming messages
  client.loop();
  #endif

  unsigned long now = millis();
  
  // Kirim data setiap interval waktu
  if (now - lastMsg > interval) {
    lastMsg = now;
    
    // Baca sensor DHT11 dengan retry
    float kelembaban = NAN;
    float suhuCelsius = NAN;
    float suhuFahrenheit = NAN;
    bool dhtSuccess = false;

    // Skip DHT reading sementara (fokus IR AC)
    #ifdef DISABLE_DHT_SENSOR
      kelembaban = 50.0;  // Default value
      suhuCelsius = 28.0; // Default value
      suhuFahrenheit = dht.readTemperature(true);
      if (isnan(suhuFahrenheit)) suhuFahrenheit = 82.4;
      dhtSuccess = true;
    #else
      // Retry hingga 3x jika gagal baca
      for (int retry = 0; retry < 3; retry++) {
        kelembaban = dht.readHumidity();
        suhuCelsius = dht.readTemperature();
        suhuFahrenheit = dht.readTemperature(true);

        if (!isnan(kelembaban) && !isnan(suhuCelsius)) {
          dhtSuccess = true;
          break;  // Berhasil baca, keluar dari loop
        }
        delay(500);  // Tunggu 500ms sebelum retry
      }

      // Cek apakah pembacaan gagal setelah retry
      if (!dhtSuccess) {
        Serial.println("⚠️ Gagal membaca DHT11! Skip sementara, gunakan default.");
        Serial.println("   Fokus: Testing IR AC sensor");
        kelembaban = 50.0;  // Default
        suhuCelsius = 28.0;  // Default
        suhuFahrenheit = 82.4;
        dhtSuccess = true;  // Lanjutkan loop
      }
    #endif
    
    // Hitung heat index
    float heatIndexC = dht.computeHeatIndex(suhuCelsius, kelembaban, false);

    // Evaluasi closed-loop otomatis berbasis suhu saat ini dan target ML/default.
    applyClosedLoopControl(suhuCelsius, kelembaban);
    
    // Baca tegangan AC dengan validasi
    VoltageReading voltageData = readACVoltage();
    
    // Baca arus AC dengan validasi
    CurrentReading currentData;
    if (DISABLE_CURRENT_SENSOR) {
      // Sensor arus di-disable, set nilai default
      currentData.current = 0.0;
      currentData.rms = 0.0;
      currentData.adcRaw = 0;
      currentData.isConnected = false;
      currentData.power = 0.0;
    } else {
      currentData = readACCurrent();
    }
    
    // Hitung daya (Power) jika kedua sensor terhubung
    float power = 0.0;
    if (voltageData.isConnected && currentData.isConnected) {
      power = voltageData.voltage * currentData.current;  // P = V × I (apparent power)
      currentData.power = power;
    }

    // ===== TINYML INFERENCE =====
    // Apply Moving Average filters untuk smooth data
    float smoothedTemp = tinyml.tempFilter.update(suhuCelsius);
    float smoothedHumidity = tinyml.humidityFilter.update(kelembaban);
    float smoothedVoltage = tinyml.voltageFilter.update(voltageData.voltage);
    float smoothedCurrent = tinyml.currentFilter.update(currentData.current);
    float smoothedPower = tinyml.powerFilter.update(power);

    voltageData.smoothed = smoothedVoltage;
    currentData.smoothed = smoothedCurrent;

    // Run anomaly detection
    unsigned long infStart = micros();
    AnomalyResult anomaly = tinyml.anomalyDetector.detect(
      smoothedVoltage,
      smoothedCurrent,
      smoothedTemp
    );
    tinyml.lastInferenceUs = micros() - infStart;

    // Update anomaly history
    tinyml.anomalyDetector.updateHistory(smoothedVoltage, smoothedCurrent);

    // Classify power usage pattern
    PowerMode powerMode = tinyml.powerClassifier.classify(smoothedPower);
    const char* powerModeLabel = tinyml.powerClassifier.getModeLabel(powerMode);
    float powerConfidence = tinyml.powerClassifier.getModeConfidence(smoothedPower, powerMode);

    // Tampilkan ke Serial Monitor
    Serial.println("=================================");
    Serial.print("Kelembaban: ");
    Serial.print(kelembaban);
    Serial.println(" %");

    Serial.print("Suhu: ");
    Serial.print(suhuCelsius);
    Serial.println(" °C");

    Serial.print("Heat Index: ");
    Serial.print(heatIndexC);
    Serial.println(" °C");

    Serial.print("Control Temp: ");
    Serial.print(lastControlTempC, 1);
    Serial.print(" °C | Band: ");
    Serial.println(closedLoopBand);

    Serial.print("Tegangan AC (RMS): ");
    Serial.print(voltageData.voltage);
    Serial.print(" V | Smoothed: ");
    Serial.print(smoothedVoltage, 1);
    Serial.print(" V | Status: ");
    Serial.println(voltageData.isConnected ? "Terhubung" : "Tidak terhubung (noise)");

    Serial.print("RMS mentah (V): ");
    Serial.print(voltageData.rms, 4);
    Serial.print(" V | ADC Raw Avg: ");
    Serial.println(voltageData.adcRaw);

    Serial.print("Arus AC (RMS): ");
    Serial.print(currentData.current, 2);
    Serial.print(" A | Smoothed: ");
    Serial.print(smoothedCurrent, 2);
    Serial.print(" A | Status: ");
    Serial.println(currentData.isConnected ? "Terhubung" : "Tidak terhubung (noise)");

    Serial.print("RMS mentah (I): ");
    Serial.print(currentData.rms, 4);
    Serial.print(" V | ADC Raw Avg: ");
    Serial.println(currentData.adcRaw);

    Serial.print("Daya (Power): ");
    Serial.print(power, 1);
    Serial.print(" W | Smoothed: ");
    Serial.print(smoothedPower, 1);
    Serial.println(" W");

    // TinyML Status Display
    Serial.print("TinyML Inference: ");
    Serial.print(tinyml.lastInferenceUs);
    Serial.println(" us");
    Serial.print("  Anomaly: ");
    Serial.print(anomaly.isAnomaly ? "DETECTED" : "none");
    if (anomaly.isAnomaly) {
      Serial.print(" (");
      Serial.print(anomaly.reason);
      Serial.print(", conf=");
      Serial.print(anomaly.confidence, 2);
      Serial.print(")");
    }
    Serial.println();
    Serial.print("  Power Mode: ");
    Serial.print(powerModeLabel);
    Serial.print(" (conf=");
    Serial.print(powerConfidence, 2);
    Serial.println(")");

    Serial.print("AC State: ");
    Serial.print(acPowerState ? "ON" : "OFF");
    Serial.print(" | Mode: ");
    Serial.print(acModeToLabel(acModeState));
    Serial.print(" | Fan: ");
    Serial.print(acFanToLabel(acFanState));
    Serial.print(" | Setpoint: ");
    Serial.print(acSetpointState);
    Serial.println(" C");

    Serial.print("Closed-loop: ");
    Serial.print(closedLoopEnabled ? "aktif" : "nonaktif");
    Serial.print(" | Target: ");
    Serial.print(effectiveTargetTempC, 1);
    Serial.print(" C (");
    Serial.print(targetSource);
    Serial.print(") | Humidity gate fan <= ");
    Serial.print(FAN_MODE_MAX_HUMIDITY_PERCENT, 0);
    Serial.println("%");

    // ===== SERIAL DATA OUTPUT UNTUK RASPBERRY PI GATEWAY =====
    // Format: DATA|suhu|kelembaban|tegangan|arus|power|anomaly|conf|inf|esp32_temp|free_heap|wifi_rssi|cpu_freq|ac_power|ac_mode|ac_setpoint|loop|target|reason
    // Contoh: DATA|28.5|65.0|220.0|0.45|99.0|0|1.00|24|38.5|185000|-45|240|on|cool|24|1|ml|auto_feels_hot_cooling
    Serial.print("DATA|");
    Serial.print(suhuCelsius, 1);
    Serial.print("|");
    Serial.print(kelembaban, 1);
    Serial.print("|");
    Serial.print(voltageData.voltage, 1);
    Serial.print("|");
    Serial.print(currentData.current, 2);
    Serial.print("|");
    Serial.print(power, 1);
    Serial.print("|");
    Serial.print(anomaly.isAnomaly ? 1 : 0);
    Serial.print("|");
    Serial.print(anomaly.confidence, 2);
    Serial.print("|");
    Serial.print(tinyml.lastInferenceUs);
    Serial.print("|");
    Serial.print(temperatureRead());
    Serial.print("|");
    Serial.print(ESP.getFreeHeap());
    Serial.print("|");
    Serial.print(WiFi.RSSI());
    Serial.print("|");
    Serial.print(getCpuFrequencyMhz());
    Serial.print("|");
    Serial.print(acPowerState ? "on" : "off");
    Serial.print("|");
    Serial.print(acModeToLabel(acModeState));
    Serial.print("|");
    Serial.print(acSetpointState);
    Serial.print("|");
    Serial.print(closedLoopEnabled ? 1 : 0);
    Serial.print("|");
    Serial.print(targetSource);
    Serial.print("|");
    Serial.println(acLastReason);

    // Buat JSON document
     JsonDocument doc;
     doc["suhu"] = round(suhuCelsius * 10) / 10.0;  // 1 desimal
     doc["kelembaban"] = round(kelembaban * 10) / 10.0;  // 1 desimal
     doc["tegangan"] = round(voltageData.voltage * 10) / 10.0;  // 1 desimal
     doc["arus"] = round(currentData.current * 100) / 100.0;  // 2 desimal
     doc["daya"] = round(power * 10) / 10.0;  // 1 desimal
     doc["status_tegangan"] = voltageData.isConnected ? "terhubung" : "tidak_terhubung";
     doc["status_arus"] = currentData.isConnected ? "terhubung" : "tidak_terhubung";
     doc["deviceId"] = deviceId;
     doc["timestamp"] = getIsoTimestampUTC();
     if (!isnan(heatIndexC)) {
       doc["heat_index"] = round(heatIndexC * 10) / 10.0;
     }

     // ESP32 Health Data
     doc["health"]["esp32_temp_c"] = round(temperatureRead() * 10) / 10.0;
     doc["health"]["free_heap_bytes"] = ESP.getFreeHeap();
     doc["health"]["wifi_rssi_dbm"] = WiFi.RSSI();
     doc["health"]["cpu_freq_mhz"] = getCpuFrequencyMhz();
     doc["health"]["uptime_seconds"] = (millis() / 1000);  // ESP32 uptime in seconds

     // TinyML data
     doc["tinyml"]["anomaly"] = anomaly.isAnomaly;
     doc["tinyml"]["anomaly_confidence"] = anomaly.confidence;
     doc["tinyml"]["anomaly_reason"] = anomaly.reason;
     doc["tinyml"]["inference_us"] = tinyml.lastInferenceUs;
     doc["tinyml"]["power_mode"] = powerModeLabel;
     doc["tinyml"]["power_confidence"] = powerConfidence;
     doc["tinyml"]["smoothed_voltage"] = round(smoothedVoltage * 10) / 10.0;
     doc["tinyml"]["smoothed_current"] = round(smoothedCurrent * 100) / 100.0;
     doc["tinyml"]["smoothed_power"] = round(smoothedPower * 10) / 10.0;

     // Serialize JSON ke string
     doc["closed_loop_enabled"] = closedLoopEnabled;
     doc["target_temp"] = round(effectiveTargetTempC * 10) / 10.0;
     doc["target_source"] = targetSource;
     doc["control_temp"] = round(lastControlTempC * 10) / 10.0;
     doc["control_band"] = closedLoopBand;
     doc["fan_humidity_gate"] = FAN_MODE_MAX_HUMIDITY_PERCENT;
     doc["ac_power"] = acPowerState ? "on" : "off";
     doc["ac_mode"] = acModeToLabel(acModeState);
     doc["ac_fan"] = acFanToLabel(acFanState);
     doc["ac_setpoint"] = acSetpointState;
     doc["ac_last_reason"] = acLastReason;
     doc["ac_pending_command"] = hasPendingAcCommand();

    char jsonBuffer[1024];  // Increased for TinyML data
    serializeJson(doc, jsonBuffer);
    
    // Tampilkan JSON yang akan dikirim
    Serial.print("JSON: ");
    Serial.println(jsonBuffer);
    
    // KIRIM DATA KE RPI GATEWAY (HTTP POST)
    #if USE_RPI_GATEWAY
    sendToRPiGateway(jsonBuffer);
    #else
    // Pastikan koneksi masih aktif sebelum publish
    if (!client.connected()) {
      Serial.println("⚠️ Koneksi terputus, reconnecting sebelum kirim...");
      reconnectMQTT();
    }

    // Legacy: Kirim ke Azure IoT Hub jika USE_RPI_GATEWAY = 0
    if (!client.connected()) {
      Serial.println("⚠️ Koneksi terputus, reconnecting sebelum kirim...");
      reconnectMQTT();
    }

    if (client.publish(mqtt_topic.c_str(), jsonBuffer, false)) {
      successCount++;
      Serial.print("✓ Data terkirim ke Azure! (Total sukses: ");
      Serial.print(successCount);
      Serial.print(", Gagal: ");
      Serial.print(failCount);
      Serial.println(")");

      for (int i = 0; i < 10; i++) {
        client.loop();
        delay(50);
      }
    } else {
      failCount++;
      Serial.println("✗ Gagal mengirim data ke Azure IoT Hub");
      Serial.print("   MQTT State: ");
      Serial.println(client.state());
      Serial.println("   Memaksa reconnect untuk percobaan berikutnya...");
      client.disconnect();
      sasToken = "";
    }
    #endif

    Serial.println("=================================");
  }

  // Maintain MQTT connection saat idle (jika tidak pakai RPi Gateway)
  #if !USE_RPI_GATEWAY
  client.loop();
  #endif
  delay(100);
}
