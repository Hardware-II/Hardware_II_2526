import oscP5.*;
import netP5.*;
import processing.data.JSONObject;

OscP5 oscP5;
NetAddress pythonServer;

String prompt = "Waiting for Python state...";
int housing = 0, green = 0, mobility = 0;

void setup() {
  size(1000, 600);
  textAlign(CENTER, CENTER);

  // listen for state from Python
  oscP5 = new OscP5(this, 9000);

  // send events to Python
  pythonServer = new NetAddress("127.0.0.1", 8000);
}

void draw() {
  background(20);

  // Header
  fill(255);
  textSize(18);
  text(prompt, width/2, 40);

  // Zones area
  int y0 = 90;
  int h = height - 150;
  int w = width / 3;

  drawZone(0*w, y0, w, h, "HOUSING");
  drawZone(1*w, y0, w, h, "GREEN");
  drawZone(2*w, y0, w, h, "MOBILITY");

  // Footer scores
  textSize(16);
  text("HOUSING: " + housing, width/6, height-35);
  text("GREEN: " + green, width/2, height-35);
  text("MOBILITY: " + mobility, 5*width/6, height-35);
}

void drawZone(int x, int y, int w, int h, String label) {
  stroke(255);
  noFill();
  rect(x, y, w, h);

  fill(255);
  textSize(24);
  text(label, x + w/2, y + h/2);
}

void mousePressed() {
  String zone = zoneUnderMouse();
  if (zone != null) {
    OscMessage msg = new OscMessage("/game/zone_click");
    msg.add(zone);
    oscP5.send(msg, pythonServer);
    prompt = "Clicked: " + zone + " (sent to Python)";
  }
}

String zoneUnderMouse() {
  int y0 = 90;
  int h = height - 150;
  if (mouseY < y0 || mouseY > y0 + h) return null;

  int w = width / 3;
  if (mouseX < w) return "HOUSING";
  if (mouseX < 2*w) return "GREEN";
  return "MOBILITY";
}

// Receive state from Python
void oscEvent(OscMessage msg) {
  if (msg.checkAddrPattern("/game/state") && msg.checkTypetag("s")) {
    String jsonStr = msg.get(0).stringValue();
    JSONObject obj = parseJSONObject(jsonStr);
    if (obj != null) {
      prompt = obj.getString("prompt");
      JSONObject scores = obj.getJSONObject("scores");
      housing = scores.getInt("HOUSING");
      green = scores.getInt("GREEN");
      mobility = scores.getInt("MOBILITY");
    }
  }
}