#include <WiFi.h>
#include <WebServer.h>

// Motor driver pins
const int AIN1 = 13;
const int AIN2 = 14;
const int BIN1 = 12;
const int BIN2 = 27;
const int PWMA = 26;
const int PWMB = 25;
const int STBY = 33;

// WiFi credentials for Access Point
const char* ssid = "ESP32_Motor_Control";
const char* password = "12345678";

WebServer server(80);

// Motor speeds (-255 to 255)
int motorASpeed = 0;
int motorBSpeed = 0;

// Autonomous mode tracking
bool autonomousMode = false;
unsigned long lastCommandTime = 0;
const unsigned long COMMAND_TIMEOUT = 500; // Stop if no command for 500ms

void setup() {
  Serial.begin(115200);
  
  // Initialize motor pins
  pinMode(AIN1, OUTPUT);
  pinMode(AIN2, OUTPUT);
  pinMode(BIN1, OUTPUT);
  pinMode(BIN2, OUTPUT);
  pinMode(PWMA, OUTPUT);
  pinMode(PWMB, OUTPUT);
  pinMode(STBY, OUTPUT);
  
  // Enable motor driver
  digitalWrite(STBY, HIGH);
  
  // Set up Access Point
  WiFi.softAP(ssid, password);
  Serial.println("\n===========================================");
  Serial.println("ESP32 AUTONOMOUS MOTOR CONTROL");
  Serial.println("===========================================");
  Serial.println("Access Point Started");
  Serial.print("SSID: ");
  Serial.println(ssid);
  Serial.print("Password: ");
  Serial.println(password);
  Serial.print("IP Address: ");
  Serial.println(WiFi.softAPIP());
  Serial.println("===========================================\n");
  
  // Define web server routes
  server.on("/", handleRoot);
  server.on("/control", handleControl);
  server.on("/stop", handleStop);
  server.on("/status", handleStatus);
  
  server.begin();
  Serial.println("✓ Web server started");
  Serial.println("✓ Ready for autonomous control\n");
}

void loop() {
  server.handleClient();
  
  // Safety timeout - stop motors if no command received
  if (autonomousMode && (millis() - lastCommandTime > COMMAND_TIMEOUT)) {
    if (motorASpeed != 0 || motorBSpeed != 0) {
      Serial.println("⚠️ Command timeout - Emergency stop");
      stopMotors();
    }
  }
}

void handleRoot() {
  String html = R"(
<!DOCTYPE html>
<html>
<head>
    <meta name='viewport' content='width=device-width, initial-scale=1'>
    <title>ESP32 Motor Control</title>
    <style>
        body { font-family: Arial; text-align: center; margin: 20px; background: #f0f0f0; }
        .container { max-width: 500px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        h1 { color: #333; margin-bottom: 20px; }
        .status { padding: 15px; margin: 20px 0; border-radius: 8px; font-weight: bold; }
        .autonomous { background: #4CAF50; color: white; }
        .manual { background: #2196F3; color: white; }
        .motor-section { margin: 20px 0; padding: 20px; border: 2px solid #ddd; border-radius: 8px; }
        button { padding: 15px 25px; margin: 10px; font-size: 16px; border: none; border-radius: 5px; cursor: pointer; }
        .forward { background: #4CAF50; color: white; }
        .backward { background: #f44336; color: white; }
        .stop { background: #ff9800; color: white; font-size: 20px; padding: 20px 40px; }
        .info { background: #e3f2fd; padding: 15px; margin: 20px 0; border-radius: 8px; border-left: 4px solid #2196F3; text-align: left; }
    </style>
</head>
<body>
    <div class='container'>
        <h1>🤖 ESP32 Motor Control</h1>
        
        <div class='info'>
            <strong>📡 Connection Info:</strong><br>
            IP: 192.168.4.1<br>
            Status: <span id='status'>Checking...</span><br>
            Mode: <span id='mode'>Manual</span>
        </div>
        
        <div class='motor-section'>
            <h3>Linear Movement Control</h3>
            <p style='color: #666;'>Both motors move together for forward/backward motion</p>
            <button class='forward' onclick='moveForward()'>🔼 FORWARD</button><br>
            <button class='backward' onclick='moveBackward()'>🔽 BACKWARD</button><br>
            <button class='stop' onclick='stopAll()'>⏹️ STOP</button>
        </div>
        
        <div class='motor-section'>
            <h3>Individual Motor Control</h3>
            <div style='display: inline-block; margin: 10px;'>
                <h4>Motor A (Left)</h4>
                <button class='forward' onclick='setMotor("A", 150)'>Forward</button>
                <button class='backward' onclick='setMotor("A", -150)'>Backward</button>
                <button class='stop' onclick='setMotor("A", 0)'>Stop</button>
            </div>
            <div style='display: inline-block; margin: 10px;'>
                <h4>Motor B (Right)</h4>
                <button class='forward' onclick='setMotor("B", 150)'>Forward</button>
                <button class='backward' onclick='setMotor("B", -150)'>Backward</button>
                <button class='stop' onclick='setMotor("B", 0)'>Stop</button>
            </div>
        </div>
    </div>

    <script>
        function setMotor(motor, speed) {
            fetch('/control?motor=' + motor + '&speed=' + speed);
        }
        
        function moveForward() {
            setMotor('A', 200);
            setMotor('B', 200);
        }
        
        function moveBackward() {
            setMotor('A', -200);
            setMotor('B', -200);
        }
        
        function stopAll() {
            fetch('/stop');
        }
        
        // Update status periodically
        setInterval(function() {
            fetch('/status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('status').innerText = 'Connected';
                    document.getElementById('mode').innerText = data.autonomous ? 'Autonomous' : 'Manual';
                })
                .catch(() => {
                    document.getElementById('status').innerText = 'Disconnected';
                });
        }, 1000);
    </script>
</body>
</html>
)";
  
  server.send(200, "text/html", html);
}

void handleControl() {
  String motor = server.arg("motor");
  int speed = server.arg("speed").toInt();
  
  // Clamp speed to valid range
  speed = constrain(speed, -255, 255);
  
  if (motor == "A") {
    motorASpeed = speed;
    controlMotorA(speed);
  } else if (motor == "B") {
    motorBSpeed = speed;
    controlMotorB(speed);
  }
  
  // Update command timestamp
  lastCommandTime = millis();
  autonomousMode = true;
  
  // Log command
  Serial.print("Motor ");
  Serial.print(motor);
  Serial.print(" → Speed: ");
  Serial.print(speed);
  if (speed > 0) {
    Serial.println(" (FORWARD)");
  } else if (speed < 0) {
    Serial.println(" (BACKWARD)");
  } else {
    Serial.println(" (STOP)");
  }
  
  server.send(200, "text/plain", "OK");
}

void handleStop() {
  Serial.println("🛑 STOP command received");
  stopMotors();
  server.send(200, "text/plain", "Stopped");
}

void handleStatus() {
  String json = "{";
  json += "\"motorA\":" + String(motorASpeed) + ",";
  json += "\"motorB\":" + String(motorBSpeed) + ",";
  json += "\"autonomous\":" + String(autonomousMode ? "true" : "false");
  json += "}";
  
  server.send(200, "application/json", json);
}

void stopMotors() {
  motorASpeed = 0;
  motorBSpeed = 0;
  controlMotorA(0);
  controlMotorB(0);
  autonomousMode = false;
}

void controlMotorA(int speed) {
  if (speed > 0) {
    // Forward
    digitalWrite(AIN1, HIGH);
    digitalWrite(AIN2, LOW);
    analogWrite(PWMA, speed);
  } else if (speed < 0) {
    // Backward
    digitalWrite(AIN1, LOW);
    digitalWrite(AIN2, HIGH);
    analogWrite(PWMA, abs(speed));
  } else {
    // Stop
    digitalWrite(AIN1, LOW);
    digitalWrite(AIN2, LOW);
    analogWrite(PWMA, 0);
  }
}

void controlMotorB(int speed) {
  if (speed > 0) {
    // Forward
    digitalWrite(BIN1, HIGH);
    digitalWrite(BIN2, LOW);
    analogWrite(PWMB, speed);
  } else if (speed < 0) {
    // Backward
    digitalWrite(BIN1, LOW);
    digitalWrite(BIN2, HIGH);
    analogWrite(PWMB, abs(speed));
  } else {
    // Stop
    digitalWrite(BIN1, LOW);
    digitalWrite(BIN2, LOW);
    analogWrite(PWMB, 0);
  }
}
